from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.database import Base
from app.models.base import UUIDMixin

class Telemetry(Base, UUIDMixin):
    __tablename__ = "telemetry"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    component = Column(String, nullable=True, index=True)
    metrics = Column(JSONB, nullable=False)
    status = Column(String, nullable=True)

    device = relationship("Device", back_populates="telemetry")

    # Composite index for efficient timeseries queries per device
    __table_args__ = (
        Index("idx_telemetry_device_timestamp", "device_id", "timestamp"),
    )
