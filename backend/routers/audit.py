"""
NEXUS CCTV — Cryptographic Audit Log Verification Router
GET /api/audit/verify
"""
import hashlib
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AuditLog
from backend.auth import require_operator

router = APIRouter(prefix="/api/audit", tags=["audit"])
logger = logging.getLogger(__name__)


@router.get("/verify")
async def verify_audit_trail(
    db: AsyncSession = Depends(get_db),
    operator = Depends(require_operator),
):
    """
    Scans the audit log database table, recalculates the SHA-256 hash chain,
    and returns whether the log remains untampered.
    """
    result = await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))
    logs = result.scalars().all()

    if not logs:
        return {"status": "secure", "total_records": 0, "message": "No audit records found"}

    expected_prev = "0" * 64

    for i, log in enumerate(logs):
        # 1. Verify prev_hash link
        if log.prev_hash != expected_prev:
            logger.warning(
                f"Audit validation failed at record ID {log.id}: "
                f"Expected prev_hash {expected_prev}, got {log.prev_hash}"
            )
            return {
                "status": "tampered",
                "record_id": log.id,
                "reason": "Prev hash link broken",
                "details": f"Expected {expected_prev[:12]}..., got {log.prev_hash[:12]}..."
            }

        # 2. Recalculate entry_hash
        payload = {
            "prev_hash": log.prev_hash,
            "incident_id": log.incident_id,
            "operator_id": log.operator_id,
            "action": log.action,
            "notes": log.notes,
            "timestamp": log.timestamp.isoformat(),
            "ip_address": log.ip_address
        }
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        computed_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        if computed_hash != log.entry_hash:
            logger.warning(
                f"Audit validation failed at record ID {log.id}: "
                f"Computed hash {computed_hash}, stored hash {log.entry_hash}"
            )
            return {
                "status": "tampered",
                "record_id": log.id,
                "reason": "Entry hash mismatch",
                "details": f"Computed {computed_hash[:12]}..., stored {log.entry_hash[:12]}..."
            }

        # Set up for next record
        expected_prev = log.entry_hash

    return {
        "status": "secure",
        "total_records": len(logs),
        "last_hash": expected_prev,
        "message": "Cryptographic audit trail is verified and intact"
    }
