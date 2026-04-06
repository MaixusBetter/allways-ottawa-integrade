import requests
import os
import time
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

OSRM_BASE = os.getenv('OSRM_URL', 'https://router.project-osrm.org')

def get_routes(origin_lat, origin_lng, dest_lat, dest_lng, alternatives=1) -> List[Dict]:
    """
    Call OSRM to get candidate routes between two points.
    Retries up to 3 times with delay for flaky public server.
    """
    url = (
        f'{OSRM_BASE}/route/v1/foot/'
        f'{origin_lng},{origin_lat};{dest_lng},{dest_lat}'
        f'?alternatives={alternatives}'
        f'&geometries=geojson'
        f'&overview=full'
        f'&steps=true'
    )
    last_err = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(1.5)
            print(f'[OSRM] Retry attempt {attempt + 1}...')
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') != 'Ok':
                raise ValueError(f"OSRM error: {data.get('message', 'unknown')}")
            return data.get('routes', [])
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            last_err = e
            print(f'[OSRM] Attempt {attempt + 1} failed: {e}')
    raise RuntimeError(f'OSRM failed after 3 attempts: {last_err}')

def extract_waypoints(route: Dict) -> List[tuple]:
    """Extract list of (lat, lng) waypoints from OSRM route geometry."""
    coords = route.get('geometry', {}).get('coordinates', [])
    # OSRM returns [lng, lat], we flip to (lat, lng)
    return [(lat, lng) for lng, lat in coords]