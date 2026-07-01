"""
NEXUS CCTV — Forensics Signer MCP Server
Exposes the evidence package sealing and signing tool.
"""
import sys
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.openclaw.mcp_helper import MCPServer
from backend.services.evidence_package import generate_evidence_package
from backend.database import AsyncSessionLocal
from backend.models import Incident, Camera

server = MCPServer("forensics-signer-mcp")

async def run_evidence_sealing(incident_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        inc = await db.get(Incident, incident_id)
        if not inc:
            return {"signed": False, "error": f"Incident {incident_id} not found"}
            
        camera = await db.get(Camera, inc.camera_id)
        cam_name = camera.name if camera else "Unknown"
        cam_loc = camera.location if camera else "Unknown"
        
        try:
            pkg = await generate_evidence_package(inc, cam_name, cam_loc)
            
            # Save signature back to DB
            inc.pdf_path = pkg["pdf_path"]
            inc.archive_path = pkg["archive_path"]
            inc.sha256_hash = pkg["sha256_hash"]
            await db.commit()
            
            return {
                "signed": True,
                "pdf_path": pkg["pdf_path"],
                "archive_path": pkg["archive_path"],
                "sha256_hash": pkg["sha256_hash"]
            }
        except Exception as e:
            return {"signed": False, "error": str(e)}

@server.tool(
    name="seal_evidence_package",
    description="Generates the SHA-256 signed evidence report and adds the tamper-evident signature.",
    input_schema={
        "type": "object",
        "properties": {
            "incident_id": {
                "type": "integer",
                "description": "ID of the incident to seal and sign."
            }
        },
        "required": ["incident_id"]
    }
)
def seal_evidence_package(incident_id: int) -> dict:
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(run_evidence_sealing(incident_id))
        finally:
            loop.close()
    except Exception as e:
        print(f"[Forensics MCP] Error: {e}", file=sys.stderr)
        return {"signed": False, "error": str(e)}

if __name__ == "__main__":
    server.run()
