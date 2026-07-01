"""
Raven AI CCTV — Demo Data Seeder
Populates the database with 4 cameras and 10 realistic incidents.
Run: python demo/mock_data.py
"""
import asyncio
import json
import random
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.auth import hash_password
from backend.config import get_settings
from backend.database import AsyncSessionLocal, init_db
from backend.models import (
    Alert, AlertChannel, AlertStatus, AuditLog, Camera, CameraStatus,
    Incident, IncidentStatus, Operator, OperatorRole, SeverityLevel,
    BiometricProfile, TrajectoryPoint
)

settings = get_settings()

CAMERAS = [
    {"name": "CAM-01 · Main Gate",      "location": "North Perimeter Gate",  "is_mock": True},
    {"name": "CAM-02 · Parking Zone A", "location": "East Parking Area",     "is_mock": True},
    {"name": "CAM-03 · Lobby CCTV",     "location": "Main Building Lobby",   "is_mock": True},
    {"name": "CAM-04 · Server Room",     "location": "B2 Data Center",        "is_mock": True},
]

MOCK_INCIDENTS = [
    {
        "threat_type": "Perimeter Intrusion",
        "severity": SeverityLevel.CRITICAL,
        "severity_score": 9.2,
        "actors_detected": json.dumps(["1 adult male", "dark clothing", "carrying bag"]),
        "scene_description": "An individual in dark clothing has crossed the perimeter fence at the northwest corner. Movement is deliberate and directed toward the main building.",
        "qwen_reasoning": "Fence line breach detected. Subject trajectory projects toward high-value asset area. Motion anomaly score: 0.94. Recommend immediate SOC review.",
        "confidence": 0.94,
        "status": IncidentStatus.PENDING,
        "tokens_used": 1420, "api_cost_usd": 0.00426,
    },
    {
        "threat_type": "Unauthorized Vehicle Access",
        "severity": SeverityLevel.HIGH,
        "severity_score": 7.5,
        "actors_detected": json.dumps(["1 vehicle (dark sedan)", "obscured plates"]),
        "scene_description": "A dark sedan has entered the restricted parking zone without a valid access pass. Stationary for 4+ minutes near the loading dock. Plate obscured.",
        "qwen_reasoning": "Vehicle in restricted zone. Plate obscured — high-risk indicator. Duration exceeds casual drop-off. Recommend physical inspection.",
        "confidence": 0.87,
        "status": IncidentStatus.APPROVED,
        "tokens_used": 980, "api_cost_usd": 0.00294,
    },
    {
        "threat_type": "Crowd Gathering",
        "severity": SeverityLevel.MEDIUM,
        "severity_score": 5.1,
        "actors_detected": json.dumps(["8-12 individuals", "mixed ages", "animated gestures"]),
        "scene_description": "A group of 8-12 people gathered near the main entrance, partially blocking ingress. Body language is animated.",
        "qwen_reasoning": "Group density above threshold. Gesture analysis suggests agitation. Monitor and consider de-escalation.",
        "confidence": 0.73,
        "status": IncidentStatus.PENDING,
        "tokens_used": 760, "api_cost_usd": 0.00228,
    },
    {
        "threat_type": "Loitering — Suspicious Behavior",
        "severity": SeverityLevel.HIGH,
        "severity_score": 6.8,
        "actors_detected": json.dumps(["1 individual", "hooded jacket", "repeated passes"]),
        "scene_description": "Individual has made 3 passes of the server room corridor in 12 minutes without accessing any office. Behavior is inconsistent with staff patterns.",
        "qwen_reasoning": "Repeated passes without destination. Dwell time in corridor: 12 min. Pattern resembles reconnaissance behavior. Recommend ID check.",
        "confidence": 0.81,
        "status": IncidentStatus.ESCALATED,
        "tokens_used": 1100, "api_cost_usd": 0.0033,
    },
    {
        "threat_type": "Tailgating — Unauthorized Entry",
        "severity": SeverityLevel.CRITICAL,
        "severity_score": 8.7,
        "actors_detected": json.dumps(["2 individuals", "1 badged employee", "1 unauthorized follower"]),
        "scene_description": "An unauthorized individual followed a badged employee through a controlled access door without scanning their own credential. Clear tailgating event.",
        "qwen_reasoning": "Tailgating detected. Two individuals entered through single badge scan. Access control bypass — high confidence (0.91). Immediate review required.",
        "confidence": 0.91,
        "status": IncidentStatus.APPROVED,
        "tokens_used": 1350, "api_cost_usd": 0.00405,
    },
    {
        "threat_type": "Abandoned Object",
        "severity": SeverityLevel.HIGH,
        "severity_score": 7.1,
        "actors_detected": json.dumps(["unattended backpack", "no owner visible"]),
        "scene_description": "An unattended backpack has been left in the main lobby for over 8 minutes. The individual who placed it is not visible in the frame.",
        "qwen_reasoning": "Unattended item — duration: 8+ min. Owner not present. Potential security risk per protocol. Recommend physical inspection and evacuation consideration.",
        "confidence": 0.85,
        "status": IncidentStatus.PENDING,
        "tokens_used": 890, "api_cost_usd": 0.00267,
    },
    {
        "threat_type": "Normal Activity",
        "severity": SeverityLevel.LOW,
        "severity_score": 1.2,
        "actors_detected": json.dumps(["2 uniformed staff", "routine movement"]),
        "scene_description": "Two uniformed staff members moving through the lobby. Movement patterns consistent with authorized shift activity.",
        "qwen_reasoning": "Uniform recognition positive. Motion trajectory nominal. No threat indicators.",
        "confidence": 0.98,
        "status": IncidentStatus.REJECTED,
        "tokens_used": 540, "api_cost_usd": 0.00162,
    },
    {
        "threat_type": "Perimeter Fence Damage",
        "severity": SeverityLevel.MEDIUM,
        "severity_score": 4.8,
        "actors_detected": json.dumps(["structural damage", "no persons present"]),
        "scene_description": "Section of perimeter fence appears bent/damaged near camera FOV. No persons currently present but breach point is accessible.",
        "qwen_reasoning": "Physical security compromise. No active threat but vulnerability exists. Recommend maintenance dispatch and increased monitoring of this sector.",
        "confidence": 0.79,
        "status": IncidentStatus.APPROVED,
        "tokens_used": 670, "api_cost_usd": 0.00201,
    },
    {
        "threat_type": "After-Hours Access Attempt",
        "severity": SeverityLevel.HIGH,
        "severity_score": 7.9,
        "actors_detected": json.dumps(["1 individual", "business attire", "22:47 local time"]),
        "scene_description": "Individual attempting to access the server room at 22:47 — outside authorized working hours for this zone. Badge scan failed twice.",
        "qwen_reasoning": "After-hours access attempt. Two failed badge scans. Business attire inconsistent with maintenance crew. Suspicious. Cross-check employee records.",
        "confidence": 0.88,
        "status": IncidentStatus.PENDING,
        "tokens_used": 1040, "api_cost_usd": 0.00312,
    },
    {
        "threat_type": "Vehicle Speeding — Internal Road",
        "severity": SeverityLevel.MEDIUM,
        "severity_score": 4.3,
        "actors_detected": json.dumps(["1 pickup truck", "estimated speed: 45 km/h"]),
        "scene_description": "A pickup truck was estimated traveling at approximately 45 km/h on the internal access road (speed limit: 15 km/h). No collision occurred.",
        "qwen_reasoning": "Speed violation. Optical flow analysis: ~45 km/h vs 15 km/h limit. Log for record. No immediate threat but safety risk present.",
        "confidence": 0.71,
        "status": IncidentStatus.REJECTED,
        "tokens_used": 720, "api_cost_usd": 0.00216,
    },
]

