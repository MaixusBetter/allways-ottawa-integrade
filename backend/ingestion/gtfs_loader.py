"""
Download OC Transpo GTFS data and load transit stops into PostGIS.
GTFS source: https://www.octranspo.com/en/plan-your-trip/travel-tools/developers/
"""
import os
import csv
import zipfile
import requests
from io import BytesIO

# Use relative import when run as module, fallback for direct execution
try:
    from db import execute_write
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from db import execute_write

GTFS_URL = 'https://www.octranspo.com/files/google_transit.zip'
DATA_DIR = os.path.join(os.path.dirname(__file__), '../../data/raw')


def download_gtfs():
    """Download the OC Transpo GTFS zip and extract stops.txt."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print('Downloading OC Transpo GTFS feed...')
    resp = requests.get(GTFS_URL, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(BytesIO(resp.content)) as zf:
        for name in ['stops.txt', 'routes.txt', 'trips.txt']:
            if name in zf.namelist():
                zf.extract(name, DATA_DIR)
                print(f'  Extracted {name}')
    print('GTFS download complete.')


def load_stops():
    """Parse stops.txt and insert into the transit_stops PostGIS table."""
    stops_path = os.path.join(DATA_DIR, 'stops.txt')
    if not os.path.exists(stops_path):
        print('stops.txt not found — run download_gtfs() first')
        return

    print('Loading transit stops into PostGIS...')
    count = 0
    with open(stops_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stop_id = row.get('stop_id', '').strip()
            stop_name = row.get('stop_name', '').strip()
            lat = row.get('stop_lat', '').strip()
            lon = row.get('stop_lon', '').strip()

            if not stop_id or not lat or not lon:
                continue
            try:
                lat_f, lon_f = float(lat), float(lon)
            except ValueError:
                continue

            execute_write('''
                INSERT INTO transit_stops (stop_id, stop_name, geom)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ON CONFLICT (stop_id) DO UPDATE
                SET stop_name = EXCLUDED.stop_name,
                    geom = EXCLUDED.geom
            ''', (stop_id, stop_name, lon_f, lat_f))
            count += 1

    print(f'  Loaded {count} transit stops.')


def load_gtfs():
    """Full pipeline: download GTFS then load stops."""
    download_gtfs()
    load_stops()


if __name__ == '__main__':
    load_gtfs()
