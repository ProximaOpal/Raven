"""
Raven AI CCTV — WebSocket Router
WS /ws/soc — Real-time SOC dashboard push
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.ws_manager import ws_manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/soc")
async def soc_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for the SOC dashboard.
    Receives real-time incident, alert, and status events.
    Requires a valid access token query param or first message, unless in demo mode.
    """
    from backend.config import get_settings
    from jose import jwt, JWTError
    import asyncio
    import json

    settings = get_settings()
    token = websocket.query_params.get("token")
    is_valid = False

    if settings.demo_mode:
        is_valid = True
    elif token:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            if payload.get("sub"):
                is_valid = True
        except JWTError:
            pass

    if not is_valid:
        # Fallback to waiting for the first message
        await websocket.accept()
        try:
            # Wait for first message within 5 seconds
            message_str = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg_data = json.loads(message_str)
            token = msg_data.get("token")
            if token:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                if payload.get("sub"):
                    is_valid = True
        except Exception:
            pass

        if not is_valid:
            # Policy violation
            await websocket.close(code=1008)
            return
    else:
        await websocket.accept()

    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep alive — listen for pings from the client
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_personal(websocket, {"event": "pong", "data": {}})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("SOC client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