REPORTS_EN = {
    SeverityLevel.CRITICAL: "EXECUTIVE SUMMARY\nA critical security event was detected and automatically recorded by the Raven AI AI surveillance system. Immediate SOC review and physical response are warranted.\n\nDETAILED OBSERVATIONS\nThe AI analysis identified the described threat with high confidence. All relevant scene context has been captured and logged.\n\nRECOMMENDED ACTIONS\n1. Dispatch security personnel immediately\n2. Secure the affected zone\n3. Preserve CCTV footage for forensic review\n\nLEGAL NOTES\nSHA-256 signed evidence package generated. Chain of custody intact.",
    SeverityLevel.HIGH: "EXECUTIVE SUMMARY\nA high-priority security incident has been detected. Prompt SOC review is required.\n\nDETAILED OBSERVATIONS\nThe scene analysis flagged anomalous behavior consistent with a potential security breach or policy violation.\n\nRECOMMENDED ACTIONS\n1. Verify incident via physical patrol\n2. Check access logs for anomalies\n3. Update incident status after verification\n\nLEGAL NOTES\nEvidence logged and secured.",
    SeverityLevel.MEDIUM: "EXECUTIVE SUMMARY\nA medium-priority incident has been logged for SOC review.\n\nDETAILED OBSERVATIONS\nAnomalous activity detected that may warrant further investigation.\n\nRECOMMENDED ACTIONS\n1. Monitor the affected zone\n2. Review over the next 30 minutes\n\nLEGAL NOTES\nLog entry created.",
    SeverityLevel.LOW: "EXECUTIVE SUMMARY\nRoutine activity logged for compliance purposes. No action required.\n\nDETAILED OBSERVATIONS\nNormal operations detected within expected parameters.\n\nRECOMMENDED ACTIONS\nNo action required.\n\nLEGAL NOTES\nCompliance log entry.",
}


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:

        # 1. Create default operator
        from sqlalchemy import select
        existing_op = await db.execute(select(Operator).where(Operator.username == "admin"))
        if not existing_op.scalar_one_or_none():
            op = Operator(
                username="admin",
                email="admin@raven.local",
                hashed_password=hash_password("raven2026"),
                role=OperatorRole.ADMIN,
            )
            db.add(op)
            await db.flush()
            op_id = op.id
            print("[OK] Created operator: admin / raven2026")
        else:
            op_result = await db.execute(select(Operator).where(Operator.username == "admin"))
            op_id = op_result.scalar_one().id
            print("[OK] Operator already exists: admin")

        # 2. Create cameras
        cam_ids = []
        for cam_data in CAMERAS:
            existing = await db.execute(select(Camera).where(Camera.name == cam_data["name"]))
            existing_cam = existing.scalar_one_or_none()
            if existing_cam:
                cam_ids.append(existing_cam.id)
                continue
            cam = Camera(**cam_data, status=CameraStatus.ONLINE)
            db.add(cam)
            await db.flush()
            cam_ids.append(cam.id)
        await db.commit()
        print(f"[OK] {len(cam_ids)} cameras ready")

        # 2.5 Create biometric profiles
        existing_bio = await db.execute(select(BiometricProfile))
        if not existing_bio.scalars().all():
            bio_profiles = [
                BiometricProfile(
                    name="Operator John Doe",
                    role="Operator",
                    face_encoding=json.dumps([0.1 * i for i in range(128)]),
                    image_path=None
                ),
                BiometricProfile(
                    name="Jane Smith (Security)",
                    role="Staff",
                    face_encoding=json.dumps([0.15 * i for i in range(128)]),
                    image_path=None
                ),
                BiometricProfile(
                    name="Mark Vance (Expelled)",
                    role="Blacklisted",
                    face_encoding=json.dumps([0.05 * i for i in range(128)]),
                    image_path=None
                )
            ]
            for bp in bio_profiles:
                db.add(bp)
            await db.flush()
            print("[OK] Seeded biometric profiles")

        # 3. Create incidents spread over last 7 days
        now = datetime.now(timezone.utc)
        inc_ids = []
        existing_count_res = await db.execute(select(Incident))
        existing_count = len(existing_count_res.scalars().all())
        if existing_count >= len(MOCK_INCIDENTS):
            print(f"[OK] {existing_count} incidents already exist -- skipping")
        else:
            for i, inc_data in enumerate(MOCK_INCIDENTS):
                cam_id = cam_ids[i % len(cam_ids)]
                ts = now - timedelta(hours=random.randint(1, 168))

                report_en = REPORTS_EN.get(inc_data["severity"], REPORTS_EN[SeverityLevel.LOW])
                report_sw = "Ripoti imetafsiriwa kwa Kiswahili. Tukio hili limeandikwa kwa usalama wa kumbukumbu."

                # Biometrics matching mock
                biometrics_matched = None
                if i % 3 == 0:
                    biometrics_matched = json.dumps([{
                        "name": "Operator John Doe",
                        "role": "Operator",
                        "confidence": 0.92,
                        "bbox": {"x": 100, "y": 120, "w": 80, "h": 80}
                    }])
                elif i % 3 == 1:
                    biometrics_matched = json.dumps([{
                        "name": "Mark Vance (Expelled)",
                        "role": "Blacklisted",
                        "confidence": 0.89,
                        "bbox": {"x": 220, "y": 140, "w": 90, "h": 90}
                    }])

                inc = Incident(
                    camera_id=cam_id,
                    timestamp=ts,
                    report_en=report_en,
                    report_sw=report_sw,
                    biometrics_matched=biometrics_matched,
                    **{k: v for k, v in inc_data.items() if k != "status"},
                    status=inc_data["status"],
                )
                # Add sha256 for approved/escalated
                if inc_data["status"] in (IncidentStatus.APPROVED, IncidentStatus.ESCALATED):
                    inc.sha256_hash = f"a{'b' * 63}"[:64]  # placeholder
                    inc.reviewed_at = ts + timedelta(minutes=random.randint(5, 30))
                    inc.reviewed_by = op_id

                db.add(inc)
                await db.flush()
                inc_ids.append(inc.id)

                # Add mock trajectories
                num_points = random.randint(5, 12)
                start_x = random.randint(100, 400) if cam_id in (1, 4) else random.randint(400, 700)
                start_y = random.randint(100, 400) if cam_id in (1, 3) else random.randint(400, 700)
                actor_id = f"actor_{i + 1}"
                for pt_idx in range(num_points):
                    db.add(TrajectoryPoint(
                        incident_id=inc.id,
                        camera_id=cam_id,
                        actor_id=actor_id,
                        world_x=float(start_x + pt_idx * random.randint(-15, 15)),
                        world_y=float(start_y + pt_idx * random.randint(-15, 15)),
                        timestamp=ts + timedelta(seconds=pt_idx * 5)
                    ))

                # Add alerts for HIGH/CRITICAL
                if inc_data["severity"] in (SeverityLevel.CRITICAL, SeverityLevel.HIGH):
                    db.add(Alert(
                        incident_id=inc.id, channel=AlertChannel.SMS,
                        recipient="+254700000000", status=AlertStatus.MOCK,
                        sent_at=ts + timedelta(seconds=15),
                        message_preview=f"🚨 Raven AI ALERT [{inc_data['severity'].value}] — {inc_data['threat_type']}",
                    ))
                    db.add(Alert(
                        incident_id=inc.id, channel=AlertChannel.EMAIL,
                        recipient="soc@raven.local", status=AlertStatus.MOCK,
                        sent_at=ts + timedelta(seconds=20),
                        message_preview=f"[Raven AI CCTV] {inc_data['severity'].value} Alert — {inc_data['threat_type']}",
                    ))

            await db.commit()
            print(f"[OK] {len(inc_ids)} incidents seeded")

        # 4. Create cryptographically chained audit logs for actioned incidents
        non_pending = await db.execute(
            select(Incident)
            .where(Incident.status != IncidentStatus.PENDING)
            .order_by(Incident.reviewed_at.asc())
        )
        logged_incidents = non_pending.scalars().all()
        
        prev_hash = "0" * 64
        import hashlib
        
        for inc in logged_incidents:
            # Check if audit already exists
            existing_audit = await db.execute(
                select(AuditLog).where(AuditLog.incident_id == inc.id)
            )
            if existing_audit.scalar_one_or_none():
                continue
                
            ts_log = inc.reviewed_at or (inc.timestamp + timedelta(minutes=10))
            action = inc.status.value
            notes = "Reviewed during demo seed"
            ip = "127.0.0.1"
            
            payload = {
                "prev_hash": prev_hash,
                "incident_id": inc.id,
                "operator_id": op_id,
                "action": action,
                "notes": notes,
                "timestamp": ts_log.isoformat(),
                "ip_address": ip
            }
            payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            entry_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            
            db.add(AuditLog(
                incident_id=inc.id,
                operator_id=op_id,
                action=action,
                notes=notes,
                timestamp=ts_log,
                ip_address=ip,
                prev_hash=prev_hash,
                entry_hash=entry_hash
            ))
            await db.flush()
            prev_hash = entry_hash
            
        await db.commit()
        print("[OK] Cryptographic audit log seeded")

    print("\n>> Raven AI CCTV demo data ready!")
    print("   Login: admin / raven2026")
    print("   Start: uvicorn backend.main:app --reload --port 8000")
    print("   Open:  http://localhost:8000\n")


if __name__ == "__main__":
    asyncio.run(seed())
