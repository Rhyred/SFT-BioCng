from app.models.alert import Alert
from app.schemas.alert import AlertCreate
from app.repositories.base import BaseRepository

class RepositoryAlert(BaseRepository[Alert, AlertCreate]):
    pass

alert = RepositoryAlert(Alert)
