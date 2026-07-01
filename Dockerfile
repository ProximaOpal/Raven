FROM python:3.11-slim

# System deps for OpenCV + WeasyPrint
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf-2.0-0 libgdk-pixbuf-xlib-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download YOLOv8-nano weights
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

COPY . .

RUN mkdir -p evidence_store demo/sample_incidents

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
