-- SPATIAL INDEXES (GiST = Generalized Search Tree, used for geometry)
CREATE INDEX IF NOT EXISTS idx_sidewalks_geom ON sidewalks USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_pedestrian_geom ON pedestrian_network USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_pathways_geom ON pathways USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_cycling_geom ON cycling_network USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_collisions_geom ON traffic_collisions USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_int_traffic_geom ON intersection_traffic USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_midblock_geom ON midblock_traffic USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_parks_geom ON parks_greenspace USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_benches_geom ON benches USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_washrooms_geom ON washrooms USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_libraries_geom ON libraries USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_community_geom ON community_centres USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_recreation_geom ON recreation_facilities USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_transit_stops_geom ON transit_stops USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_segment_scores_geom ON segment_scores USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_segment_scores_osm_id ON segment_scores (osm_way_id);
