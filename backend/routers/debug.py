"""
Raven AI CCTV — Debug / Diagnostics Router
GET /api/debug/status — aggregated system state for the debug console
"""
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config import get_settings

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)

# Ring buffer for recent pipeline log lines (shared with AgentX runtime)
DEBUG_LOG_BUFFER: deque[dict] = deque(maxlen=500)


def append_debug_log(level: str, source: str, message: str, **extra) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "message": message,
        **extra,
    }
    DEBUG_LOG_BUFFER.appendleft(entry)


@router.get("/status")
async def debug_status():
    """Return aggregated health, pipeline, and OpenClaw state."""
    from backend.openclaw.gateway import is_gateway_reachable
    from backend.database import AsyncSessionLocal
    from backend.models import Camera, Incident, IncidentStatus
    from backend.services.yolo_filter import _get_model
    from sqlalchemy import select, func
    from datetime import date

    settings = get_settings()
    gateway_ok = await is_gateway_reachable(timeout=1.5)

    async with AsyncSessionLocal() as db:
        cameras = await db.scalar(select(func.count(Camera.id)))
        pending = await db.scalar(
            select(func.count(Incident.id)).where(Incident.status == IncidentStatus.PENDING)
        )

    yolo_loaded = _get_model() is not None

    return {
        "service": "Raven AI CCTV",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "demo_mode": settings.demo_mode,
        "openclaw_gateway": {
            "url": settings.openclaw_gateway_url,
            "reachable": gateway_ok,
            "token_configured": bool(settings.openclaw_gateway_token),
        },
        "qwen": {
            "configured": settings.is_qwen_configured,
            "model": settings.qwen_vl_model,
            "base_url": settings.dashscope_openai_base_url,
        },
        "yolo": {"model_loaded": yolo_loaded},
        "pipeline": {
            "cameras_active": cameras or 0,
            "pending_review": pending or 0,
        },
        "ws_connections": __import__("backend.ws_manager", fromlist=["ws_manager"]).ws_manager.connection_count,
    }


@router.get("/logs")
async def debug_logs(limit: int = 100):
    """Return recent pipeline log entries."""
    limit = min(max(limit, 1), 500)
    return {"logs": list(DEBUG_LOG_BUFFER)[:limit]}
