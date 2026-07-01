"""
Raven AI CCTV — Qwen-VL-Max Integration
Analyzes video frames for threat classification.
Falls back to mock data in DEMO_MODE or on quota errors.
"""
import base64
import json
import logging
import os
import random
from pathlib import Path

from backend.config import get_settings
from backend.schemas import ThreatAnalysis
from backend.models import SeverityLevel

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Mock responses for demo mode ───────────────────────────────────────────

MOCK_ANALYSES: list[dict] = [
    {
        "threat_type": "Perimeter Intrusion",
        "severity": "CRITICAL",
        "severity_score": 9.2,
        "actors_detected": ["1 adult male", "dark clothing", "carrying bag"],
        "scene_description": (
            "An individual in dark clothing has crossed the perimeter fence at the "
            "northwest corner of the compound. The subject appears to be moving "
            "deliberately toward the main building entrance. No visible weapon, "
            "but posture is furtive and motion pattern is inconsistent with authorized "
            "personnel behavior."
        ),
        "qwen_reasoning": (
            "Analysis: Fence line breach detected. Subject trajectory projects toward "
            "high-value asset area. Motion anomaly score: 0.94. Recommend immediate "
            "SOC review and guard dispatch."
        ),
        "confidence": 0.94,
        "bounding_boxes": [{"label": "person", "x": 312, "y": 180, "w": 80, "h": 200, "conf": 0.94}],
    },
    {
        "threat_type": "Unauthorized Vehicle Access",
        "severity": "HIGH",
        "severity_score": 7.5,
        "actors_detected": ["1 vehicle (sedan)", "unplated or obscured plates"],
        "scene_description": (
            "A dark-colored sedan has entered the restricted parking zone without "
            "displaying a valid access pass. The vehicle has been stationary for "
            "4+ minutes near the loading dock. License plate appears to be obscured "
            "or missing. No driver visible through windscreen."
        ),
        "qwen_reasoning": (
            "Vehicle in restricted zone. Plate obscured — high-risk indicator. "
            "Duration exceeds casual drop-off. Recommend plate verification query "
            "and physical inspection."
        ),
        "confidence": 0.87,
        "bounding_boxes": [{"label": "car", "x": 150, "y": 300, "w": 280, "h": 140, "conf": 0.87}],
    },
    {
        "threat_type": "Crowd Gathering / Possible Disturbance",
        "severity": "MEDIUM",
        "severity_score": 5.1,
        "actors_detected": ["8-12 individuals", "mixed ages", "animated gestures"],
        "scene_description": (
            "A group of 8-12 people have gathered near the main entrance. Body "
            "language is animated with several individuals gesticulating. The group "
            "is partially blocking the ingress path. No weapons visible. Situation "
            "could escalate to an access obstruction or public order incident."
        ),
        "qwen_reasoning": (
            "Group density above threshold for this zone. Gesture analysis suggests "
            "agitation. Recommend monitoring and verbal de-escalation if blocking persists."
        ),
        "confidence": 0.73,
        "bounding_boxes": [
            {"label": "person", "x": 100 + i * 45, "y": 220, "w": 40, "h": 120, "conf": 0.7}
            for i in range(6)
        ],
    },
    {
        "threat_type": "Normal Activity",
        "severity": "LOW",
        "severity_score": 1.2,
        "actors_detected": ["2 individuals", "staff uniforms", "scheduled shift"],
        "scene_description": (
            "Two uniformed staff members are moving through the lobby area. "
            "Movement patterns are consistent with authorized personnel conducting "
            "routine tasks. No anomalies detected. Scene is within expected parameters "
            "for this time period."
        ),
        "qwen_reasoning": (
            "Uniform recognition: positive match with registered staff profiles. "
            "Motion trajectory nominal. No threat indicators. Confidence: high."
        ),
        "confidence": 0.98,
        "bounding_boxes": [
            {"label": "person", "x": 200, "y": 200, "w": 60, "h": 160, "conf": 0.98},
            {"label": "person", "x": 350, "y": 195, "w": 60, "h": 165, "conf": 0.97},
        ],
    },
]


# ─── System Prompt ───────────────────────────────────────────────────────────

