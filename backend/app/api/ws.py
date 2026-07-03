"""WebSocket telemetry broadcaster with bounding-box subscriptions."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.schemas import FlightDeltaSchema, WsUpdateMessage
from app.state.telemetry import store

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@dataclass
class WsClient:
    websocket: WebSocket
    bbox: tuple[float, float, float, float] = (39.0, -76.0, 42.0, -72.0)


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: list[WsClient] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> WsClient:
        await websocket.accept()
        client = WsClient(websocket=websocket)
        async with self._lock:
            self._clients.append(client)
        return client

    async def disconnect(self, client: WsClient) -> None:
        async with self._lock:
            if client in self._clients:
                self._clients.remove(client)

    async def set_bbox(
        self, client: WsClient, south: float, west: float, north: float, east: float
    ) -> None:
        client.bbox = (south, west, north, east)

    async def broadcast_tick(self) -> None:
        async with self._lock:
            clients = list(self._clients)
        now = time.time()
        for client in clients:
            south, west, north, east = client.bbox
            flights = await store.flights_in_bbox(south, west, north, east)
            deltas = [
                FlightDeltaSchema(
                    icao24=f.icao24,
                    callsign=f.callsign,
                    phase=f.phase.value,
                    go_around=f.go_around,
                    latitude=f.latitude,
                    longitude=f.longitude,
                    altitude_ft=f.altitude_ft,
                    vertical_speed_fpm=f.vertical_speed_fpm,
                    heading_deg=f.heading_deg,
                    ground_speed_kt=f.ground_speed_kt,
                    inferred_runway=f.inferred_runway,
                    nearest_airport=f.nearest_airport,
                )
                for f in flights
            ]
            msg = WsUpdateMessage(type="update", flights=deltas, ts=now)
            try:
                await client.websocket.send_text(msg.model_dump_json())
            except Exception:
                logger.debug("WS send failed")


manager = ConnectionManager()


@ws_router.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket) -> None:
    client = await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("type") != "subscribe":
                continue
            bbox = data.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            await manager.set_bbox(
                client,
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            )
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(client)


async def ws_broadcast_loop(interval_sec: float = 2.0) -> None:
    while True:
        await manager.broadcast_tick()
        await asyncio.sleep(interval_sec)
