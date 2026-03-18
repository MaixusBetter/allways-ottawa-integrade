import requests
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

OSRM_BASE = os.getenv('OSRM_URL', 'http://localhost:5000')

def get_routes(origin_lat, origin_lng, dest_lat, dest_lng, alternatives=3) -> List[Dict]:
    """
    Call OSRM to get candidate routes between two points.
    Returns list of route dicts, each with 'geometry' (GeoJSON) and 'legs' data.
    """
    # Note: OSRM takes LONGITUDE first, then LATITUDE
    url = (
        f'{OSRM_BASE}/route/v1/foot/'
        f'{origin_lng},{origin_lat};{dest_lng},{dest_lat}'
        f'?alternatives={alternatives}'
        f'&geometries=geojson'
        f'&overview=full'
        f'&steps=true'
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 'Ok':
            raise ValueError(f"OSRM error: {data.get('message', 'unknown')}")
        return data.get('routes', [])
    except requests.exceptions.ConnectionError:
        raise RuntimeError('Cannot connect to OSRM. Is docker running?')

def extract_waypoints(route: Dict) -> List[tuple]:
    """Extract list of (lat, lng) waypoints from OSRM route geometry."""
    coords = route.get('geometry', {}).get('coordinates', [])
    # OSRM returns [lng, lat], we flip to (lat, lng)
    return [(lat, lng) for lng, lat in coords]