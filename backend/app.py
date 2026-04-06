import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from db import execute_query
from routing.osrm_client import get_routes, extract_waypoints
from routing.scorer import score_route_segment, compute_composite_score
from routing.weights import RouteWeights, PRESETS
from ai.allen import chat_with_allen, generate_storymap, generate_directions

load_dotenv()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

# ─────────────────────────────────────
# SERVE FRONTEND
# ─────────────────────────────────────
@app.route('/')
def serve_frontend():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve any static file from frontend/, skip API paths."""
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ─────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'message': 'AllWays Ottawa API is running'})

# ─────────────────────────────────────
# ROUTES ENDPOINT
# ─────────────────────────────────────
@app.route('/api/routes', methods=['POST'])
def routes():
    """
    Get 2-3 scored route alternatives between two points.
    Body: { origin: {lat, lng}, destination: {lat, lng}, weights: {...} }
    """
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Request body required'}), 400

    try:
        origin = body['origin']
        dest = body['destination']
        w_dict = body.get('weights', {})
        weights = RouteWeights.from_dict(w_dict)

        osrm_routes = get_routes(origin['lat'], origin['lng'], dest['lat'], dest['lng'], alternatives=1)
        if not osrm_routes:
            return jsonify({'error': 'No route found'}), 404

        scored = []
        for i, route in enumerate(osrm_routes[:3]):
            waypoints = extract_waypoints(route)
            sample = waypoints[::5] or waypoints[:1]
            seg_scores = [score_route_segment(lat, lng) for lat, lng in sample]
            composite = compute_composite_score(seg_scores, weights)
            n = len(seg_scores)
            avg_scores = {k: round(sum(s[k] for s in seg_scores)/n, 3) for k in seg_scores[0]}
            scored.append({
                'id': i,
                'geometry': route['geometry'],
                'distance_m': route['distance'],
                'duration_s': route['duration'],
                'legs': route.get('legs', []),
                'composite_score': composite,
                'scores': avg_scores,
            })

        scored.sort(key=lambda r: r['composite_score'], reverse=True)
        return jsonify({'routes': scored})

    except KeyError as e:
        return jsonify({'error': f'Missing field: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────
# ALLEN AI ENDPOINT
# ─────────────────────────────────────
@app.route('/api/allen', methods=['POST'])
def allen():
    """
    Send a message to Allen and get routing weights + explanation.
    Body: { message: string, conversation_history: [{role, content}] }
    """
    body = request.get_json()
    user_message = body.get('message', '')
    history = body.get('conversation_history', [])
    if not user_message:
        return jsonify({'error': 'message required'}), 400
    try:
        result = chat_with_allen(user_message, history)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────
# ALLEN STORY MAP ENDPOINT
# ─────────────────────────────────────
@app.route('/api/allen/storymap', methods=['POST'])
def storymap():
    """
    Generate a story map description for a destination.
    Body: { destination: string, user_context?: string }
    """
    body = request.get_json()
    destination = body.get('destination', '')
    user_context = body.get('user_context', '')
    if not destination:
        return jsonify({'error': 'destination required'}), 400
    try:
        result = generate_storymap(destination, user_context)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────
# ALLEN DIRECTIONS ENDPOINT
# ─────────────────────────────────────
@app.route('/api/allen/directions', methods=['POST'])
def directions():
    """
    Generate turn-by-turn walking directions for a route.
    Body: { origin: {lat,lng} OR string, destination: {lat,lng} OR string,
            origin_name: string, dest_name: string, user_context?: string }
    """
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Request body required'}), 400

    origin_name = body.get('origin_name', 'your location')
    dest_name = body.get('dest_name', 'your destination')
    user_context = body.get('user_context', '')

    try:
        origin = body.get('origin', {})
        dest = body.get('destination', {})
        if not origin or not dest:
            return jsonify({'error': 'origin and destination required'}), 400

        # Get lat/lng
        o_lat = origin.get('lat') if isinstance(origin, dict) else origin
        o_lng = origin.get('lng') if isinstance(origin, dict) else origin
        d_lat = dest.get('lat') if isinstance(dest, dict) else dest
        d_lng = dest.get('lng') if isinstance(dest, dict) else dest

        # Fetch route with steps from OSRM
        osrm_routes = get_routes(o_lat, o_lng, d_lat, d_lng, alternatives=1)
        if not osrm_routes:
            return jsonify({'error': 'No route found'}), 404

        route = osrm_routes[0]
        legs = route.get('legs', [])
        if not legs:
            return jsonify({'error': 'No route legs'}), 404

        steps = legs[0].get('steps', [])
        if not steps:
            return jsonify({'error': 'No route steps (OSRM may not have step data)'}), 404

        # Get Allen to humanize the directions
        result = generate_directions(steps, origin_name, dest_name, user_context)

        # Also include the route geometry for the frontend
        result['geometry'] = route.get('geometry', {})
        result['duration_s'] = route.get('duration', 0)
        result['distance_m'] = route.get('distance', 0)

        # Include step coordinates for GPS sync
        step_coords = []
        for s in steps:
            maneuver = s.get('maneuver', {})
            loc = maneuver.get('location', [])
            if loc:
                step_coords.append({'lng': loc[0], 'lat': loc[1]})
        result['step_coordinates'] = step_coords

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────
# LAYERS ENDPOINT
# ─────────────────────────────────────
@app.route('/api/layers/<layer_name>')
def get_layer(layer_name):
    """Return a PostGIS table as GeoJSON for the map overlay."""
    ALLOWED = ['sidewalks','pedestrian_network','pathways','cycling_network',
               'parks_greenspace','benches','washrooms','libraries',
               'community_centres','recreation_facilities','transit_stops']
    if layer_name not in ALLOWED:
        return jsonify({'error': 'Unknown layer'}), 404
    rows = execute_query(
        f"SELECT ST_AsGeoJSON(geom) as geojson FROM {layer_name} LIMIT 5000"
    )
    features = [{'type':'Feature','geometry':json.loads(r['geojson']),'properties':{}} for r in rows]
    return jsonify({'type':'FeatureCollection','features':features})

# ─────────────────────────────────────
# GEOCODING ENDPOINT
# ─────────────────────────────────────
@app.route('/api/geocode')
def geocode():
    """Convert an address string to lat/lng using Nominatim (OpenStreetMap)."""
    import requests as req
    address = request.args.get('q', '')
    if not address:
        return jsonify({'error': 'q parameter required'}), 400
    r = req.get(
        'https://nominatim.openstreetmap.org/search',
        params={'q': f'{address}, Ottawa, Ontario', 'format':'json', 'limit':1},
        headers={'User-Agent': 'AllWaysOttawa/1.0'}
    )
    results = r.json()
    if not results:
        return jsonify({'error': 'Address not found'}), 404
    return jsonify({'lat': float(results[0]['lat']), 'lng': float(results[0]['lon'])})

# ─────────────────────────────────────
# FEEDBACK ENDPOINT
# ─────────────────────────────────────
@app.route('/api/feedback', methods=['POST'])
def feedback():
    """
    Store user feedback about a route.
    Body: { rating, route_type, name?, what_went_well?, improvements?, other? }
    """
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Request body required'}), 400
    rating = body.get('rating')
    route_type = body.get('route_type')
    if not rating or not route_type:
        return jsonify({'error': 'rating and route_type are required'}), 400
    try:
        from db import execute_write
        execute_write('''
            INSERT INTO feedback (rating, route_type, user_name, what_went_well, improvements, other_comments)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            int(rating),
            route_type,
            body.get('name', ''),
            body.get('what_went_well', ''),
            body.get('improvements', ''),
            body.get('other', '')
        ))
        return jsonify({'status': 'ok', 'message': 'Feedback saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────────────────
# AVAILABLE LAYERS LIST
# ─────────────────────────────────────
@app.route('/api/layers')
def list_layers():
    """Return the list of available map overlay layers."""
    available = ['sidewalks','pedestrian_network','pathways','cycling_network',
                 'parks_greenspace','benches','washrooms','libraries',
                 'community_centres','recreation_facilities','transit_stops']
    return jsonify({'layers': available})

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    app.run(debug=True, port=port)