"""
Raven AI CCTV — Pydantic v2 Schemas (Request / Response models)
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, field_validator

from backend.models import (
    AlertChannel, AlertStatus, CameraStatus, IncidentStatus,
    OperatorRole, SeverityLevel
)


# ─── Camera ─────────────────────────────────────────────────────────────────

class CameraBase(BaseModel):
    name: str
    location: str
    rtsp_url: str | None = None
    is_mock: bool = False


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    rtsp_url: str | None = None
    status: CameraStatus | None = None


class CameraOut(CameraBase):
    id: int
    status: CameraStatus
    created_at: datetime
    last_seen: datetime | None = None
    model_config = {"from_attributes": True}


# ─── Incident ────────────────────────────────────────────────────────────────

class ThreatAnalysis(BaseModel):
    """Output of Qwen-VL-Max analysis — sent as JSON from the model."""
    threat_type: str
    severity: SeverityLevel
    severity_score: float       # 1.0–10.0
    actors_detected: list[str]
    scene_description: str
    qwen_reasoning: str
    confidence: float           # 0.0–1.0
    bounding_boxes: list[dict[str, Any]] = []  # [{label, x, y, w, h, conf}]


class IncidentOut(BaseModel):
    id: int
    camera_id: int
    timestamp: datetime
    threat_type: str | None
    severity: SeverityLevel | None
    severity_score: float | None
    actors_detected: str | None   # JSON-encoded list
    scene_description: str | None
    qwen_reasoning: str | None
    confidence: float | None
    report_en: str | None
    report_sw: str | None
    frame_path: str | None
    pdf_path: str | None
    sha256_hash: str | None
    status: IncidentStatus
    reviewed_at: datetime | None
    tokens_used: int | None
    api_cost_usd: float | None
    camera: CameraOut | None = None
    model_config = {"from_attributes": True}


class IncidentDecision(BaseModel):
    notes: str | None = None


# ─── Alert ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    incident_id: int
    channel: AlertChannel
    recipient: str | None
    status: AlertStatus
    sent_at: datetime
    message_preview: str | None
    error_detail: str | None
    model_config = {"from_attributes": True}


# ─── AuditLog ────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    incident_id: int
    operator_id: int | None
    action: str
    notes: str | None
    timestamp: datetime
    ip_address: str | None
    model_config = {"from_attributes": True}


# ─── Operator / Auth ─────────────────────────────────────────────────────────

class OperatorCreate(BaseModel):
    username: str
    email: str
    password: str
    role: OperatorRole = OperatorRole.SOC

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one numeric digit")
        return v


class OperatorOut(BaseModel):
    id: int
    username: str
    email: str
    role: OperatorRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    operator: OperatorOut


class TokenRefreshRequest(BaseModel):
    refresh_token: str



class LoginRequest(BaseModel):
    username: str
    password: str


# ─── Search ──────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    limit: int = 20

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()


class SearchResponse(BaseModel):
    query: str
    sql_filter: str
    results: list[IncidentOut]
    total: int


# ─── WebSocket Events ────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    event: str          # "incident_new" | "incident_updated" | "alert_sent" | "ping"
    data: dict[str, Any]
    timestamp: datetime


# ─── Pipeline ────────────────────────────────────────────────────────────────

class AnalyzeFrameRequest(BaseModel):
    camera_id: int
    image_b64: str      # base64-encoded JPEG/PNG

    @field_validator("image_b64")
    @classmethod
    def validate_image_b64(cls, v: str) -> str:
        # Limit image upload size to 10MB of base64 characters
        if len(v) > 10_000_000:
            raise ValueError("Base64 image data too large (max 10MB)")
        return v


class PipelineStatus(BaseModel):
    cameras_active: int
    incidents_today: int
    pending_review: int
    alerts_sent: int
    api_cost_today_usd: float
    demo_mode: bool
