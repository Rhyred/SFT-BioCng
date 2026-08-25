from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin

class Device(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "devices"

    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="offline")
    firmware = Column(String, nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="devices")
    telemetry = relationship("Telemetry", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
