# NEXUS CCTV — Setup & Run Guide

This guide details setting up, configuring, and running the NEXUS CCTV autopilot system locally or via Docker.

## Prerequisites

- Python 3.10 or 3.11 (Python 3.11 recommended)
- Node.js (Optional, only if running local web server tools, but FastAPI serves the frontend natively)
- Redis Server (Required for Celery task queuing; run locally or via Docker)
- Docker Desktop (Optional, for containerized execution)

---

## 1. Environment Configuration

Clone or navigate to the project directory and create a `.env` file from the example:

```bash
cp .env.example .env
```

Open `.env` and configure the settings:

### Critical Settings
- `DASHSCOPE_API_KEY`: Your Alibaba Cloud DashScope API Key (Required for live Qwen-VL/Qwen-Plus processing).
- `DEMO_MODE`: Set to `True` (default) to use mock Qwen-VL analyses and mock alert dispatchers if you do not have API keys. Set to `False` for live production API execution.

### Optional Integrations
- **Database**: `DATABASE_URL` defaults to SQLite (`sqlite+aiosqlite:///./nexus.db`). For production, supply a PostgreSQL connection string.
- **Twilio (SMS)**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `ALERT_TO_NUMBER`.
- **SendGrid (Email)**: `SENDGRID_API_KEY`, `ALERT_FROM_EMAIL`, `ALERT_TO_EMAIL`.
- **Alibaba Cloud OSS (Storage)**: `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`, `OSS_BUCKET_NAME`, `OSS_ENDPOINT`.

---

## 2. Local Setup (Without Docker)

### Step 2.1: Install Python Dependencies

Using virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual env (Windows)
.\venv\Scripts\activate
# Activate virtual env (Mac/Linux)
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2.2: Start Redis

Ensure Redis is running locally. If you have Docker installed, you can start a Redis broker container instantly:

```bash
docker run -d -p 6379:6379 redis:alpine
```

### Step 2.3: Seed the Database

Seed the database with mock cameras and past incidents to populate the dashboard immediately:

```bash
python demo/mock_data.py
```

### Step 2.4: Start Celery Worker

Start the Celery worker pipeline to process camera frames in the background:

```bash
celery -A backend.workers.pipeline.celery_app worker --loglevel=info -P threads
```
*(Note: `-P threads` or `-P solo` is recommended on Windows to avoid process-spawning issues).*

### Step 2.5: Start FastAPI Backend Server

Run the Uvicorn ASGI server to serve the API and the SOC dashboard frontend:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your web browser and navigate to:
- **SOC Operator Console**: [http://localhost:8000](http://localhost:8000)
- **API Swagger Documentation**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## 3. Running the Camera Ingestion Simulator

To simulate live tactical camera feeds pushing frames into the pipeline, run the simulator CLI tool in a separate terminal:

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run with 4 cameras, sending frames every 10 seconds (indefinitely)
python demo/simulate_camera.py --streams 4 --interval 10
```

### Command Options:
- `--streams`: Number of simulated cameras (1-4).
- `--interval`: Ingestion rate per camera in seconds (e.g., `--interval 5`).
- `--mode`: Set to `stress` to run high QPS loading tests.

---

## 4. Containerized Setup (Docker Compose)

You can spin up the entire multi-service stack (FastAPI, Postgres, Redis, Celery worker) automatically using Docker Compose:

```bash
# Build and run all container services
docker-compose up --build
```

This starts:
- `nexus-api` on [http://localhost:8000](http://localhost:8000)
- `nexus-redis` on port 6379
- `nexus-db` (Postgres database)
- `nexus-worker` (Celery background worker)
