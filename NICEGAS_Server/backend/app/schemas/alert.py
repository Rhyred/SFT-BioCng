from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from typing import Optional

class AlertBase(BaseModel):
    device_id: UUID4
    component: Optional[str] = None
    severity: str
    status: str = "active"
    message: str
    timestamp: datetime

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: UUID4

    model_config = ConfigDict(from_attributes=True)
