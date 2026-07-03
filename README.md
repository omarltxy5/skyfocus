# SkyFocus

Real-time open-source aviation intelligence platform. Fuses live ADS-B telemetry with METAR weather data to infer aircraft behavior (active runways, flight phases, go-arounds).

## Repository layout

```
Skyfocus/
├── backend/          # FastAPI + Uvicorn (Python 3.10+)
│   ├── app/
│   │   ├── api/          # REST + WebSocket (Step 3)
│   │   ├── inference/    # Runway, phase, Douglas–Peucker (Step 2)
│   │   ├── ingestion/    # ADS-B + METAR loops (Step 3)
│   │   ├── state/        # In-memory telemetry cache (Step 3)
│   │   ├── config.py
│   │   └── main.py
│   └── requirements.txt
└── frontend/         # React + Vite + Leaflet + Tailwind
    ├── src/
    │   ├── components/
    │   ├── services/
    │   └── types/
    └── package.json
```

## Prerequisites

- **Python** 3.10 or newer
- **Node.js** 18+ and npm (for the frontend)

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Dev server: [http://localhost:5173](http://localhost:5173) (API/WebSocket proxied to port 8000)

## Quick start (working UI)

**Terminal 1 — backend** (stop any old process on port 8000 first):

```powershell
cd C:\Users\Omar\Documents\Skyfocus\backend
.\run.ps1
```

**Terminal 2 — frontend:**

```powershell
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). You should see live aircraft near NYC, KJFK METAR/runway intel in the sidebar, and phase-colored markers (red pulsing = go-around).

Live OpenSky ADS-B is **on by default**. Copy `backend/.env.example` to `backend/.env` and set `SKYFOCUS_USE_MOCK_ADSB=true` only for offline demo mode.

**Airports:** blue pins — runway + METAR inference for **any** indexed airport with OurAirports runway data. Map opens at your nearest airport (IP geolocation).

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/airports` | Airport layer (bbox or top 500 hubs) |
| `GET /api/v1/airports/{icao}/intelligence` | Active runway + wind components |
| `GET /api/v1/flights/{callsign}/state` | Fused flight state |
| `WS /ws/telemetry` | Subscribe with `{"type":"subscribe","bbox":[south,west,north,east]}` |

## Development roadmap

| Step | Status |
|------|--------|
| 1 | Project scaffolding |
| 2 | Inference engine (METAR, runway, phase, Douglas–Peucker) |
| 3 | FastAPI server, cache, REST, WebSocket |
| 4–5 | Leaflet map, WebSocket client, phase styling UI |

## License

Open source — license TBD.
