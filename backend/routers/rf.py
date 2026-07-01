"""
NEXUS CCTV — RF / Wi-Fi Spatial Intelligence Router
GET /api/rf/aps, GET /api/rf/telemetry, POST /api/rf/simulate-move
"""
from fastapi import APIRouter, HTTPException
from backend.services.rf_sensor import RFSensorService
from backend.ws_manager import ws_manager
from pydantic import BaseModel

router = APIRouter(prefix="/api/rf", tags=["rf"])

class RFMoveRequest(BaseModel):
    x: float
    y: float

@router.get("/aps")
async def get_aps():
    """Returns locations and specifications of virtual Wi-Fi access points."""
    return RFSensorService.get_aps()

@router.get("/telemetry")
async def get_telemetry():
    """Returns active real-time RSSI and CSI telemetry, plus estimated target coordinates."""
    telemetry = RFSensorService.get_telemetry()
    return telemetry

@router.post("/simulate-move")
async def simulate_move(body: RFMoveRequest):
    """Triggers simulated occupant movement towards a coordinate (e.g. following camera events)."""
    RFSensorService.simulate_move_trigger(body.x, body.y)
    
    # Generate fresh telemetry and broadcast immediately to socket
    telemetry = RFSensorService.get_telemetry()
    await ws_manager.broadcast_rf_telemetry(telemetry)
    return {"status": "moved", "telemetry": telemetry}
