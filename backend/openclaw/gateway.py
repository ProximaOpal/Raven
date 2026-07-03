"""
Raven AI CCTV — OpenClaw Gateway lifecycle helpers.
Checks gateway health and auto-starts when unreachable.
"""
import asyncio
import logging

import websockets

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_gateway_process: asyncio.subprocess.Process | None = None


async def is_gateway_reachable(timeout: float = 2.0) -> bool:
    """Return True if the OpenClaw WebSocket gateway accepts connections."""
    url = settings.openclaw_gateway_url
    try:
        async with websockets.connect(url, open_timeout=timeout, close_timeout=1):
            return True
    except Exception:
        return False


async def ensure_openclaw_gateway() -> asyncio.subprocess.Process | None:
    """
    Start `openclaw gateway start` if the gateway is not already reachable.
    Returns the subprocess handle when spawned, otherwise None.
    """
    global _gateway_process

    if await is_gateway_reachable():
        logger.info("OpenClaw Gateway already reachable at %s", settings.openclaw_gateway_url)
        return None

    logger.info("OpenClaw Gateway not reachable — launching: openclaw gateway start")
    try:
        _gateway_process = await asyncio.create_subprocess_exec(
            "openclaw",
            "gateway",
            "start",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning(
            "openclaw CLI not found on PATH — gateway auto-start skipped. "
            "Install OpenClaw or start the gateway manually."
        )
        return None
    except Exception as e:
        logger.error("Failed to spawn OpenClaw gateway: %s", e)
        return None

    for attempt in range(20):
        await asyncio.sleep(1)
        if await is_gateway_reachable():
            logger.info("OpenClaw Gateway started and verified (attempt %d)", attempt + 1)
            return _gateway_process

    logger.warning(
        "OpenClaw Gateway subprocess started but not yet reachable after 20s — "
        "bridge will retry connection."
    )
    return _gateway_process


async def shutdown_openclaw_gateway() -> None:
    """Terminate auto-started gateway subprocess on app shutdown."""
    global _gateway_process
    if _gateway_process and _gateway_process.returncode is None:
        logger.info("Stopping auto-started OpenClaw Gateway subprocess")
        _gateway_process.terminate()
        try:
            await asyncio.wait_for(_gateway_process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            _gateway_process.kill()
            await _gateway_process.wait()
    _gateway_process = None
