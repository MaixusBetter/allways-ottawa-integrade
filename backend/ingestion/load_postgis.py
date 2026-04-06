import geopandas as gpd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'allways_db')
    DB_USER = os.getenv('DB_USER', 'allways')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'allways_dev')
    url = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    return create_engine(url)

TABLE_MAP = {
    'sidewalks': 'sidewalks',
    'pedestrian_network': 'pedestrian_network',
    'pathways': 'pathways',
    'cycling_network': 'cycling_network',
    'parks_greenspace': 'parks_greenspace',
    'traffic_collisions': 'traffic_collisions',
    'benches': 'benches',
    'washrooms': 'washrooms',
    'libraries': 'libraries',
    'community_centres': 'community_centres',
    'recreation_facilities': 'recreation_facilities',
}

RAW_DIR = os.path.join(os.path.dirname(__file__), '../../data/raw')

def load_dataset(name, table_name, engine):
    path = os.path.join(RAW_DIR, f'{name}.geojson')
    if not os.path.exists(path):
        print(f'  SKIP {name}: file not found (run fetch_layers.py first)')
        return
    print(f'Loading {name} -> table {table_name}...')
    gdf = gpd.read_file(path)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    gdf = gdf[gdf.geometry.notna()]
    gdf.to_postgis(table_name, engine, if_exists='replace', index=False)
    print(f'  Loaded {len(gdf)} rows')

def load_all():
    engine = get_engine()
    for name, table in TABLE_MAP.items():
        load_dataset(name, table, engine)
    print('All datasets loaded into PostGIS.')

if __name__ == '__main__':
    load_all()