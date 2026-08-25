from app.models.device import Device
from app.schemas.device import DeviceCreate
from app.repositories.base import BaseRepository

class RepositoryDevice(BaseRepository[Device, DeviceCreate]):
    pass

device = RepositoryDevice(Device)
