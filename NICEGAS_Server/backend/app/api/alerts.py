from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import UUID4
from typing import Optional
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.repositories import alert as alert_repo
from app.schemas.alert import AlertResponse
from app.schemas.common import PaginatedResponse
from app.models.alert import Alert

router = APIRouter()

@router.get("", response_model=PaginatedResponse[AlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    device_id: Optional[UUID4] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    filters = []
    if device_id:
        filters.append(Alert.device_id == device_id)
    if severity:
        filters.append(Alert.severity == severity)
    if status:
        filters.append(Alert.status == status)
        
    return alert_repo.get_paginated(db, page=page, limit=limit, filters=filters)
