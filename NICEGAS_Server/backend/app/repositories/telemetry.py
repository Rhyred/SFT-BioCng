from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryCreate
from app.repositories.base import BaseRepository

class RepositoryTelemetry(BaseRepository[Telemetry, TelemetryCreate]):
    pass

telemetry = RepositoryTelemetry(Telemetry)
