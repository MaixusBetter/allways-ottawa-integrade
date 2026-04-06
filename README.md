# 🗺️ AllWays Ottawa

**AI-powered accessible pedestrian navigation for Ottawa.**

AllWays Ottawa helps you find walking routes based on what matters most to you — whether that's safety, wheelchair accessibility, green space, or nearby amenities. Ask our AI assistant Allen to plan your route in plain language, and watch it appear on the map.

---

## ✨ What's New

- **Allen AI now runs on Ollama** — completely free, runs locally on your machine, no API keys needed
- **Allen understands full routing requests** — say *"I'm in a wheelchair, get me from 95 Bronson to 75 Laurier"* and the route plots automatically on the map
- **Full frontend integrated** — polished mobile-style UI with live map, route toggles, autocomplete, and feedback
- **Smart fallback system** — the app auto-detects what's available and gracefully degrades (works as a standalone demo with zero setup, or as a full-stack app with AI + database scoring)
- **Windows + Mac + Linux compatible** — tested on Windows with Git Bash

---

## 🏗️ Architecture

```
allways-ottawa/
├── frontend/
│   └── index.html               ← Full UI (auto-detects backend)
├── backend/
│   ├── app.py                   ← Flask API + serves frontend
│   ├── db.py                    ← PostGIS database connection
│   ├── ai/
│   │   └── allen.py             ← Allen AI (Ollama/Mistral, free + local)
│   ├── routing/
│   │   ├── osrm_client.py       ← OSRM walking route engine
│   │   ├── scorer.py            ← PostGIS safety/access/env scoring
│   │   └── weights.py           ← Route weight presets
│   └── ingestion/
│       ├── fetch_layers.py      ← Download Ottawa open data
│       ├── load_postgis.py      ← Load into PostGIS tables
│       └── gtfs_loader.py       ← OC Transpo transit stops
├── sql/
│   ├── 01_schema.sql            ← Database tables
│   └── 02_indexes.sql           ← Spatial indexes
├── setup.sh                     ← One-command setup script
├── prepare_osrm.sh              ← Optional: local routing engine
├── allways_ottawa_gps.py        ← Google Colab launcher
└── docker-compose.yml           ← PostgreSQL + PostGIS
```

---

## 🚀 Getting Started

### Option 1: Demo Mode (no setup at all)

If you just want to see the app running:

1. Open `frontend/index.html` in any web browser
2. That's it! You'll see a yellow **DEMO MODE** badge
3. Type locations like "Rideau Centre" → "Parliament Hill" and press **Go**

Everything runs in your browser — no server, no database, no AI needed. Routes come from a public routing server.

---

### Option 2: Full Stack (recommended)

This gives you the real AI assistant, proper routing, and the connected experience.

#### What you'll need

