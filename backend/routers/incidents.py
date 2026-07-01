"""
NEXUS CCTV — Incidents Router
GET /api/incidents, GET /api/incidents/{id}
POST /api/incidents/{id}/approve|reject|escalate
POST /api/incidents/analyze (manual frame submission)
"""
import base64
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth import get_current_operator
from backend.database import get_db
from backend.models import Alert, AlertChannel, Camera, Incident, IncidentStatus, Operator, SeverityLevel
from backend.schemas import AnalyzeFrameRequest, IncidentDecision, IncidentOut
from backend.services import alert_dispatch, evidence_package, qwen_plus, qwen_vl
from backend.services.hitl import HITLWorkflow
from backend.ws_manager import ws_manager

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
logger = logging.getLogger(__name__)


def _incident_to_dict(inc: Incident) -> dict:
    d = {
        "id": inc.id,
        "camera_id": inc.camera_id,
        "timestamp": inc.timestamp.isoformat() if inc.timestamp else None,
        "threat_type": inc.threat_type,
        "severity": inc.severity.value if inc.severity else None,
        "severity_score": inc.severity_score,
        "actors_detected": inc.actors_detected,
        "scene_description": inc.scene_description,
        "qwen_reasoning": inc.qwen_reasoning,
        "confidence": inc.confidence,
        "report_en": inc.report_en,
        "report_sw": inc.report_sw,
        "frame_path": inc.frame_path,
        "pdf_path": inc.pdf_path,
        "sha256_hash": inc.sha256_hash,
        "status": inc.status.value if inc.status else None,
        "reviewed_at": inc.reviewed_at.isoformat() if inc.reviewed_at else None,
        "tokens_used": inc.tokens_used,
        "api_cost_usd": inc.api_cost_usd,
    }
    if hasattr(inc, "camera") and inc.camera:
        d["camera"] = {"id": inc.camera.id, "name": inc.camera.name, "location": inc.camera.location}
    return d


