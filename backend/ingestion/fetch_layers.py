"""
Download Ottawa open data GeoJSON layers.

Ottawa uses ArcGIS Hub (open.ottawa.ca). The ArcGIS Feature Server
endpoints return GeoJSON via ?f=geojson queries. If a FeatureServer
URL is not known, we fall back to the Hub's standard GeoJSON download.

Run:  python -m ingestion.fetch_layers
"""
import requests
import geopandas as gpd
import os
import json
from io import BytesIO

# ArcGIS Feature Server query URLs (reliable, paginated)
# These query the City of Ottawa's ArcGIS REST services directly.
# Format: FeatureServer/{layer}/query?where=1=1&outFields=*&f=geojson&outSR=4326
ARCGIS_BASE = 'https://maps.ottawa.ca/arcgis/rest/services'

DATASETS = {
    # ── Using ArcGIS Feature Server query (most reliable) ──
    'sidewalks': {
        'url': f'{ARCGIS_BASE}/Sidewalks/MapServer/0/query',
        'type': 'query',
    },
    'pathways': {
        'url': f'{ARCGIS_BASE}/Pathways/MapServer/0/query',
        'type': 'query',
    },
    'cycling_network': {
        'url': f'{ARCGIS_BASE}/Cycling_Network/MapServer/0/query',
        'type': 'query',
    },
    'parks_greenspace': {
        'url': f'{ARCGIS_BASE}/Parks_Inventory/MapServer/0/query',
        'type': 'query',
    },

    # ── Using ArcGIS Hub GeoJSON download (fallback) ──
    'pedestrian_network': {
        'url': 'https://open.ottawa.ca/datasets/ottawa::pedestrian-network-.geojson',
        'alt_url': f'{ARCGIS_BASE}/Pedestrian_Network/MapServer/0/query',
        'type': 'hub_or_query',
    },
    'traffic_collisions': {
        'url': 'https://open.ottawa.ca/datasets/ottawa::traffic-crash-data.geojson',
        'alt_url': f'{ARCGIS_BASE}/Traffic_Crashes/MapServer/0/query',
        'type': 'hub_or_query',
    },
    'benches': {
        'url': f'{ARCGIS_BASE}/Benches/MapServer/0/query',
        'type': 'query',
    },
    'washrooms': {
        'url': f'{ARCGIS_BASE}/Public_Washrooms/MapServer/0/query',
        'type': 'query',
    },
    'libraries': {
        'url': f'{ARCGIS_BASE}/Library_Branches/MapServer/0/query',
        'type': 'query',
    },
    'community_centres': {
        'url': f'{ARCGIS_BASE}/Community_Centres/MapServer/0/query',
        'type': 'query',
    },
    'recreation_facilities': {
        'url': f'{ARCGIS_BASE}/Recreation_Facilities/MapServer/0/query',
        'type': 'query',
    },
}

SAVE_DIR = os.path.join(os.path.dirname(__file__), '../../data/raw')

# Standard ArcGIS query params to get GeoJSON
QUERY_PARAMS = {
    'where': '1=1',
    'outFields': '*',
    'outSR': '4326',
    'f': 'geojson',
    'resultRecordCount': 5000,  # ArcGIS default max per page
}


def fetch_arcgis_query(name, url):
    """
    Fetch GeoJSON from an ArcGIS MapServer/FeatureServer query endpoint.
    Paginates through results if needed.
    """
    all_features = []
    offset = 0
    page_size = 5000

    while True:
        params = {**QUERY_PARAMS, 'resultOffset': offset, 'resultRecordCount': page_size}
        resp = requests.get(url, params=params, timeout=60)

        if resp.status_code == 400:
            # Some older servers don't support pagination — try without offset
            params.pop('resultOffset', None)
            params.pop('resultRecordCount', None)
            resp = requests.get(url, params=params, timeout=60)

        resp.raise_for_status()
        data = resp.json()

        features = data.get('features', [])
        if not features:
            break

        all_features.extend(features)
        print(f'    Page {offset // page_size + 1}: {len(features)} features')

        # If we got fewer than page_size, we've reached the end
        if len(features) < page_size:
            break
        offset += page_size

    if not all_features:
        return None

    geojson = {
        'type': 'FeatureCollection',
        'features': all_features,
    }
    return geojson


def fetch_hub_geojson(name, url):
    """Try to download GeoJSON directly from an ArcGIS Hub URL."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def fetch_dataset(name, config):
    """Download a dataset using the best available method."""
    print(f'Fetching {name}...')

    geojson = None
    methods_tried = []

    # Try ArcGIS query first
    for attempt_url in [config.get('url'), config.get('alt_url')]:
        if not attempt_url:
            continue

        if '/query' in attempt_url or config.get('type') == 'query':
            try:
                methods_tried.append(f'ArcGIS query: {attempt_url}')
                geojson = fetch_arcgis_query(name, attempt_url)
                if geojson and geojson.get('features'):
                    break
            except Exception as e:
                print(f'    ArcGIS query failed: {e}')
        else:
            try:
                methods_tried.append(f'Hub download: {attempt_url}')
                geojson = fetch_hub_geojson(name, attempt_url)
                if geojson and geojson.get('features'):
                    break
            except Exception as e:
                print(f'    Hub download failed: {e}')

    if not geojson or not geojson.get('features'):
        print(f'  SKIP {name}: no data returned')
        print(f'    Tried: {"; ".join(methods_tried)}')
        return None

    # Save as GeoJSON
    os.makedirs(SAVE_DIR, exist_ok=True)
    out_path = os.path.join(SAVE_DIR, f'{name}.geojson')
    with open(out_path, 'w') as f:
        json.dump(geojson, f)

    n_features = len(geojson.get('features', []))
    print(f'  ✅ Saved {n_features} features to {out_path}')

    # Also try to load as GeoDataFrame to reproject if needed
    try:
        gdf = gpd.read_file(out_path)
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
            gdf.to_file(out_path, driver='GeoJSON')
            print(f'    Reprojected to EPSG:4326')
    except Exception as e:
        print(f'    Warning: could not validate CRS: {e}')

    return geojson


def fetch_all():
    os.makedirs(SAVE_DIR, exist_ok=True)
    results = {}
    success = 0
    for name, config in DATASETS.items():
        results[name] = fetch_dataset(name, config)
        if results[name]:
            success += 1
    print(f'\nDone! {success}/{len(DATASETS)} datasets fetched.')
    if success < len(DATASETS):
        print('Some datasets may require updated URLs — check open.ottawa.ca')
    return results


if __name__ == '__main__':
    fetch_all()
