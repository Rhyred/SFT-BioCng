from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import UUID4
from datetime import datetime
from typing import Optional
from app.db.database import get_db
from app.repositories import telemetry as telemetry_repo
from app.schemas.telemetry import TelemetryResponse
from app.schemas.common import PaginatedResponse
from app.models.telemetry import Telemetry

router = APIRouter()

@router.get("", response_model=PaginatedResponse[TelemetryResponse])
def get_telemetry(
    device_id: UUID4,
    start_time: datetime,
    end_time: datetime,
    component: Optional[str] = None,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    if start_time >= end_time:
        raise HTTPException(
            status_code=400, 
            detail={"code": "INVALID_TIME_RANGE", "message": "start_time must be before end_time"}
        )

    filters = [
        Telemetry.device_id == device_id,
        Telemetry.timestamp >= start_time,
        Telemetry.timestamp <= end_time
    ]
    
    if component:
        filters.append(Telemetry.component == component)
        
    return telemetry_repo.get_paginated(db, page=page, limit=limit, filters=filters)