@router.get("", response_model=list[IncidentOut])
async def list_incidents(
    status: str | None = None,
    severity: str | None = None,
    camera_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Incident).options(selectinload(Incident.camera)).order_by(desc(Incident.timestamp))
    if status:
        q = q.where(Incident.status == IncidentStatus(status.upper()))
    if severity:
        q = q.where(Incident.severity == SeverityLevel(severity.upper()))
    if camera_id:
        q = q.where(Incident.camera_id == camera_id)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    from datetime import date
    today = date.today()
    total = await db.scalar(select(func.count(Incident.id)))
    today_count = await db.scalar(
        select(func.count(Incident.id)).where(func.date(Incident.timestamp) == today)
    )
    pending = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status == IncidentStatus.PENDING)
    )
    cost = await db.scalar(
        select(func.sum(Incident.api_cost_usd)).where(func.date(Incident.timestamp) == today)
    )
    return {
        "total_incidents": total or 0,
        "incidents_today": today_count or 0,
        "pending_review": pending or 0,
        "api_cost_today_usd": round(float(cost or 0), 4),
    }


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Incident).options(selectinload(Incident.camera)).where(Incident.id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@router.get("/{incident_id}/frame")
async def get_incident_frame(incident_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not inc.frame_path or not os.path.exists(inc.frame_path):
        raise HTTPException(status_code=404, detail="Incident frame image not found")
    return FileResponse(inc.frame_path, media_type="image/jpeg")


@router.post("/{incident_id}/approve")
async def approve_incident(
    incident_id: int,
    body: IncidentDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: Operator | None = Depends(get_current_operator),
):
    inc = await _get_pending(db, incident_id)
    operator_id = operator.id if operator else 1  # default for demo
    inc = await HITLWorkflow.approve(db, inc, operator_id, body.notes, _get_ip(request))

    # Generate evidence package on approval
    camera = await db.get(Camera, inc.camera_id)
    cam_name = camera.name if camera else "Unknown"
    cam_loc = camera.location if camera else "Unknown"
    try:
        pkg = await evidence_package.generate_evidence_package(inc, cam_name, cam_loc)
        inc.pdf_path = pkg["pdf_path"]
        inc.archive_path = pkg["archive_path"]
        inc.sha256_hash = pkg["sha256_hash"]
        await db.commit()
        await db.refresh(inc)
    except Exception as e:
        logger.error(f"Evidence package error: {e}")

    await ws_manager.broadcast_incident_update(_incident_to_dict(inc))
    return {"status": "approved", "incident_id": inc.id, "sha256": inc.sha256_hash}


@router.post("/{incident_id}/reject")
async def reject_incident(
    incident_id: int,
    body: IncidentDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: Operator | None = Depends(get_current_operator),
):
    inc = await _get_pending(db, incident_id)
    operator_id = operator.id if operator else 1
    inc = await HITLWorkflow.reject(db, inc, operator_id, body.notes, _get_ip(request))
    await ws_manager.broadcast_incident_update(_incident_to_dict(inc))
    return {"status": "rejected", "incident_id": inc.id}


@router.post("/{incident_id}/escalate")
async def escalate_incident(
    incident_id: int,
    body: IncidentDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: Operator | None = Depends(get_current_operator),
):
    inc = await _get_pending(db, incident_id)
    operator_id = operator.id if operator else 1
    inc = await HITLWorkflow.escalate(db, inc, operator_id, body.notes, _get_ip(request))

    # Escalation also triggers evidence packaging
    camera = await db.get(Camera, inc.camera_id)
    cam_name = camera.name if camera else "Unknown"
    cam_loc = camera.location if camera else "Unknown"
    try:
        pkg = await evidence_package.generate_evidence_package(inc, cam_name, cam_loc)
        inc.pdf_path = pkg["pdf_path"]
        inc.archive_path = pkg["archive_path"]
        inc.sha256_hash = pkg["sha256_hash"]
        await db.commit()
    except Exception as e:
        logger.error(f"Evidence package error on escalate: {e}")

    await ws_manager.broadcast_incident_update(_incident_to_dict(inc))
    return {"status": "escalated", "incident_id": inc.id}


@router.post("/analyze")
async def analyze_frame(
    body: AnalyzeFrameRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually submit a base64 frame for full pipeline processing.
    Creates an Incident record and triggers Qwen-VL analysis.
    """
    camera = await db.get(Camera, body.camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    # Run Qwen-VL analysis
    analysis = await qwen_vl.analyze_frame(
        body.image_b64,
        camera.name,
        camera.location,
    )

    # Persist incident
    actors_json = json.dumps(analysis.actors_detected)
    inc = Incident(
        camera_id=camera.id,
        timestamp=datetime.now(timezone.utc),
        threat_type=analysis.threat_type,
        severity=analysis.severity,
        severity_score=analysis.severity_score,
        actors_detected=actors_json,
        scene_description=analysis.scene_description,
        qwen_reasoning=analysis.qwen_reasoning,
        confidence=analysis.confidence,
        status=IncidentStatus.PENDING,
        tokens_used=getattr(analysis, "tokens_used", None),
        api_cost_usd=getattr(analysis, "api_cost_usd", None),
    )
    db.add(inc)
    await db.flush()

    # Save frame image
    from backend.services.evidence_package import save_incident_frame
    frame_path = save_incident_frame(inc.id, body.image_b64)
    inc.frame_path = frame_path

    # Generate report
    try:
        rep_en, rep_sw = await qwen_plus.generate_incident_report(
            analysis, camera.name, camera.location, inc.timestamp
        )
        inc.report_en = rep_en
        inc.report_sw = rep_sw
    except Exception as e:
        logger.error(f"Report generation error: {e}")

    await db.commit()
    await db.refresh(inc)

    # Dispatch alerts
    try:
        alert_records = await alert_dispatch.dispatch_alerts(
            inc.id, inc.severity, inc.threat_type or "Unknown",
            camera.location, inc.scene_description or "", inc.report_en
        )
        for ar in alert_records:
            alert = Alert(incident_id=inc.id, **ar)
            db.add(alert)
        await db.commit()
    except Exception as e:
        logger.error(f"Alert dispatch error: {e}")

    # Broadcast to SOC dashboard
    await ws_manager.broadcast_incident(_incident_to_dict(inc))

    return _incident_to_dict(inc)


@router.get("/{incident_id}/trajectory")
async def get_incident_trajectory(incident_id: int, db: AsyncSession = Depends(get_db)):
    from backend.models import TrajectoryPoint
    result = await db.execute(
        select(TrajectoryPoint)
        .where(TrajectoryPoint.incident_id == incident_id)
        .order_by(TrajectoryPoint.timestamp.asc())
    )
    points = result.scalars().all()
    return [
        {
            "id": p.id,
            "camera_id": p.camera_id,
            "actor_id": p.actor_id,
            "world_x": p.world_x,
            "world_y": p.world_y,
            "timestamp": p.timestamp.isoformat() if p.timestamp else None
        }
        for p in points
    ]


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_pending(db: AsyncSession, incident_id: int) -> Incident:
    result = await db.execute(
        select(Incident).options(selectinload(Incident.camera)).where(Incident.id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if inc.status not in (IncidentStatus.PENDING, IncidentStatus.ESCALATED):
        raise HTTPException(
            status_code=400,
            detail=f"Incident is {inc.status.value} — only PENDING/ESCALATED can be actioned"
        )
    return inc


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
