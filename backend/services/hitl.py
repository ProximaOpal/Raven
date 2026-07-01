"""
Raven AI CCTV — HITL (Human-in-the-Loop) Workflow
State machine: PENDING → APPROVED / REJECTED / ESCALATED
Writes full audit trail on every SOC decision.
"""
import logging
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditLog, Incident, IncidentStatus, SeverityLevel

logger = logging.getLogger(__name__)


class HITLWorkflow:
    """Manages the HITL approval state machine for security incidents."""

    VALID_TRANSITIONS = {
        IncidentStatus.PENDING: {
            IncidentStatus.APPROVED,
            IncidentStatus.REJECTED,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.ESCALATED: {
            IncidentStatus.APPROVED,
            IncidentStatus.REJECTED,
        },
    }

    @staticmethod
    async def approve(
        db: AsyncSession,
        incident: Incident,
        operator_id: int,
        notes: str | None,
        ip_address: str | None,
    ) -> Incident:
        """SOC operator approves incident — triggers evidence packaging."""
        return await HITLWorkflow._transition(
            db, incident, IncidentStatus.APPROVED, operator_id, "APPROVED", notes, ip_address
        )

    @staticmethod
    async def reject(
        db: AsyncSession,
        incident: Incident,
        operator_id: int,
        notes: str | None,
        ip_address: str | None,
    ) -> Incident:
        """SOC operator rejects incident as false positive."""
        return await HITLWorkflow._transition(
            db, incident, IncidentStatus.REJECTED, operator_id, "REJECTED", notes, ip_address
        )

    @staticmethod
    async def escalate(
        db: AsyncSession,
        incident: Incident,
        operator_id: int,
        notes: str | None,
        ip_address: str | None,
    ) -> Incident:
        """SOC operator escalates to law enforcement."""
        return await HITLWorkflow._transition(
            db, incident, IncidentStatus.ESCALATED, operator_id, "ESCALATED", notes, ip_address
        )

    @staticmethod
    async def _transition(
        db: AsyncSession,
        incident: Incident,
        new_status: IncidentStatus,
        operator_id: int,
        action: str,
        notes: str | None,
        ip_address: str | None,
    ) -> Incident:
        valid = HITLWorkflow.VALID_TRANSITIONS.get(incident.status, set())
        if new_status not in valid:
            raise ValueError(
                f"Invalid transition: {incident.status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in valid]}"
            )

        now = datetime.now(timezone.utc)
        incident.status = new_status
        incident.reviewed_at = now
        incident.reviewed_by = operator_id

        # Forensics: Hash-chaining
        last_audit_result = await db.execute(
            select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
        )
        last_audit = last_audit_result.scalar_one_or_none()
        prev_hash = last_audit.entry_hash if last_audit else "0" * 64

        timestamp_str = now.isoformat()
        payload = {
            "prev_hash": prev_hash,
            "incident_id": incident.id,
            "operator_id": operator_id,
            "action": action,
            "notes": notes,
            "timestamp": timestamp_str,
            "ip_address": ip_address
        }
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        entry_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        audit = AuditLog(
            incident_id=incident.id,
            operator_id=operator_id,
            action=action,
            notes=notes,
            timestamp=now,
            ip_address=ip_address,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        db.add(audit)
        await db.commit()
        await db.refresh(incident)

        logger.info(
            f"Incident #{incident.id}: {action} by operator #{operator_id} | "
            f"Notes: {notes or 'none'} | IP: {ip_address}"
        )
        return incident

    @staticmethod
    async def get_pending_count(db: AsyncSession) -> int:
        result = await db.execute(
            select(Incident).where(Incident.status == IncidentStatus.PENDING)
        )
        return len(result.scalars().all())

    @staticmethod
    def requires_immediate_response(incident: Incident) -> bool:
        """CRITICAL incidents require a response within 15 minutes."""
        return incident.severity == SeverityLevel.CRITICAL
