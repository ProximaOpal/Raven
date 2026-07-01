"""
NEXUS CCTV — SQLAlchemy ORM Models
Tables: cameras, incidents, alerts, audit_log, operators
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ──────────────────────────────────────────────────────────────────

class SeverityLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(str, enum.Enum):
    PENDING = "PENDING"          # Awaiting HITL review
    APPROVED = "APPROVED"        # SOC approved — evidence packaged
    REJECTED = "REJECTED"        # SOC rejected — false positive
    ESCALATED = "ESCALATED"      # Escalated to law enforcement
    PROCESSING = "PROCESSING"    # Qwen-VL analysis in progress


class AlertChannel(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"
    WEBSOCKET = "WEBSOCKET"


class AlertStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"
    MOCK = "MOCK"


class CameraStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class OperatorRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SOC = "SOC"
    VIEWER = "VIEWER"


# ─── Models ─────────────────────────────────────────────────────────────────

class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    rtsp_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[CameraStatus] = mapped_column(
        SAEnum(CameraStatus), default=CameraStatus.ONLINE
    )
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incidents: Mapped[list["Incident"]] = relationship("Incident", back_populates="camera")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # AI Analysis
    threat_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[SeverityLevel | None] = mapped_column(SAEnum(SeverityLevel), nullable=True)
    severity_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1.0–10.0
    actors_detected: Mapped[str | None] = mapped_column(Text, nullable=True)    # JSON string
    biometrics_matched: Mapped[str | None] = mapped_column(Text, nullable=True) # JSON string
    scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    qwen_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Report
    report_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_sw: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Evidence
    frame_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    archive_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # HITL
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(IncidentStatus), default=IncidentStatus.PROCESSING
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)

    # Cost tracking
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    camera: Mapped["Camera"] = relationship("Camera", back_populates="incidents")
    alerts: Mapped[list["Alert"]] = relationship("Alert", back_populates="incident")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="incident")
    reviewer: Mapped["Operator | None"] = relationship("Operator", foreign_keys=[reviewed_by])
    trajectories: Mapped[list["TrajectoryPoint"]] = relationship("TrajectoryPoint", back_populates="incident")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    channel: Mapped[AlertChannel] = mapped_column(SAEnum(AlertChannel), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.MOCK)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    message_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("operators.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. APPROVED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="0" * 64)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="0" * 64)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="audit_logs")
    operator: Mapped["Operator | None"] = relationship("Operator")


class Operator(Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[OperatorRole] = mapped_column(SAEnum(OperatorRole), default=OperatorRole.SOC)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BiometricProfile(Base):
    __tablename__ = "biometric_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)  # Operator, Intruder, VIP, Staff
    face_encoding: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized float list (128-dim)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrajectoryPoint(Base):
    __tablename__ = "trajectory_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., person_0, vehicle_1
    world_x: Mapped[float] = mapped_column(Float, nullable=False)  # BEV X
    world_y: Mapped[float] = mapped_column(Float, nullable=False)  # BEV Y
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped["Incident | None"] = relationship("Incident", back_populates="trajectories")
