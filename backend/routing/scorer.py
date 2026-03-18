from typing import List, Dict
from db import execute_query
from routing.weights import RouteWeights

COLLISION_RADIUS_M = 100
BENCH_RADIUS_M = 50
SERVICE_RADIUS_M = 200
PARK_RADIUS_M = 30
SIDEWALK_RADIUS_M = 20

def score_route_segment(lat: float, lng: float) -> Dict:
    """
    Given a lat/lng point on a route, query PostGIS to compute
    safety, accessibility, environment, and comfort scores.
    """
    # --- SAFETY ---
    collision_rows = execute_query('''
        SELECT COUNT(*) as cnt FROM traffic_collisions
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
    ''', (lng, lat, COLLISION_RADIUS_M))
    collision_count = collision_rows[0]['cnt'] if collision_rows else 0
    safety_score = max(0.1, 1.0 - (collision_count / 10.0))

    # --- ACCESSIBILITY ---
    sidewalk_rows = execute_query('''
        SELECT COUNT(*) as cnt FROM sidewalks
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
    ''', (lng, lat, SIDEWALK_RADIUS_M))
    has_sidewalk = sidewalk_rows[0]['cnt'] > 0 if sidewalk_rows else False
    accessibility_score = 0.9 if has_sidewalk else 0.3

    # --- ENVIRONMENT ---
    park_rows = execute_query('''
        SELECT COUNT(*) as cnt FROM parks_greenspace
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
    ''', (lng, lat, PARK_RADIUS_M))
    near_park = park_rows[0]['cnt'] > 0 if park_rows else False
    environment_score = 0.9 if near_park else 0.5

    # --- COMFORT ---
    bench_rows = execute_query('''
        SELECT COUNT(*) as cnt FROM benches
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
    ''', (lng, lat, BENCH_RADIUS_M))
    bench_count = bench_rows[0]['cnt'] if bench_rows else 0

    service_rows = execute_query('''
        SELECT (
            (SELECT COUNT(*) FROM libraries WHERE
                ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s)) +
            (SELECT COUNT(*) FROM community_centres WHERE
                ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s)) +
            (SELECT COUNT(*) FROM washrooms WHERE
                ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, %s))
        ) as total
    ''', (lng,lat,SERVICE_RADIUS_M, lng,lat,SERVICE_RADIUS_M, lng,lat,SERVICE_RADIUS_M))
    service_count = service_rows[0]['total'] if service_rows else 0

    comfort_score = min(1.0, 0.4 + (bench_count * 0.1) + (service_count * 0.05))

    return {
        'safety': round(safety_score, 3),
        'accessibility': round(accessibility_score, 3),
        'environment': round(environment_score, 3),
        'comfort': round(comfort_score, 3),
    }

def compute_composite_score(segment_scores: List[Dict], weights: RouteWeights) -> float:
    """Average the segment scores and apply user weights to get one composite score."""
    if not segment_scores:
        return 0.0
    n = len(segment_scores)
    avg_safety  = sum(s['safety'] for s in segment_scores) / n
    avg_access  = sum(s['accessibility'] for s in segment_scores) / n
    avg_env     = sum(s['environment'] for s in segment_scores) / n
    avg_comfort = sum(s['comfort'] for s in segment_scores) / n

    total_weight = weights.safety + weights.accessibility + weights.environment + weights.comfort
    if total_weight == 0:
        return 0.0

    composite = (
        weights.safety        * avg_safety +
        weights.accessibility * avg_access +
        weights.environment   * avg_env +
        weights.comfort       * avg_comfort
    ) / total_weight

    return round(composite, 4)