"""
Raven AI CCTV — Qwen-Plus Integration
Generates bilingual incident reports (EN + Swahili) and semantic search filters.
"""
import json
import logging
import random
from datetime import datetime

from backend.config import get_settings
from backend.schemas import ThreatAnalysis

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Report Generation Prompt ────────────────────────────────────────────────

REPORT_PROMPT_TEMPLATE = """You are a certified security analyst and forensic report writer.

Generate a structured incident report in TWO languages: English and Swahili.

Incident Details:
- Camera: {camera_name} | Location: {camera_location}
- Timestamp: {timestamp}
- Threat Type: {threat_type}
- Severity: {severity} (Score: {severity_score}/10)
- Actors: {actors}
- Scene: {scene_description}
- AI Reasoning: {reasoning}

Return a JSON object with this EXACT structure:
{{
  "report_en": "Full English report (3-4 paragraphs: summary, observations, recommendations, legal notes)",
  "report_sw": "Ripoti kamili ya Kiswahili (aya 3-4: muhtasari, uchunguzi, mapendekezo, maelezo ya kisheria)"
}}

The report must include:
1. Executive Summary (what happened, when, where)
2. Detailed Observations (actors, behavior, anomalies)
3. Recommended Actions (immediate response, investigation steps)
4. Legal/Forensic Notes (chain of custody, evidence integrity)

Return ONLY the JSON object."""


SEARCH_PROMPT_TEMPLATE = """You are a database query assistant for a CCTV security system.

Convert the user's natural language query into SQL WHERE clause conditions for the incidents table.

Available columns:
- threat_type (text)
- severity (CRITICAL/HIGH/MEDIUM/LOW)
- timestamp (datetime)
- scene_description (text)
- camera_id (integer)
- status (PENDING/APPROVED/REJECTED/ESCALATED/PROCESSING)

User query: "{query}"

Return ONLY a JSON object:
{{"where_clause": "SQL WHERE clause conditions (without the WHERE keyword)", "explanation": "brief explanation"}}

Examples:
- "show me critical incidents from today" → {{"where_clause": "severity = 'CRITICAL' AND date(timestamp) = date('now')", "explanation": "Filter by CRITICAL severity and today's date"}}
- "all vehicle intrusions last week" → {{"where_clause": "threat_type LIKE '%Vehicle%' AND timestamp >= datetime('now', '-7 days')", "explanation": "Vehicle-related threats in last 7 days"}}
- "pending reviews" → {{"where_clause": "status = 'PENDING'", "explanation": "Incidents awaiting SOC review"}}"""


# ─── Mock Reports ────────────────────────────────────────────────────────────

