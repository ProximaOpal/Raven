"""
Raven AI CCTV — Cameras Router
GET/POST /api/cameras, PATCH /api/cameras/{id}
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Camera, Operator
from backend.schemas import CameraCreate, CameraOut, CameraUpdate
from backend.auth import require_role

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.id))
    return result.scalars().all()


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_role("ADMIN", "SOC")),
):
    cam = Camera(**body.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.patch("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: int,
    body: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_role("ADMIN", "SOC")),
):
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cam, field, value)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
    operator: Operator = Depends(require_role("ADMIN", "SOC")),
):
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(cam)
    await db.commit()

