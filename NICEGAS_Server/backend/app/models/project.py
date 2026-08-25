from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.base import UUIDMixin, TimestampMixin

class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name = Column(String, index=True, nullable=False)
    location = Column(String, nullable=True)
    
    devices = relationship("Device", back_populates="project", cascade="all, delete-orphan")
