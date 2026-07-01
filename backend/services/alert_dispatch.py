"""
NEXUS CCTV — Multi-Channel Alert Dispatch
Sends CRITICAL/HIGH incident alerts via Twilio SMS, SendGrid email, and WebSocket.
Falls back to mock/log mode when credentials are not configured.
"""
import logging
from datetime import datetime, timezone

from backend.config import get_settings
from backend.models import AlertChannel, AlertStatus, SeverityLevel

logger = logging.getLogger(__name__)
settings = get_settings()

# Severity levels that trigger SMS + email alerts
ALERT_SEVERITY_THRESHOLD = {SeverityLevel.CRITICAL, SeverityLevel.HIGH}


# ─── SMS (Twilio) ─────────────────────────────────────────────────────────

async def send_sms_alert(incident_id: int, severity: str, threat_type: str, location: str) -> dict:
    """Send SMS alert via Twilio for CRITICAL/HIGH incidents."""
    message = (
        f"🚨 NEXUS ALERT [{severity}]\n"
        f"Incident #{incident_id}: {threat_type}\n"
        f"Location: {location}\n"
        f"Action required — SOC dashboard: http://your-ecs-ip:8000"
    )

    if not settings.is_twilio_configured:
        logger.info(f"MOCK SMS → {settings.alert_to_number}: {message}")
        return {
            "channel": AlertChannel.SMS,
            "recipient": settings.alert_to_number or "+254700000000",
            "status": AlertStatus.MOCK,
            "message_preview": message[:120],
            "error_detail": None,
        }

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            body=message,
            from_=settings.twilio_from_number,
            to=settings.alert_to_number,
        )
        logger.info(f"SMS sent: SID={msg.sid}")
        return {
            "channel": AlertChannel.SMS,
            "recipient": settings.alert_to_number,
            "status": AlertStatus.SENT,
            "message_preview": message[:120],
            "error_detail": None,
        }
    except Exception as e:
        logger.error(f"Twilio SMS error: {e}")
        return {
            "channel": AlertChannel.SMS,
            "recipient": settings.alert_to_number,
            "status": AlertStatus.FAILED,
            "message_preview": message[:120],
            "error_detail": str(e),
        }


# ─── Email (SendGrid) ────────────────────────────────────────────────────────

async def send_email_alert(
    incident_id: int,
    severity: str,
    threat_type: str,
    location: str,
    description: str,
    report_en: str | None = None,
) -> dict:
    """Send structured incident email via SendGrid."""
    subject = f"[NEXUS CCTV] {severity} Alert — {threat_type} @ {location}"
    body_html = _build_email_html(incident_id, severity, threat_type, location, description, report_en)
    body_text = f"NEXUS CCTV Alert\n\nIncident #{incident_id}\nSeverity: {severity}\nType: {threat_type}\nLocation: {location}\n\n{description}"

    if not settings.is_sendgrid_configured:
        logger.info(f"MOCK EMAIL → {settings.alert_to_email} | Subject: {subject}")
        return {
            "channel": AlertChannel.EMAIL,
            "recipient": settings.alert_to_email,
            "status": AlertStatus.MOCK,
            "message_preview": subject,
            "error_detail": None,
        }

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        mail = Mail(
            from_email=settings.alert_from_email,
            to_emails=settings.alert_to_email,
            subject=subject,
            html_content=body_html,
            plain_text_content=body_text,
        )
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(mail)
        logger.info(f"Email sent: status={response.status_code}")
        return {
            "channel": AlertChannel.EMAIL,
            "recipient": settings.alert_to_email,
            "status": AlertStatus.SENT,
            "message_preview": subject,
            "error_detail": None,
        }
    except Exception as e:
        logger.error(f"SendGrid email error: {e}")
        return {
            "channel": AlertChannel.EMAIL,
            "recipient": settings.alert_to_email,
            "status": AlertStatus.FAILED,
            "message_preview": subject,
            "error_detail": str(e),
        }


def _build_email_html(
    incident_id: int,
    severity: str,
    threat_type: str,
    location: str,
    description: str,
    report_en: str | None,
) -> str:
    severity_colors = {
        "CRITICAL": "#dc2626",
        "HIGH": "#ea580c",
        "MEDIUM": "#ca8a04",
        "LOW": "#16a34a",
    }
    color = severity_colors.get(severity, "#6b7280")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Courier New', monospace; background: #f1f5f9; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <div style="background: #0f172a; padding: 24px; text-align: center;">
      <h1 style="color: white; margin: 0; font-size: 20px; letter-spacing: 4px;">NEXUS CCTV</h1>
      <p style="color: #94a3b8; margin: 4px 0 0; font-size: 12px;">AUTONOMOUS SECURITY OPERATIONS</p>
    </div>
    <div style="padding: 24px;">
      <div style="background: {color}; color: white; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px;">
        <strong style="font-size: 18px;">⚠ {severity} ALERT — Incident #{incident_id}</strong>
      </div>
      <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 8px; color: #64748b; width: 120px;">Threat Type</td><td style="padding: 8px; font-weight: bold;">{threat_type}</td></tr>
        <tr style="background: #f8fafc;"><td style="padding: 8px; color: #64748b;">Location</td><td style="padding: 8px;">{location}</td></tr>
        <tr><td style="padding: 8px; color: #64748b;">Time</td><td style="padding: 8px;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
      </table>
      <div style="background: #f8fafc; border-left: 4px solid {color}; padding: 16px; margin: 20px 0; border-radius: 0 6px 6px 0;">
        <strong style="color: #0f172a;">AI Scene Analysis</strong>
        <p style="color: #475569; margin: 8px 0 0; font-size: 14px; line-height: 1.6;">{description}</p>
      </div>
      <div style="text-align: center; margin-top: 24px;">
        <a href="http://your-ecs-ip:8000" style="background: #0f172a; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; letter-spacing: 1px;">OPEN SOC DASHBOARD →</a>
      </div>
    </div>
    <div style="background: #f1f5f9; padding: 16px; text-align: center; font-size: 11px; color: #94a3b8;">
      NEXUS CCTV · Powered by Qwen-VL-Max · Alibaba Cloud ECS<br>
      This is an automated alert. SHA-256 signed evidence package available on dashboard.
    </div>
  </div>
</body>
</html>"""


# ─── Dispatch orchestrator ───────────────────────────────────────────────────

async def dispatch_alerts(
    incident_id: int,
    severity: SeverityLevel,
    threat_type: str,
    location: str,
    description: str,
    report_en: str | None = None,
) -> list[dict]:
    """
    Dispatch all configured alert channels for an incident.
    Returns list of alert records to persist.
    """
    results = []

    if severity in ALERT_SEVERITY_THRESHOLD:
        sms_result = await send_sms_alert(incident_id, severity.value, threat_type, location)
        results.append(sms_result)

        email_result = await send_email_alert(
            incident_id, severity.value, threat_type, location, description, report_en
        )
        results.append(email_result)
    else:
        logger.info(f"Incident #{incident_id}: severity {severity.value} below alert threshold — skipping SMS/email")

    return results
