"""
SkyFocus FastAPI entrypoint — REST, WebSocket, ingestion.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.geo import geo_router
from app.api.routes import router as api_router
from app.api.ws import ws_router
from app.config import settings
from app.data.airports_index import airport_index
from app.inference.runways_data import runway_index
from app.ingestion.service import start_ingestion

logging.basicConfig(level=logging.INFO if settings.debug else logging.WARNING)
logger = logging.getLogger(__name__)

_ingestion_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ingestion_tasks
    airport_index.load()
    runway_index.load()
    _ingestion_tasks = await start_ingestion()
    yield
    for task in _ingestion_tasks:
        task.cancel()
    await asyncio.gather(*_ingestion_tasks, return_exceptions=True)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Real-time aviation intelligence — ADS-B + METAR fusion",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(geo_router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str | int | bool]:
    from app.state.telemetry import store

    return {
        "status": "ok",
        "service": settings.app_name,
        "use_mock_adsb": settings.use_mock_adsb,
        "aircraft_tracked": await store.flight_count(),
        "airports_indexed": airport_index.count(),
    }
