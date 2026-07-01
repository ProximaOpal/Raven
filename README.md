# Raven AI CCTV — Autonomous Security Operations

> **Qwen Cloud Global AI Hackathon 2026 · Track 4: Autopilot Agent**

End-to-end autonomous CCTV security operations. Camera alerts → Qwen-VL-Max analysis → incident report → multi-channel notification → HITL SOC approval → law enforcement evidence handoff.

![Raven AI CCTV Architecture](docs/architecture.png)

## 🚀 Quick Start (Demo Mode — No API Keys Required)

```bash
# 1. Clone & enter
git clone https://github.com/your-username/Raven
cd Raven

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env template (demo mode works without real keys)
cp .env.example .env

# 4. Seed demo data & start
python demo/mock_data.py
uvicorn backend.main:app --reload --port 8000

# 5. Open SOC Dashboard
open http://localhost:8000
```

## 🏗️ Architecture

```
📷 Camera RTSP  →  🎯 YOLOv8-nano  →  🤖 Qwen-VL-Max  →  📋 Qwen-Plus
     ↓                   ↓                    ↓                  ↓
  OpenCV             Pre-filter           Threat JSON        Incident Report
                    (85% cost cut)       + Scene NL          EN + Swahili
                                              ↓
                                    🔔 Alert Dispatch
                                    Twilio SMS + SendGrid
                                          ↓
                                    👤 HITL SOC Review
                                    Approve / Reject / Escalate
                                          ↓
                                    ⚖️ Evidence Package
                                    SHA-256 PDF Archive
```

## 🤖 AI Pipeline

| Stage | Model | Purpose |
|-------|-------|---------|
| Vision Analysis | `qwen-vl-max` | Threat classification, actor detection, scene description |
| Report Generation | `qwen-plus` | Bilingual incident report (EN + Swahili) |
| Semantic Search | `qwen-plus` | NL query → incident retrieval |
| Pre-filter | `YOLOv8-nano` | Person/vehicle detection to gate Qwen-VL calls |

## 📦 Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2.0
- **AI**: DashScope SDK (Qwen-VL-Max, Qwen-Plus), ultralytics (YOLOv8)
- **Async**: httpx.AsyncClient, Celery + Redis
- **Alerts**: Twilio SMS, SendGrid email
- **Evidence**: WeasyPrint PDF, SHA-256 signing
- **Frontend**: Vanilla HTML/CSS/JS, Chart.js, WebSocket
- **Cloud**: Alibaba Cloud ECS (Singapore), OSS, ApsaraDB RDS
- **Container**: Docker + docker-compose

## 🔑 Environment Variables

See [`.env.example`](.env.example) for all required variables.

## 🐋 Docker Deployment

```bash
docker-compose up -d
```

## ☁️ Alibaba Cloud ECS

See [`docs/setup.md`](docs/setup.md) for full ECS deployment guide.

## 📺 Demo Video

[▶ Watch 3-minute pipeline walkthrough](#) *(YouTube link — add before submission)*

## 🏆 Hackathon

- **Event**: Qwen Cloud Global AI Hackathon 2026
- **Track**: Track 4 — Autopilot Agent ($7,000 + $3,000 cloud credits)
- **Deadline**: July 9, 2026 @ 5:00 PM EDT

## 📄 License

MIT License — see [LICENSE](LICENSE)
