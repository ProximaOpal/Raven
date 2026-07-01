"""
NEXUS CCTV — OpenClaw WebSocket Gateway Bridge
Connects to ws://127.0.0.1:18789, authenticates, and routes triggers to AgentX pipeline.
"""
import json
import logging
import asyncio
import websockets
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.openclaw.agentx_runtime import AgentXRuntime
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OPENCLAW_WS_URL = "ws://127.0.0.1:18789"
GATEWAY_TOKEN = "c2dae22b5ee180a947c0b1c38d718e7464dcb24b453f1bef"

async def start_openclaw_bridge():
    """Main loop connecting and listening to the OpenClaw Gateway WebSocket."""
    retry_delay = 2.0
    
    while True:
        try:
            logger.info(f"Connecting to OpenClaw Gateway at {OPENCLAW_WS_URL}...")
            async with websockets.connect(OPENCLAW_WS_URL) as ws:
                logger.info("WebSocket connected. Sending authentication handshake...")
                
                # Send the connect/auth payload
                handshake = {
                    "event": "connect",
                    "data": {
                        "auth": {
                            "token": GATEWAY_TOKEN
                        }
                    }
                }
                await ws.send(json.dumps(handshake))
                
                # Reset retry delay on successful connection
                retry_delay = 2.0
                logger.info("OpenClaw gateway connection verified. Awaiting triggers...")
                
                # Listen for messages
                async for message in ws:
                    try:
                        payload = json.loads(message)
                        event = payload.get("event")
                        data = payload.get("data", {})
                        
                        if event == "camera_trigger":
                            camera_id = data.get("camera_id")
                            image_b64 = data.get("image_b64")
                            if camera_id and image_b64:
                                logger.info(f"Received camera_trigger event for camera #{camera_id}")
                                # Execute AgentX loop in background task to avoid blocking bridge
                                asyncio.create_task(
                                    AgentXRuntime.run_agentx_pipeline(camera_id, image_b64)
                                )
                            else:
                                logger.warning("Received camera_trigger with missing parameters.")
                                
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse websocket message: {message[:200]}")
                    except Exception as e:
                        logger.error(f"Error handling gateway message: {e}")
                        
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"Connection lost to OpenClaw gateway: {e}. Retrying in {retry_delay}s...")
        except Exception as e:
            logger.error(f"Unexpected error in OpenClaw bridge: {e}. Retrying in {retry_delay}s...")
            
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60.0)  # Exponential backoff capped at 60s
