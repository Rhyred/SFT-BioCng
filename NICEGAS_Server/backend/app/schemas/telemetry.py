from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any

class TelemetryBase(BaseModel):
    device_id: UUID4
    timestamp: datetime
    component: Optional[str] = None
    metrics: Dict[str, Any]
    status: Optional[str] = None

class TelemetryCreate(TelemetryBase):
    pass

class TelemetryResponse(TelemetryBase):
    id: UUID4

    model_config = ConfigDict(from_attributes=True)
