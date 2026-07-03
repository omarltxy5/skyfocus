# SkyFocus Backend

FastAPI application for ADS-B + METAR fusion and aviation intelligence APIs.

## Run locally

**Always run from the `backend/` folder** (not from `.venv\Scripts`), or use the helper script:

```powershell
cd C:\Users\Omar\Documents\Skyfocus\backend
.\run.ps1
```

Manual start:

```powershell
cd C:\Users\Omar\Documents\Skyfocus\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If you see `ModuleNotFoundError: No module named 'app'`, your terminal cwd is wrong — `cd` to `backend` first.

## Airport database (OurAirports)

```powershell
python scripts/build_airports_db.py
```

Produces `data/airports.json` (5,013 medium/large airports, top 500 hub index) and `data/runways.json` (runway headings for global inference).

```powershell
python scripts/build_airports_db.py
python scripts/build_runways_db.py
```

## Geo home

`GET /api/v1/geo/home` — resolves client IP to lat/lon and returns the nearest indexed airport (used to center the map on load).

## Inference engine (Step 2)

```powershell
python -m unittest tests.test_inference -v
```

Modules under `app/inference/`: `metar`, `runway`, `phase`, `trajectory`.

## Environment variables

Optional `.env` in `backend/` with `SKYFOCUS_` prefix, e.g.:

```
SKYFOCUS_DEBUG=true
SKYFOCUS_PORT=8000
```

See `app/config.py` for all settings.
