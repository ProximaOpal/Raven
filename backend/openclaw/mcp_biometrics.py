"""
Raven AI CCTV — Biometric Matcher MCP Server
Exposes face detection and identification tool.
"""
import sys
import base64
import json
import asyncio
import numpy as np
import cv2
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.openclaw.mcp_helper import MCPServer
from backend.services.biometrics import BiometricsService
from backend.database import AsyncSessionLocal
from backend.models import BiometricProfile
from sqlalchemy import select

server = MCPServer("biometric-matcher-mcp")

async def match_face_in_db(image_b64: str) -> dict:
    # Decode image
    if "," in image_b64:
        image_b64 = image_b64.split(",")[1]
    img_bytes = base64.b64decode(image_b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"matched": False, "name": "Unknown", "role": "Visitor", "confidence": 0.0, "error": "Invalid image"}
        
    faces = BiometricsService.detect_faces(frame)
    if not faces:
        return {"matched": False, "name": "Unknown", "role": "Visitor", "confidence": 0.0, "reason": "No face detected"}
        
    # Take the largest face region
    best_face = max(faces, key=lambda f: f["w"] * f["h"])
    emb = BiometricsService.extract_embedding(frame, best_face)
    
    # Query enrolled profiles
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(BiometricProfile))
        enrolled = res.scalars().all()
        
    match, score = BiometricsService.match_face(emb, enrolled)
    if match:
        return {
            "matched": True,
            "name": match["name"],
            "role": match["role"],
            "confidence": round(score, 3),
            "bbox": best_face
        }
    else:
        return {
            "matched": False,
            "name": "Unknown Person",
            "role": "Visitor",
            "confidence": round(score, 3),
            "bbox": best_face
        }

@server.tool(
    name="match_biometric_face",
    description="Detects a face in base64 frame and compares it against enrolled biometric databases.",
    input_schema={
        "type": "object",
        "properties": {
            "image_b64": {
                "type": "string",
                "description": "Base64-encoded string of the JPEG/PNG image frame."
            }
        },
        "required": ["image_b64"]
    }
)
def match_biometric_face(image_b64: str) -> dict:
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(match_face_in_db(image_b64))
        finally:
            loop.close()
    except Exception as e:
        print(f"[Biometrics MCP] Error: {e}", file=sys.stderr)
        return {"matched": False, "name": "Unknown", "role": "Visitor", "confidence": 0.0, "error": str(e)}

if __name__ == "__main__":
    server.run()
