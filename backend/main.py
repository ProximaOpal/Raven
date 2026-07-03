"""
Raven AI CCTV — FastAPI Application Factory
Entry point: uvicorn backend.main:app
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import get_settings
from backend.database import init_db
from backend.routers import auth, cameras, evidence, incidents, search, ws, audit, biometrics, rf

import time
from collections import OrderedDict
import threading
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens=1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    """
    Thread-safe in-memory rate limiter using a sliding window token bucket.
    Employs LRU-eviction via OrderedDict to cap tracked IP count and prevent memory growth.

    WARNING: This implementation is in-memory and per-process only. If running
    multiple ASGI workers or load-balanced replicas, it will not synchronize
    limits across processes. In production, this should be replaced with a
    Redis-backed rate limiter (e.g., using fastapi-limiter or custom Redis Lua script).
    """
    def __init__(self, capacity: int, refill_rate: float, max_tracked_ips: int = 10000):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.max_tracked_ips = max_tracked_ips
        self.buckets = OrderedDict()
        self.lock = threading.Lock()

    def is_allowed(self, ip: str) -> bool:
        with self.lock:
            if ip in self.buckets:
                # Move to end to mark as most recently used
                self.buckets.move_to_end(ip)
                bucket = self.buckets[ip]
            else:
                # Evict oldest entry (first item) if limit reached
                if len(self.buckets) >= self.max_tracked_ips:
                    self.buckets.popitem(last=False)
                bucket = TokenBucket(self.capacity, self.refill_rate)
                self.buckets[ip] = bucket
        return bucket.consume()

auth_limiter = RateLimiter(capacity=10, refill_rate=0.2)
global_limiter = RateLimiter(capacity=100, refill_rate=10.0)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com https://cdn.jsdelivr.net https://unpkg.com https://esm.sh; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com https://esm.sh; "
            "img-src * data: blob:; "
            "connect-src 'self' ws: wss: http://localhost:* http://127.0.0.1:* "
            "https://raven-klqu.onrender.com https://*.netlify.app https://*.netlify.com "
            "https://proximusraven.app.n8n.cloud;"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        if path.startswith("/api/auth/login") or path.startswith("/api/auth/register") or path.startswith("/api/auth/refresh"):
            if not auth_limiter.is_allowed(ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many auth requests. Please try again later."}
                )
        else:
            if not global_limiter.is_allowed(ip):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Too many requests."}
                )
        return await call_next(request)

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    import asyncio
    
    # Lifespan security check for production environments
    if not settings.demo_mode and settings.secret_key == "raven-dev-secret-change-in-prod":
        logger.critical("CRITICAL: secret_key is set to the default dev value outside DEMO_MODE. Refusing to start.")
        raise RuntimeError("Refusing to start: Default dev secret_key is not permitted in production.")

    logger.info("=" * 60)
    logger.info("  Raven AI CCTV — Autonomous Security Operations")
    logger.info(f"  Demo Mode: {settings.demo_mode}")
    logger.info(f"  Qwen Model: {settings.qwen_vl_model}")
    logger.info(f"  Database: {settings.database_url[:40]}...")
    logger.info("=" * 60)

    # Create DB tables
    await init_db()
    logger.info("Database initialized")

    # Pre-load YOLO model for in-process frame filtering
    from backend.services.yolo_filter import _get_model
    _get_model()
    logger.info("YOLOv8 model pre-loaded for in-process detection")

    # Create evidence store directory
    Path(settings.evidence_store_path).mkdir(parents=True, exist_ok=True)

    # Ensure OpenClaw Gateway is running before bridge connects
    from backend.openclaw.gateway import ensure_openclaw_gateway, shutdown_openclaw_gateway
    await ensure_openclaw_gateway()

    # Start OpenClaw AgentX bridge background task
    from backend.openclaw.bridge import start_openclaw_bridge
    bridge_task = asyncio.create_task(start_openclaw_bridge())
    logger.info("OpenClaw AgentX bridge background task started")

    yield  # Application runs here

    bridge_task.cancel()
    try:
        await bridge_task
    except asyncio.CancelledError:
        pass
    await shutdown_openclaw_gateway()
    logger.info("OpenClaw AgentX bridge task stopped")
    logger.info("Raven AI CCTV shutting down")


app = FastAPI(
    title="Raven AI CCTV — Autonomous Security Operations",
    description=(
        "End-to-end AI-powered CCTV security operations system. "
        "Camera alerts → Qwen-VL-Max analysis → incident report → "
        "multi-channel notification → HITL SOC approval → evidence handoff. "
        "\n\nQwen Cloud Global AI Hackathon 2026 · Track 4: Autopilot Agent"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Middlewares ──────────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(incidents.router)
app.include_router(search.router)
app.include_router(evidence.router)
app.include_router(ws.router)
app.include_router(audit.router)
app.include_router(biometrics.router)
app.include_router(rf.router)

from backend.routers import debug as debug_router
app.include_router(debug_router.router)

# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": "Raven AI CCTV",
        "demo_mode": settings.demo_mode,
        "qwen_model": settings.qwen_vl_model,
        "version": "1.0.0",
    }


@app.get("/api/pipeline/status", tags=["system"])
async def pipeline_status():
    from backend.database import AsyncSessionLocal
    from backend.models import Camera, Incident, Alert, IncidentStatus
    from sqlalchemy import select, func
    from datetime import date

    async with AsyncSessionLocal() as db:
        cameras_active = await db.scalar(select(func.count(Camera.id)))
        incidents_today = await db.scalar(
            select(func.count(Incident.id)).where(func.date(Incident.timestamp) == date.today())
        )
        pending = await db.scalar(
            select(func.count(Incident.id)).where(Incident.status == IncidentStatus.PENDING)
        )
        alerts = await db.scalar(select(func.count(Alert.id)))
        cost = await db.scalar(
            select(func.sum(Incident.api_cost_usd)).where(
                func.date(Incident.timestamp) == date.today()
            )
        )

    return {
        "cameras_active": cameras_active or 0,
        "incidents_today": incidents_today or 0,
        "pending_review": pending or 0,
        "alerts_sent": alerts or 0,
        "api_cost_today_usd": round(float(cost or 0), 4),
        "demo_mode": settings.demo_mode,
        "ws_connections": __import__("backend.ws_manager", fromlist=["ws_manager"]).ws_manager.connection_count,
    }


# ── Static Frontend ───────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(frontend_path / "index.html"))

    @app.get("/farmer-calendar", include_in_schema=False)
    async def serve_farmer_calendar():
        return FileResponse(str(frontend_path / "farmer-calendar.html"))