MOCK_REPORTS = {
    "CRITICAL": {
        "report_en": """INCIDENT REPORT — Raven AI CCTV SECURITY SYSTEM
Classification: CRITICAL | Priority: IMMEDIATE RESPONSE REQUIRED

EXECUTIVE SUMMARY
A perimeter security breach was detected at 20:47 EAT by the Raven AI AI surveillance system. An unauthorized individual was identified crossing the northern perimeter fence at the compound's northwest access point. The Raven AI-VL AI engine assessed the threat at severity level 9.2/10 (CRITICAL) with 94% confidence.

DETAILED OBSERVATIONS
The subject — one adult male in dark clothing carrying an unidentified bag — entered the restricted zone via a deliberate breach of the perimeter fence. Motion analysis indicates purposeful movement toward the main building. The individual did not display any visible access credentials. Behavioral pattern analysis flagged the subject's posture and movement trajectory as consistent with unauthorized intrusion intent.

RECOMMENDED ACTIONS
1. IMMEDIATE: Dispatch security response team to northwest perimeter (Grid Ref: NW-07)
2. IMMEDIATE: Lock down main building access points B and C
3. SHORT-TERM: Pull CCTV footage from cameras CAM-02, CAM-05, and CAM-11 for corroborating evidence
4. Review access log for any tailgating or credential anomalies in the past 30 minutes

LEGAL AND FORENSIC NOTES
This incident has been automatically recorded with a SHA-256 signed evidence package. Chain of custody is preserved from initial detection through AI analysis. All video evidence is stored in encrypted format on Alibaba Cloud OSS. This report constitutes a formal incident record and may be submitted to law enforcement upon SOC operator approval. Evidence integrity: VERIFIED.""",
        "report_sw": """RIPOTI YA TUKIO — MFUMO WA USALAMA WA Raven AI CCTV
Uainishaji: MUHIMU | Kipaumbele: MWITIKIO WA HARAKA UNAHITAJIKA

MUHTASARI WA MKURUGENZI
Uvunjaji wa usalama wa mipaka uligunduliwa saa 20:47 EAT na mfumo wa ufuatiliaji wa AI wa Raven AI. Mtu asiye na ruhusa alitambuliwa akivuka uzio wa mipaka ya kaskazini kwenye hatua ya upatikanaji ya kaskazini magharibi ya kiwanja. Injini ya AI ya Raven AI-VL ilitathmini tishio kwa kiwango cha ukali wa 9.2/10 (MUHIMU) kwa uhakika wa asilimia 94.

UCHUNGUZI WA KINA
Mhusika — mtu mzima wa kiume katika mavazi ya giza akibeba mfuko usiojulikana — aliingia kwenye eneo lililozuiwa kwa njia ya kuvunja kwa makusudi uzio wa mipaka. Uchambuzi wa mwendo unaonyesha harakati za makusudi kuelekea jengo kuu. Mtu huyo hakuonyesha vitambulisho vyovyote vya upatikanaji. Uchambuzi wa mfano wa tabia uliashiria mkao na njia ya harakati ya mhusika kama inayoendana na nia ya kuingia bila ruhusa.

MAPENDEKEZO YA HATUA
1. HARAKA: Tuma timu ya mwitikio wa usalama kwenye mipaka ya kaskazini magharibi (Rejea ya Gridi: NW-07)
2. HARAKA: Funga hatua za upatikanaji wa jengo kuu B na C
3. MUDA MFUPI: Chapua tapes za CCTV kutoka kamera CAM-02, CAM-05, na CAM-11 kwa ushahidi wa ziada
4. Kagua kumbukumbu ya upatikanaji kwa utoroshaji wowote au upungufu wa vitambulisho katika dakika 30 zilizopita

MAELEZO YA KISHERIA NA UCHUNGUZI
Tukio hili limerekodiwa kiotomatiki na kifurushi cha ushahidi kilichosainiwa na SHA-256. Mlolongo wa uhifadhi umehifadhiwa kuanzia ugunduzi wa awali hadi uchambuzi wa AI. Ushahidi wote wa video umehifadhiwa katika umbizo lililofichwa kwenye Alibaba Cloud OSS. Ripoti hii inaunda rekodi rasmi ya tukio na inaweza kuwasilishwa kwa vyombo vya utekelezaji wa sheria baada ya idhini ya mwendeshaji wa SOC. Uadilifu wa ushahidi: IMETHIBITISHWA."""
    },
    "LOW": {
        "report_en": """INCIDENT REPORT — Raven AI CCTV SECURITY SYSTEM
Classification: LOW | Priority: LOGGED FOR RECORD

EXECUTIVE SUMMARY
Routine activity was detected and logged at 20:47 EAT. The Raven AI AI surveillance system identified two uniformed staff members conducting normal operations within an authorized zone. Threat assessment: 1.2/10 (LOW). No action required.

DETAILED OBSERVATIONS
Two individuals wearing company uniforms were observed moving through the designated staff corridor. Movement patterns are consistent with authorized shift activity. Both individuals were identified via uniform recognition as registered staff. No anomalies, restricted zone breaches, or behavioral irregularities were detected.

RECOMMENDED ACTIONS
1. No immediate action required
2. Log retained for 90-day audit compliance
3. This event contributes to baseline behavioral modeling for this zone and time period

LEGAL AND FORENSIC NOTES
Low-priority log entry. Evidence package generated for compliance purposes. Chain of custody intact. No escalation warranted.""",
        "report_sw": """RIPOTI YA TUKIO — MFUMO WA USALAMA WA Raven AI CCTV
Uainishaji: CHINI | Kipaumbele: ILIREKODIWA KWA KUMBUKUMBU

MUHTASARI
Shughuli ya kawaida iligunduliwa na kuorodheshwa saa 20:47 EAT. Hakuna hatua inayohitajika. Tathmini ya tishio: 1.2/10 (CHINI)."""
    }
}


