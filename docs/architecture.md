# NEXUS CCTV — Architecture & Data Flow

This document details the system design, hardware/software stack, and pipeline workflow of NEXUS CCTV.

## System Architecture Diagram

```mermaid
graph TD
    classDef hardware fill:#f1f5f9,stroke:#334155,stroke-width:2px;
    classDef software fill:#eff6ff,stroke:#2563eb,stroke-width:2px;
    classDef database fill:#f0fdf4,stroke:#16a34a,stroke-width:2px;
    classDef qwen fill:#faf5ff,stroke:#7c3aed,stroke-width:2px;
    classDef actor fill:#fff7ed,stroke:#ea580c,stroke-width:2px;

    %% Source Ingestion
    subgraph Ingestion["Tactical Feed Ingestion"]
        Camera["RTSP Camera Streams"]
        MockCamera["Mock Feed Simulator"]
    end
    class Camera,MockCamera hardware;

    %% Processing Pipeline
    subgraph Pipeline["Autopilot Processing Pipeline"]
        YOLO["YOLOv8 Pre-Filter (Target Ingress)"]
        Celery["Celery Task Pipeline"]
        Redis["Redis (Task Queue & Broker)"]
    end
    class YOLO,Celery software;
    class Redis database;

    %% Qwen AI Layer
    subgraph AIEngine["Alibaba Cloud & DashScope API"]
        QwenVL["Qwen-VL-Max (Multimodal Scene Reasoning)"]
        QwenPlus["Qwen-Plus (Bilingual Reporting & Search NLP)"]
    end
    class QwenVL,QwenPlus qwen;

    %% Central Backend
    subgraph BackendApp["Central Backend Service"]
        FastAPI["FastAPI App Server"]
        SQLite["SQL Database (SQLite / Postgres)"]
    end
    class FastAPI software;
    class SQLite database;

    %% Operations Console
    subgraph SOC["SOC Operations Console"]
        UI["SOC Operator Web UI"]
        WS["WebSocket (Real-Time Push)"]
    end
    class UI software;
    class WS software;

    %% Actions
    subgraph Dispatch["Incident Dispatch Services"]
        Twilio["Twilio (SMS Alerts)"]
        SendGrid["SendGrid (Email Reports)"]
        Evidence["PDF & ZIP Generator (Forensic Export)"]
    end
    class Twilio,SendGrid,Evidence software;

    %% Flow Paths
    Camera -->|Frame Capture| YOLO
    MockCamera -->|Inject Frame| YOLO
    
    YOLO -->|Empty Frame| Drop["Drop Frame (API Cost Saved 85%)"]
    YOLO -->|Target Detected| Redis
    
    Redis --> Celery
    
    Celery -->|Post Image B64| QwenVL
    QwenVL -->|Threat Metadata| Celery
    
    Celery -->|Format Report Query| QwenPlus
    QwenPlus -->|English + Swahili Reports| Celery
    
    Celery -->|Persist Incident| SQLite
    Celery -->|Broadast Telemetry| WS
    
    WS -->|Live Telemetry Push| UI
    FastAPI -->|REST API Requests| UI
    
    %% HITL Flow
    UI -->|Decision: Approve / Escalate| FastAPI
    FastAPI -->|Generate Evidence Package| Evidence
    FastAPI -->|Trigger Alert Dispatch| Twilio
    FastAPI -->|Trigger Alert Dispatch| SendGrid
```

## Detailed Data Flow Breakdown

1. **tactical Ingestion**: RTSP camera streams or simulation feeds submit frames at a configurable interval (default: 10s per camera) to the system.
2. **YOLOv8 Pre-Filter**: To avoid wasting API costs, a local CPU-bound YOLOv8-nano model screens frames for target activity (people/vehicles). If none are found, the frame is immediately dropped, yielding a cost reduction of up to 85%.
3. **Task Queueing**: If people or vehicles are present, the frame is encoded in base64 and pushed to Redis. A Celery task queue processes the frame asynchronously.
4. **Qwen-VL-Max Analysis**: Celery runs the multimodal analysis by sending the image frame to the DashScope API. The model returns a structured JSON containing threat classification, threat severity (CRITICAL, HIGH, MEDIUM, LOW), actors detected, and scene reasoning.
5. **Qwen-Plus Report & Translation**: The system formats the threat metadata and sends a text prompt to Qwen-Plus to generate official reports in both English and Kiswahili (bilingual output requirement).
6. **Telemetry Update**: The backend stores the incident details in the database and broadcasts the event payload via WebSocket to all connected SOC operators.
7. **Human-in-the-Loop Validation**: The incident is displayed in the SOC Operator Dashboard. The operator reviews the reasoning, image snapshot, and bilingual reports, then enters notes and clicks **Approve**, **Reject**, or **Escalate**.
8. **Forensic Handoff & Dispatch**:
   - On **Approval / Escalation**, the system compiles a forensic PDF report containing the chain of custody and computes a SHA-256 seal. It packs the PDF, metadata, and original frame into a signed ZIP archive stored in the local evidence vault (or uploaded to Alibaba Cloud OSS in production).
   - If configured, Twilio and SendGrid dispatch SMS and email alerts to emergency contacts.
9. **Semantic Search**: Operators can type queries (e.g., *"Show me all critical intrusions at night"*) which are translated by Qwen-Plus into SQL WHERE clauses to search the SQLite/PostgreSQL incident database.
