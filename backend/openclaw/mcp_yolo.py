"""
Raven AI CCTV — YOLO Filter MCP Server
Exposes the object pre-filter tool for OpenClaw.
"""
import sys
import base64
import json
import numpy as np
import cv2
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.openclaw.mcp_helper import MCPServer
from backend.services.yolo_filter import detect_targets, detections_to_boxes

server = MCPServer("yolo-filter-mcp")

@server.tool(
    name="detect_objects",
    description="Pre-filters raw CCTV frames using YOLOv8 to detect targets before executing LLM vision analysis.",
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
def detect_objects(image_b64: str) -> dict:
    try:
        # Strip data URI prefix if present
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        img_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"has_targets": True, "detections": [], "error": "Invalid image data"}
            
        result = detect_targets(frame)
        boxes = detections_to_boxes(result)
        return {
            "has_targets": result.has_targets,
            "detections": boxes
        }
    except Exception as e:
        print(f"[YOLO MCP] Error in tool execution: {e}", file=sys.stderr)
        return {"has_targets": True, "detections": [], "error": str(e)}

if __name__ == "__main__":
    server.run()