# ─── Main functions ──────────────────────────────────────────────────────────

async def generate_incident_report(
    analysis: ThreatAnalysis,
    camera_name: str,
    camera_location: str,
    timestamp: datetime,
) -> tuple[str, str]:
    """
    Generate bilingual incident report (EN + Swahili).
    Returns (report_en, report_sw).
    """
    if not settings.is_qwen_configured:
        logger.info("DEMO_MODE: Returning mock incident report")
        key = analysis.severity.value if analysis.severity.value in MOCK_REPORTS else "LOW"
        report = MOCK_REPORTS[key]
        return report["report_en"], report["report_sw"]

    return await _call_qwen_plus_report(analysis, camera_name, camera_location, timestamp)


async def semantic_search(query: str) -> tuple[str, str]:
    """
    Convert NL query → SQL WHERE clause via Qwen-Plus.
    Returns (where_clause, explanation).
    """
    if not settings.is_qwen_configured:
        return _mock_search(query)

    return await _call_qwen_plus_search(query)


# ─── Live API calls ──────────────────────────────────────────────────────────

async def _call_qwen_plus_with_retry(payload: dict) -> dict:
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


async def _call_qwen_plus_report(
    analysis: ThreatAnalysis,
    camera_name: str,
    camera_location: str,
    timestamp: datetime,
) -> tuple[str, str]:
    prompt = REPORT_PROMPT_TEMPLATE.format(
        camera_name=camera_name,
        camera_location=camera_location,
        timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
        threat_type=analysis.threat_type,
        severity=analysis.severity.value,
        severity_score=analysis.severity_score,
        actors=", ".join(analysis.actors_detected),
        scene_description=analysis.scene_description,
        reasoning=analysis.qwen_reasoning,
    )

    payload = {
        "model": settings.qwen_plus_model,
        "messages": [{"role": "user", "content": prompt}]
    }

    res_json = await _call_qwen_plus_with_retry(payload)
    text = res_json["choices"][0]["message"]["content"]
    data = _parse_json(text)
    return data.get("report_en", "Report generation failed."), data.get("report_sw", "Uzalishaji wa ripoti umeshindwa.")


async def _call_qwen_plus_search(query: str) -> tuple[str, str]:
    prompt = SEARCH_PROMPT_TEMPLATE.format(query=query)

    payload = {
        "model": settings.qwen_plus_model,
        "messages": [{"role": "user", "content": prompt}]
    }

    res_json = await _call_qwen_plus_with_retry(payload)
    text = res_json["choices"][0]["message"]["content"]
    data = _parse_json(text)
    return data.get("where_clause", "1=1"), data.get("explanation", "")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse Qwen-Plus JSON: {text[:200]}")
        return {}


def _mock_search(query: str) -> tuple[str, str]:
    """Simple keyword-based mock search translation."""
    q = query.lower()
    if "critical" in q:
        return "severity = 'CRITICAL'", "Filter by CRITICAL severity"
    elif "high" in q:
        return "severity = 'HIGH'", "Filter by HIGH severity"
    elif "pending" in q or "review" in q:
        return "status = 'PENDING'", "Incidents awaiting SOC review"
    elif "today" in q:
        return "date(timestamp) = date('now')", "Today's incidents"
    elif "vehicle" in q or "car" in q:
        return "threat_type LIKE '%Vehicle%'", "Vehicle-related incidents"
    elif "intrusion" in q or "fence" in q:
        return "threat_type LIKE '%Intrusion%'", "Perimeter intrusion incidents"
    elif "approved" in q:
        return "status = 'APPROVED'", "Approved incidents"
    elif "escalated" in q:
        return "status = 'ESCALATED'", "Escalated incidents"
    else:
        return "1=1", f"Showing all incidents (no specific filter matched for: '{query}')"
