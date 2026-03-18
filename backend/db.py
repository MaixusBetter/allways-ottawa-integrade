import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Return a live psycopg2 connection to the PostGIS database."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', 5432),
        dbname=os.getenv('DB_NAME', 'allways_db'),
        user=os.getenv('DB_USER', 'allways'),
        password=os.getenv('DB_PASSWORD', 'allways_dev'),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def execute_query(sql, params=None):
    """Run a SELECT query and return all rows as a list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()

def execute_write(sql, params=None):
    """Run an INSERT/UPDATE/DELETE query."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
    finally:
        conn.close()
