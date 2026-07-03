"""
Raven AI CCTV — WebSocket Connection Manager
Manages SOC dashboard real-time push connections.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for the SOC dashboard."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS connected. Total: {len(self.active_connections)}")

        # Send welcome ping
        await self.send_personal(websocket, {
            "event": "ping",
            "data": {"message": "Raven AI SOC dashboard connected", "connections": len(self.active_connections)},
        })

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WS disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, websocket: WebSocket, payload: dict) -> None:
        try:
            payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            await websocket.send_text(json.dumps(payload, default=str))
        except Exception as e:
            logger.error(f"WS personal send error: {e}")

    async def broadcast(self, payload: dict) -> None:
        """Broadcast an event to all connected SOC clients."""
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        message = json.dumps(payload, default=str)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_incident(self, incident_data: dict[str, Any]) -> None:
        await self.broadcast({
            "event": "incident_new",
            "data": incident_data,
        })

    async def broadcast_incident_update(self, incident_data: dict[str, Any]) -> None:
        await self.broadcast({
            "event": "incident_updated",
            "data": incident_data,
        })

    async def broadcast_alert(self, alert_data: dict[str, Any]) -> None:
        await self.broadcast({
            "event": "alert_sent",
            "data": alert_data,
        })

    async def broadcast_rf_telemetry(self, telemetry_data: dict[str, Any]) -> None:
        await self.broadcast({
            "event": "rf_telemetry",
            "data": telemetry_data,
        })

    async def broadcast_detection(self, detection_data: dict[str, Any]) -> None:
        """Broadcast YOLO pre-filter detections (before Qwen-VL reasoning)."""
        await self.broadcast({
            "event": "yolo_detection",
            "data": detection_data,
        })

    async def broadcast_frame_skipped(self, skip_data: dict[str, Any]) -> None:
        """Broadcast when a frame is dropped by the YOLO pre-filter."""
        await self.broadcast({
            "event": "frame_skipped",
            "data": skip_data,
        })

    async def broadcast_pipeline_log(self, log_data: dict[str, Any]) -> None:
        """Broadcast pipeline activity for the debug console."""
        await self.broadcast({
            "event": "pipeline_log",
            "data": log_data,
        })

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Global singleton
ws_manager = ConnectionManager()
