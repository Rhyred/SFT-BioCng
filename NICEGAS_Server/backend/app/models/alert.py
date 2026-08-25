from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from app.models.base import UUIDMixin

class Alert(Base, UUIDMixin):
    __tablename__ = "alerts"

    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    component = Column(String, nullable=True, index=True)
    severity = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True, default="active")
    message = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    device = relationship("Device", back_populates="alerts")

    __table_args__ = (
        Index("idx_alerts_device_timestamp", "device_id", "timestamp"),
    )
