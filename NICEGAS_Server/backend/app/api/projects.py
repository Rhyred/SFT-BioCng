from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.repositories import project as project_repo
from app.schemas.project import ProjectResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()

@router.get("", response_model=PaginatedResponse[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    return project_repo.get_paginated(db, page=page, limit=limit)
