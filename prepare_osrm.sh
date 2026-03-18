#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# prepare_osrm.sh — Download + prepare Ontario walking data for OSRM
# Run this ONCE before starting the OSRM container.
# Takes ~10-20 min depending on connection + CPU.
# ──────────────────────────────────────────────────────────
set -e

OSRM_DIR="$(dirname "$0")/osrm_data"
PBF_URL="https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf"
PBF_FILE="$OSRM_DIR/ontario-latest.osm.pbf"

mkdir -p "$OSRM_DIR"

# 1. Download Ontario extract
if [ ! -f "$PBF_FILE" ]; then
  echo "⬇️  Downloading Ontario OSM extract (~400 MB)..."
  wget -q --show-progress -O "$PBF_FILE" "$PBF_URL"
else
  echo "✅ Ontario PBF already exists, skipping download."
fi

# 2. Extract (foot profile for walking routes)
if [ ! -f "$OSRM_DIR/ontario-latest.osrm" ]; then
  echo "🔧 Extracting with foot profile..."
  docker run --rm -v "$OSRM_DIR:/data" osrm/osrm-backend \
    osrm-extract -p /opt/foot.lua /data/ontario-latest.osm.pbf
else
  echo "✅ OSRM extract already exists, skipping."
fi

# 3. Partition
if [ ! -f "$OSRM_DIR/ontario-latest.osrm.partition" ]; then
  echo "📐 Partitioning..."
  docker run --rm -v "$OSRM_DIR:/data" osrm/osrm-backend \
    osrm-partition /data/ontario-latest.osrm
else
  echo "✅ Partition already exists, skipping."
fi

# 4. Customize
if [ ! -f "$OSRM_DIR/ontario-latest.osrm.cell_metrics" ]; then
  echo "⚙️  Customizing..."
  docker run --rm -v "$OSRM_DIR:/data" osrm/osrm-backend \
    osrm-customize /data/ontario-latest.osrm
else
  echo "✅ Customization already exists, skipping."
fi

echo ""
echo "✅ OSRM data ready! Now update docker-compose.yml volume to point here:"
echo "   volumes:"
echo "     - ./osrm_data:/data"
echo ""
echo "Then run: docker-compose up -d"
