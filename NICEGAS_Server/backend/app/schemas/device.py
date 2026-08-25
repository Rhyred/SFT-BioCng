from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from typing import Optional

class DeviceBase(BaseModel):
    project_id: UUID4
    name: str
    type: str
    status: Optional[str] = "offline"
    firmware: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceResponse(DeviceBase):
    id: UUID4
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