| Tool | What it does | Download |
|---|---|---|
| **Docker Desktop** | Runs the database | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Python 3.10+** | Runs the backend server | [python.org](https://www.python.org/downloads/) |
| **Ollama** | Runs Allen AI (free and local!) | [ollama.com](https://ollama.com/download) |

> **Windows users:** When installing Python, make sure you check the box that says ✅ **"Add Python to PATH"** — this saves a lot of headaches later.

#### Step by step

**1. Clone and enter the project**
```bash
git clone https://github.com/abbywilson11/allways-ottawa.git
cd allways-ottawa
```

**2. Start the database**

Make sure Docker Desktop is open and running, then:
```bash
docker compose up -d postgres
```
Wait about 10 seconds for it to initialize. You can verify it's ready:
```bash
docker exec allways_postgres psql -U allways -d allways_db -c "SELECT 1;"
```
If you see a little table with the number `1`, you're good! If not, check the [Troubleshooting](#-troubleshooting) section below.

**3. Set up Python**
```bash
cd backend
python -m venv venv
```

Activate the virtual environment:
| Your system | Command |
|---|---|
| **Windows (Git Bash)** | `source venv/Scripts/activate` |
| **Mac / Linux** | `source venv/bin/activate` |

You'll see `(venv)` appear at the start of your terminal prompt. Now install the dependencies:
```bash
pip install -r requirements.txt
pip install --upgrade openai
```

**4. Create your config file**
```bash
cp .env.example .env
```
The defaults work right away — no API keys needed since Allen uses Ollama.

**5. Set up Allen AI**

Open a **separate terminal window** and run:
```bash
ollama pull mistral
```
This downloads the Mistral AI model (~4 GB). You only need to do this once.

> **🧠 A note about warming up Allen**
>
> The very first time you ask Allen a question after starting your computer, Ollama needs to load the AI model into memory. Think of it like opening a big application — the first launch takes a moment (about 30–60 seconds), but after that it stays open and responds quickly (2–5 seconds).
>
> If you'd like Allen to be fast right from the start, you can warm him up before launching the app. In a separate terminal, run:
> ```bash
> ollama run mistral "say hello"
> ```
> Wait for Mistral to respond, then type `/bye` to exit. Allen is now warmed up and ready! This step is totally optional — Allen will still work without it, the first answer just takes a little longer.

**6. Launch the app**

Back in your original terminal (the one showing `(venv)`):
```bash
python app.py
```

You should see:
```
[Allen] Using Ollama (mistral) at http://localhost:11434
 * Running on http://127.0.0.1:5001
```

**7. Open your browser and try it out!**

Go to **http://localhost:5001**

You should see a green **CONNECTED** badge in the top-right corner. 🎉

---

## 🤖 Using Allen AI

Allen is your personal navigation assistant. He understands natural language and can plan routes directly.

### Full routing requests

Just tell Allen where you want to go and what you need. He'll extract the locations, set the right priorities, and plot the route on the map automatically:

- *"I'm in a wheelchair, get me from 95 Bronson to 75 Laurier"*
- *"Navigate me from uOttawa to Lansdowne, I want lots of greenery"*
- *"Safest route from Rideau Centre to Parliament Hill at night"*

### Preference-only requests

If you just want to set priorities without specific locations, Allen will adjust the route weights and let you enter locations on the Map tab:

- *"I use a wheelchair"*
- *"I want the greenest route with lots of parks"*
- *"What's the safest way to walk tonight?"*

### Route scoring dimensions

Allen scores routes on four dimensions and adjusts them based on your needs:

| Dimension | What it considers |
|---|---|
| 🛡️ **Safety** | Collision data, traffic volume, lighting, busy pedestrian zones |
| ♿ **Accessibility** | Sidewalk quality, curb cuts, ramps, wheelchair-friendly paths |
| 🌿 **Environment** | Parks, green corridors, tree canopy, air quality |
| 🪑 **Comfort** | Nearby benches, washrooms, libraries, community services |

---

## 📡 API Reference

For developers integrating with AllWays Ottawa:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the frontend |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/routes` | Get scored walking route alternatives |
| `POST` | `/api/allen` | Chat with Allen AI assistant |
| `GET` | `/api/geocode?q=...` | Convert an address to coordinates |
| `GET` | `/api/layers` | List available map overlay layers |
| `GET` | `/api/layers/<name>` | Get a specific layer as GeoJSON |
| `POST` | `/api/feedback` | Submit feedback about a route |

### Example: Ask Allen for a route

```bash
curl -X POST http://localhost:5001/api/allen \
  -H "Content-Type: application/json" \
  -d '{"message": "wheelchair route from Rideau Centre to uOttawa"}'
```

### Example: Health check

```bash
curl http://localhost:5001/api/health
```

---

## 🔧 Troubleshooting

Here are the most common issues people run into and how to solve them.

### "role allways does not exist"

This happens when Docker reuses an old database volume from a previous attempt. The fix is to remove the old data and let the database reinitialize:

```bash
docker compose down -v
docker compose up -d postgres
```

The `-v` flag is the important part — it removes the old volume. Wait 10 seconds and try again.

### "Python was not found" (Windows)

Windows sometimes has a `python3` shortcut that opens the Microsoft Store instead of actually running Python. A few things to check:

- Use `python` (not `python3`) in all commands
- Make sure you checked **"Add Python to PATH"** when you installed Python
- If you installed Python after opening your terminal, close and reopen the terminal

### Allen is slow on the first question

Totally normal! The first time you ask Allen something after starting your computer, Ollama loads the AI model into memory (~4 GB). This takes about 30–60 seconds. Every question after that is fast (2–5 seconds).

To warm Allen up ahead of time, open a separate terminal and run:
```bash
ollama run mistral "say hello"
```
Wait for the response, type `/bye`, and Allen is ready to go.

### "No AI backend available"

Allen can't find Ollama. Make sure it's installed and has the Mistral model:
```bash
ollama list
```
If you see `mistral` in the list, Ollama is ready. If not, pull the model:
```bash
ollama pull mistral
```
If the `ollama` command itself isn't found, [download and install Ollama](https://ollama.com/download).

### "Container is not running"

Docker Desktop probably isn't open. Launch Docker Desktop from your applications, wait for it to finish starting up (the whale icon in your taskbar/menu bar will stop animating), then:
```bash
docker compose up -d postgres
```

### SQL errors during database startup

If you see errors about tables not existing when indexes are being created, the SQL files ran in the wrong order. Make sure the files in the `sql/` folder are named:
- `01_schema.sql` (tables — runs first)
- `02_indexes.sql` (indexes — runs second)

Then reset the database:
```bash
docker compose down -v
docker compose up -d postgres
```

### Port 5001 is already in use

Another application is using that port. You can either close it, or change the port in `backend/.env`:
```
FLASK_PORT=5002
```
Then access the app at `http://localhost:5002` instead.

### "HTTPConnectionPool read timed out" from Allen

This usually means Ollama is still loading the model. Give it a minute and try again. If it keeps happening, your computer might not have enough free RAM (Mistral needs about 4 GB). Close some other applications and try again.

---

## 🧰 Tech Stack

| Component | Technology | Cost |
|---|---|---|
| **AI Assistant** | Ollama + Mistral 7B | Free |
| **Backend** | Python 3 + Flask | Free |
| **Database** | PostgreSQL 15 + PostGIS 3.4 | Free (Docker) |
| **Routing Engine** | OSRM (walking profile) | Free |
| **Frontend** | HTML/CSS/JS + Leaflet.js | Free |
| **Map Tiles** | CARTO Dark Basemap | Free |
| **City Data** | Ottawa Open Data Portal | Free |
| **Transit Data** | OC Transpo GTFS | Free |

**Total running cost: $0** — everything runs locally on your own machine.

---

## 👥 Team

Built at the University of Ottawa.

---

## 📄 License

This project is for educational purposes as part of university coursework.
