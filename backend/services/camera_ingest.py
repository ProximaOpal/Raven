"""
Raven AI CCTV — Camera Ingest
Handles RTSP streams, file uploads, and mock camera feeds.
"""
import asyncio
import base64
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DEMO_IMAGES_DIR = Path(__file__).parent.parent.parent / "demo" / "sample_incidents"

# Mock camera definitions for demo
MOCK_CAMERAS = [
    {"id": 1, "name": "CAM-01 — Main Gate", "location": "North Perimeter Gate"},
    {"id": 2, "name": "CAM-02 — Parking Zone A", "location": "East Parking Area"},
    {"id": 3, "name": "CAM-03 — Lobby CCTV", "location": "Main Building Lobby"},
    {"id": 4, "name": "CAM-04 — Server Room", "location": "B2 Data Center"},
]


def encode_image_to_b64(image_path: str | Path) -> str:
    """Read an image file and return its base64 encoding."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def capture_rtsp_frame(rtsp_url: str) -> bytes | None:
    """
    Capture a single frame from an RTSP stream using OpenCV.
    Returns raw JPEG bytes or None on failure.
    """
    try:
        import cv2
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return buffer.tobytes()
    except Exception as e:
        logger.error(f"RTSP capture failed for {rtsp_url}: {e}")
        return None


def get_mock_frame_b64(severity_hint: str | None = None) -> tuple[str, str]:
    """
    Return a (base64_image, filename) pair from demo images.
    Optionally biased toward a specific severity.
    """
    if not DEMO_IMAGES_DIR.exists():
        # Return a tiny 1x1 gray JPEG if no demo images
        return _minimal_gray_b64(), "fallback.jpg"

    images = list(DEMO_IMAGES_DIR.glob("*.jpg")) + list(DEMO_IMAGES_DIR.glob("*.png"))
    if not images:
        return _minimal_gray_b64(), "fallback.jpg"

    # Bias selection toward higher-severity images for drama
    weights_map = {
        "fence_intrusion": 3,
        "vehicle": 2,
        "crowd": 2,
        "lobby": 1,
    }
    weighted = []
    weights = []
    for img in images:
        w = 1
        for key, val in weights_map.items():
            if key in img.stem.lower():
                w = val
                break
        weighted.append(img)
        weights.append(w)

    chosen = random.choices(weighted, weights=weights, k=1)[0]
    return encode_image_to_b64(chosen), chosen.name


def _minimal_gray_b64() -> str:
    """Return a 1x1 gray JPEG as base64 (fallback when no demo images)."""
    # Minimal valid JPEG
    data = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
        b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00"
        b"\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00"
        b"\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81"
        b"\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19"
        b"\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\xff\xda\x00\x08"
        b"\x01\x01\x00\x00?\x00\xf5\x00\xff\xd9"
    )
    return base64.b64encode(data).decode()


async def mock_camera_stream(
    camera_id: int,
    interval_seconds: float = 5.0,
    on_frame=None,
):
    """
    Async generator that yields mock frames at a fixed interval.
    Calls on_frame(camera_id, image_b64) if provided.
    """
    logger.info(f"Mock camera stream started: camera_id={camera_id}, interval={interval_seconds}s")
    while True:
        await asyncio.sleep(interval_seconds)
        b64, fname = get_mock_frame_b64()
        if on_frame:
            await on_frame(camera_id, b64)
        yield camera_id, b64, fname
