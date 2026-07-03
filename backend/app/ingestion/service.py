"""Background ingestion orchestration."""

from __future__ import annotations

import asyncio
import logging

from app.api.ws import manager, ws_broadcast_loop
from app.config import settings
from app.ingestion.adsb import poll_adsb_loop
from app.ingestion.metar import fetch_metar_batch, poll_metar_loop
from app.data.airports_index import airport_index

logger = logging.getLogger(__name__)


async def start_ingestion() -> list[asyncio.Task]:
    from app.ingestion.adsb import _advance_mock, fetch_opensky
    from app.state.telemetry import store

    # Prime METAR and telemetry before first WebSocket tick
    try:
        hub_icaos = [a.icao for a in airport_index.top_hubs(120)]
        await fetch_metar_batch(hub_icaos)
    except Exception:
        logger.exception("Initial METAR fetch failed")

    try:
        if settings.use_mock_adsb:
            await store.upsert_mock_states(_advance_mock())
        else:
            n = await fetch_opensky(bbox=None)
            logger.info("Initial OpenSky ingest: %d aircraft", n)
    except Exception:
        logger.exception("Initial telemetry seed failed")

    tasks = [
        asyncio.create_task(
            poll_adsb_loop(settings.adsb_poll_interval_sec, settings.use_mock_adsb),
            name="adsb_poll",
        ),
        asyncio.create_task(
            poll_metar_loop(settings.metar_poll_interval_sec),
            name="metar_poll",
        ),
        asyncio.create_task(
            ws_broadcast_loop(settings.ws_broadcast_interval_sec),
            name="ws_broadcast",
        ),
    ]
    logger.info("Ingestion started (%d tasks)", len(tasks))
    return tasks
