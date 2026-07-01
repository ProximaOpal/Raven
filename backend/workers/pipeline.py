"""
NEXUS CCTV — Celery Pipeline Workers
Background tasks: frame processing, Qwen analysis, alert dispatch.
"""
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone

from celery import Celery

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "nexus",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.workers.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def run_async(coro):
    """Run an async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="nexus.process_frame", bind=True, max_retries=2)
def process_frame(self, camera_id: int, image_b64: str):
    """
    Delegate CCTV frame processing to the AgentX OpenClaw Agentic Runtime.
    """
    logger.info(f"Processing frame for camera #{camera_id} via AgentX Runtime")
    return run_async(_async_pipeline(camera_id, image_b64))


async def _async_pipeline(camera_id: int, image_b64: str) -> dict:
    """Async portion of the pipeline running the AgentX Agentic core."""
    from backend.openclaw.agentx_runtime import AgentXRuntime
    try:
        return await AgentXRuntime.run_agentx_pipeline(camera_id, image_b64)
    except Exception as e:
        logger.error(f"AgentX pipeline runtime execution failed: {e}")
        return {"status": "error", "reason": str(e)}
