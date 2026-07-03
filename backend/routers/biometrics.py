"""
Raven AI CCTV — Biometrics Router
GET /api/biometrics/profiles, POST /api/biometrics/enroll
"""
import io
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image
import numpy as np
import cv2

from backend.database import get_db
from backend.models import BiometricProfile, Operator
from backend.auth import require_operator
from backend.services.biometrics import BiometricsService

router = APIRouter(prefix="/api/biometrics", tags=["biometrics"])
logger = logging.getLogger(__name__)


@router.get("/profiles")
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_operator),
):
    """List all enrolled biometric profiles."""
    result = await db.execute(select(BiometricProfile).order_by(BiometricProfile.name))
    profiles = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "role": p.role,
            "image_path": p.image_path,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in profiles
    ]


@router.post("/enroll", status_code=201)
async def enroll_profile(
    name: str = Form(...),
    role: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_operator),
):
    """
    Enrolls a new biometric profile.
    Uploads a face image, detects a face, extracts a 128-dim embedding, and registers it.
    """
    # 1. Read file contents
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum size allowed is 5MB."
        )
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image format: {e}")

    # 2. Run face detection
    faces = BiometricsService.detect_faces(frame)
    if not faces:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the image. Please use an image showing a clear, front-facing face."
        )
    
    # Take the largest face if multiple detected
    best_face = max(faces, key=lambda f: f["w"] * f["h"])

    # 3. Extract embedding
    embedding = BiometricsService.extract_embedding(frame, best_face)

    # 4. Save raw image (simulated locally, or save to evidence store)
    from backend.config import get_settings
    settings = get_settings()
    
    import os
    biometrics_dir = os.path.join(settings.evidence_store_path, "biometrics")
    os.makedirs(biometrics_dir, exist_ok=True)
    
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_").lower()
    image_filename = f"{safe_name}_{int(np.mean(embedding)*100000)}.jpg"
    image_path = os.path.join(biometrics_dir, image_filename)
    
    # Save the original image
    cv2.imwrite(image_path, frame)

    # 5. Save database record
    db_profile = BiometricProfile(
        name=name,
        role=role,
        face_encoding=json.dumps(embedding),
        image_path=f"/api/biometrics/image/{image_filename}" # Servable path
    )
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)

    logger.info(f"Biometrics: Enrolled profile {name} as {role} | Image saved: {image_path}")

    return {
        "id": db_profile.id,
        "name": db_profile.name,
        "role": db_profile.role,
        "message": "Biometric profile successfully enrolled"
    }


@router.get("/image/{filename}")
async def serve_biometric_image(filename: str):
    """Serves the enrolled profile's photo."""
    from backend.config import get_settings
    settings = get_settings()
    import os
    from fastapi.responses import FileResponse
    
    image_path = os.path.join(settings.evidence_store_path, "biometrics", filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Biometric photo not found")
        
    return FileResponse(image_path, media_type="image/jpeg")
