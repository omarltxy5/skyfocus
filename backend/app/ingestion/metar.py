"""METAR ingestion from Aviation Weather Center API."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.inference.metar import parse_metar
from app.data.airports_index import airport_index
from app.state.telemetry import store

logger = logging.getLogger(__name__)

AWC_METAR_URL = "https://aviationweather.gov/api/data/metar"


async def fetch_metar_batch(icao_list: list[str]) -> None:
    if not icao_list:
        return
    ids = ",".join(icao_list)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            AWC_METAR_URL,
            params={"ids": ids, "format": "raw"},
        )
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                report = parse_metar(line)
                await store.set_metar(report.icao, report)
                logger.debug("METAR updated %s", report.icao)
            except ValueError as exc:
                logger.warning("METAR parse skip: %s (%s)", line[:40], exc)


async def poll_metar_loop(interval_sec: float) -> None:
    airport_index.load()
    airports = [a.icao for a in airport_index.top_hubs(200)]
    while True:
        try:
            await fetch_metar_batch(airports)
        except Exception:
            logger.exception("METAR poll failed")
        await asyncio.sleep(interval_sec)
