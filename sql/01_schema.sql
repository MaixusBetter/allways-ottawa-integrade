-- Enable PostGIS extension (must be first)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

CREATE TABLE IF NOT EXISTS sidewalks (
  id SERIAL PRIMARY KEY,
  osm_id TEXT,
  surface TEXT,
  width_m FLOAT,
  smoothness TEXT,
  geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS pedestrian_network (
  id SERIAL PRIMARY KEY,
  name TEXT,
  type TEXT,
  geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS pathways (
  id SERIAL PRIMARY KEY,
  name TEXT,
  type TEXT,
  geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS cycling_network (
  id SERIAL PRIMARY KEY,
  name TEXT,
  lane_type TEXT,
  geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS traffic_collisions (
  id SERIAL PRIMARY KEY,
  year INT,
  severity TEXT,
  collision_type TEXT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS intersection_traffic (
  id SERIAL PRIMARY KEY,
  aadt INT,
  year INT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS midblock_traffic (
  id SERIAL PRIMARY KEY,
  aadt INT,
  street_name TEXT,
  geom GEOMETRY(LINESTRING, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS parks_greenspace (
  id SERIAL PRIMARY KEY,
  name TEXT,
  type TEXT,
  geom GEOMETRY(MULTIPOLYGON, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS benches (
  id SERIAL PRIMARY KEY,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS washrooms (
  id SERIAL PRIMARY KEY,
  accessible BOOLEAN,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS libraries (
  id SERIAL PRIMARY KEY,
  name TEXT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS community_centres (
  id SERIAL PRIMARY KEY,
  name TEXT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS recreation_facilities (
  id SERIAL PRIMARY KEY,
  name TEXT,
  type TEXT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS transit_stops (
  id SERIAL PRIMARY KEY,
  stop_id TEXT UNIQUE NOT NULL,
  stop_name TEXT,
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS segment_scores (
  id SERIAL PRIMARY KEY,
  osm_way_id BIGINT UNIQUE NOT NULL,
  safety_score FLOAT DEFAULT 0.5,
  accessibility_score FLOAT DEFAULT 0.5,
  environment_score FLOAT DEFAULT 0.5,
  comfort_score FLOAT DEFAULT 0.5,
  collision_count INT DEFAULT 0,
  has_sidewalk BOOLEAN DEFAULT FALSE,
  bench_count INT DEFAULT 0,
  service_count INT DEFAULT 0,
  in_park BOOLEAN DEFAULT FALSE,
  geom GEOMETRY(LINESTRING, 4326),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
  id SERIAL PRIMARY KEY,
  rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  route_type TEXT NOT NULL,
  user_name TEXT,
  what_went_well TEXT,
  improvements TEXT,
  other_comments TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
