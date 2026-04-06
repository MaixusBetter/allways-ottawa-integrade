#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# setup.sh — First-time setup for AllWays Ottawa
# Starts DB, loads open data, then launches the app.
# ──────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "═══════════════════════════════════════════════"
echo "  AllWays Ottawa — Setup"
echo "═══════════════════════════════════════════════"
echo ""

# ── 1. Check prerequisites ────────────────────────────
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required. Install it from docker.com"; exit 1; }

# Detect Python command (Windows uses 'python', Linux/Mac uses 'python3')
PYTHON=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  # Verify it's Python 3, not Python 2
  PY_VER=$(python -c "import sys; print(sys.version_info[0])" 2>/dev/null)
  if [ "$PY_VER" = "3" ]; then
    PYTHON="python"
  fi
fi
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3 is required. Install it from python.org"
  echo "   On Windows, make sure 'Add Python to PATH' is checked during install."
  exit 1
fi
echo "   Using: $($PYTHON --version)"

# ── 2. Environment file ──────────────────────────────
if [ ! -f backend/.env ]; then
  echo "📋 Creating .env from template..."
  cp backend/.env.example backend/.env
  echo "⚠️  Edit backend/.env to add your OpenAI API key."
  echo "   (Allen AI will use hardcoded responses without it.)"
  echo ""
fi

# ── 3. Start PostgreSQL ──────────────────────────────
echo "🐘 Starting PostgreSQL + PostGIS..."
docker compose up -d postgres
echo "   Waiting for database to be ready..."
sleep 5
# Wait for healthcheck
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U allways -d allways_db > /dev/null 2>&1; then
    echo "   ✅ Database ready."
    break
  fi
  sleep 2
done

# ── 4. Python environment ────────────────────────────
echo ""
echo "🐍 Setting up Python environment..."
cd backend
if [ ! -d venv ]; then
  $PYTHON -m venv venv
fi
# Activate: Windows (Git Bash / MINGW) vs Linux/Mac
if [ -f venv/Scripts/activate ]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed."

# ── 5. Fetch + load open data ────────────────────────
echo ""
echo "📊 Fetching Ottawa open data layers..."
python -c "from ingestion.fetch_layers import fetch_all; fetch_all()"

echo ""
echo "📥 Loading data into PostGIS..."
python -c "from ingestion.load_postgis import load_all; load_all()"

echo ""
echo "🚌 Loading OC Transpo GTFS transit stops..."
python -c "from ingestion.gtfs_loader import load_gtfs; load_gtfs()" 2>/dev/null || echo "   ⚠️  GTFS load skipped (OC Transpo may be unavailable)."

# ── 6. Build spatial indexes ─────────────────────────
echo ""
echo "🔍 Building spatial indexes..."
cd ..
docker compose exec -T postgres psql -U allways -d allways_db -f /docker-entrypoint-initdb.d/indexes.sql > /dev/null 2>&1 || true
echo "   ✅ Indexes ready."

# ── 7. OSRM status ───────────────────────────────────
echo ""
if [ -f osrm_data/ontario-latest.osrm ]; then
  echo "🗺️  OSRM data found. Starting routing engine..."
  docker compose up -d osrm
else
  echo "⚠️  OSRM data not prepared yet."
  echo "   Run: bash prepare_osrm.sh    (takes ~15 min, ~400 MB download)"
  echo "   Then: docker compose up -d osrm"
  echo "   The app works without it (falls back to public OSRM demo server)."
fi

# ── 8. Launch ─────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo ""
if [ -f backend/venv/Scripts/activate ]; then
  echo "  Start the app:"
  echo "    cd backend"
  echo "    source venv/Scripts/activate"
  echo "    python app.py"
else
  echo "  Start the app:"
  echo "    cd backend"
  echo "    source venv/bin/activate"
  echo "    python app.py"
fi
echo ""
echo "  Open browser:   http://localhost:5001"
echo "═══════════════════════════════════════════════"
