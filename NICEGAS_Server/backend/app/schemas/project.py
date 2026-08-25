from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    location: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
