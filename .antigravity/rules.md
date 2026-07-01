# NEXUS CCTV — Project Constitution

This document defines the core principles, operational constraints, and forensic integrity standards governing the NEXUS CCTV Autonomous System.

---

## 1. Forensic Integrity Standards

* **Immutability of State**: The system must enforce a linear, cryptographically-linked hash chain on all audit log records. No event or operator action can be altered or erased without breaking the chain.
* **Tamper Evidence**: Any audit log query must verify the chain from the genesis block to the latest entry before returning a "Secure" status. Any hash mismatch must trigger an immediate CRITICAL alert.
* **Evidence Preservation**: Incident frames and generated PDF reports must be cryptographically hashed using SHA-256 immediately upon generation, and locked in the local or cloud database.

---

## 2. Zero-Trust Access & Telemetry

* **Token Families & Rotation**: Every user session must employ JWT access token expiration and strict refresh token rotation with immediate family revocation on replay detection.
* **Input Sanitization**: All incoming camera frames, biometrics uploads, and search queries must be sanitized and validated using Pydantic schemas before parsing.
* **Network Isolations**: External API configurations (Twilio, SendGrid, Alibaba Cloud OSS) must be read from environment variables and must never be committed to source control.

---

## 3. Operational Priorities

1. **Life Safety**: Prioritize detection of violent threats, perimeter intrusion, and emergency incidents.
2. **Data Privacy**: Biometric details and facial recognition databases must be kept local and comply with strict access controls. No face embeddings should be transmitted outside the authorized network.
3. **Auditability**: Every decision (Approved, Rejected, Escalated) made by the autonomous agent or a human operator must register a corresponding block in the immutable ledger.
