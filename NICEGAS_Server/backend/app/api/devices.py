from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import UUID4
from typing import Optional
from app.db.database import get_db
from app.repositories import device as device_repo
from app.schemas.device import DeviceResponse
from app.schemas.common import PaginatedResponse
from app.models.device import Device

router = APIRouter()

@router.get("", response_model=PaginatedResponse[DeviceResponse])
def get_devices(
    db: Session = Depends(get_db),
    project_id: Optional[UUID4] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    filters = []
    if project_id:
        filters.append(Device.project_id == project_id)
        
    return device_repo.get_paginated(db, page=page, limit=limit, filters=filters)

@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(
    device_id: UUID4,
    db: Session = Depends(get_db)
):
    device = device_repo.get(db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail={"code": "DEVICE_NOT_FOUND", "message": "Device not found"})
    return device
