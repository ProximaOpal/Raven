"""
Raven AI CCTV — Evidence Router
GET /api/evidence/{incident_id}/download — PDF + archive download
GET /api/evidence/{incident_id}/audit — Full audit log for incident
"""
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AuditLog, Incident, Operator
from backend.schemas import AuditLogOut
from backend.auth import require_operator

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/{incident_id}/pdf")
async def download_pdf(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_operator),
):
    inc = await _get_incident(db, incident_id)
    if not inc.pdf_path or not Path(inc.pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not yet generated. Approve the incident first.")
    return FileResponse(
        inc.pdf_path,
        media_type="application/pdf",
        filename=f"raven_incident_{incident_id}_report.pdf",
    )


@router.get("/{incident_id}/archive")
async def download_archive(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_operator),
):
    inc = await _get_incident(db, incident_id)
    if not inc.archive_path or not Path(inc.archive_path).exists():
        raise HTTPException(status_code=404, detail="Evidence archive not yet generated.")
    return FileResponse(
        inc.archive_path,
        media_type="application/zip",
        filename=f"raven_incident_{incident_id}_evidence.zip",
    )


@router.get("/{incident_id}/audit", response_model=list[AuditLogOut])
async def get_audit_log(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_operator),
):
    await _get_incident(db, incident_id)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.incident_id == incident_id)
        .order_by(AuditLog.timestamp)
    )
    return result.scalars().all()


async def _get_incident(db: AsyncSession, incident_id: int) -> Incident:
    inc = await db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

