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
    """
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
