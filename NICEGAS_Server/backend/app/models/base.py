import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID

class UUIDMixin:
    """Provides a UUID primary key column."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

class TimestampMixin:
    """Provides created_at and updated_at timestamp columns."""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