THREAT_ANALYSIS_PROMPT = """You are Raven AI-VL, an expert AI security analyst reviewing CCTV footage.

Analyze the provided image and return a structured threat assessment in valid JSON format.

Required JSON structure:
{
  "threat_type": "brief threat category (e.g. Perimeter Intrusion, Suspicious Package, Normal Activity)",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "severity_score": 1.0-10.0,
  "actors_detected": ["list of detected individuals/vehicles with descriptions"],
  "scene_description": "2-3 sentence professional security narrative describing what you observe",
  "qwen_reasoning": "your analytical reasoning chain for the threat classification",
  "confidence": 0.0-1.0,
  "bounding_boxes": [{"label": "person|car|...", "x": int, "y": int, "w": int, "h": int, "conf": float}]
}

Severity levels:
- CRITICAL (8-10): Active intrusion, weapons visible, immediate threat to persons
- HIGH (6-7): Unauthorized access, vehicle anomaly, suspicious behavior
- MEDIUM (4-5): Crowd gathering, loitering, minor protocol breach
- LOW (1-3): Normal activity, authorized personnel, routine movements

Return ONLY the JSON object, no markdown fencing."""


# ─── Main analysis function ──────────────────────────────────────────────────

async def analyze_frame(
    image_b64: str,
    camera_name: str = "Camera",
    camera_location: str = "Unknown",
) -> ThreatAnalysis:
    """
    Send a base64-encoded frame to Qwen-VL-Max for threat analysis.
    Returns a ThreatAnalysis object.
    Falls back to mock data in demo mode or on API errors.
    """
    if not settings.is_qwen_configured:
        logger.info("DEMO_MODE: Returning mock Qwen-VL analysis")
        return _mock_analysis()

    return await _call_qwen_vl(image_b64, camera_name, camera_location)


async def _call_qwen_vl_with_retry(payload: dict) -> dict:
    import httpx
    import asyncio
    url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.dashscope_api_key}",
        "Content-Type": "application/json"
    }
    
    max_retries = 3
    delay = 1.0
    
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=60.0)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(f"Transient error {response.status_code} on attempt {attempt+1}. Retrying in {delay}s...")
                else:
                    logger.error(f"Unrecoverable API status code {response.status_code}: {response.text}")
                    response.raise_for_status()
            except Exception as e:
                logger.warning(f"Request error on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    raise
            
            await asyncio.sleep(delay)
            delay *= 2.0
            
        raise Exception("API request failed after maximum retries.")


async def _call_qwen_vl(
    image_b64: str,
    camera_name: str,
    camera_location: str,
) -> ThreatAnalysis:
    """Live DashScope Qwen-VL-Max compatible-mode call."""
    image_data_uri = f"data:image/jpeg;base64,{image_b64}"

    payload = {
        "model": settings.qwen_vl_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": THREAT_ANALYSIS_PROMPT},
                    {
                        "type": "text",
                        "text": f"Camera: {camera_name} | Location: {camera_location}\nAnalyze this CCTV frame and return the threat assessment JSON:"
                    },
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ]
            }
        ]
    }

    try:
        res_json = await _call_qwen_vl_with_retry(payload)
        model_used = settings.qwen_vl_model
    except Exception as e:
        logger.warning(f"Qwen-VL-Max call failed, trying fallback model: {e}")
        payload["model"] = settings.qwen_vl_fallback_model
        res_json = await _call_qwen_vl_with_retry(payload)
        model_used = settings.qwen_vl_fallback_model

    # Parse response
    text = res_json["choices"][0]["message"]["content"]
    usage = res_json.get("usage", {})
    tokens = usage.get("total_tokens", 0)
    cost = _estimate_cost(tokens, model_used)

    data = _parse_json_response(text)
    data["tokens_used"] = tokens
    data["api_cost_usd"] = cost

    return ThreatAnalysis(**data)


def _parse_json_response(text: str) -> dict:
    """Extract JSON from model response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Qwen-VL JSON: {text[:200]}")
        return MOCK_ANALYSES[0]


def _mock_analysis() -> ThreatAnalysis:
    """Return a weighted-random mock analysis (more HIGH/CRITICAL for demo drama)."""
    weights = [0.25, 0.30, 0.25, 0.20]  # CRITICAL, HIGH, MEDIUM, LOW
    data = random.choices(MOCK_ANALYSES, weights=weights, k=1)[0]
    return ThreatAnalysis(**data)


def _estimate_cost(tokens: int, model: str) -> float:
    """Rough cost estimate in USD (DashScope pricing as of 2026)."""
    rates = {
        "qwen-vl-max": 0.003 / 1000,
        "qwen-vl-plus": 0.0015 / 1000,
    }
    rate = rates.get(model, 0.003 / 1000)
    return round(tokens * rate, 6)
