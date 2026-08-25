from app.models.project import Project
from app.schemas.project import ProjectCreate
from app.repositories.base import BaseRepository

class RepositoryProject(BaseRepository[Project, ProjectCreate]):
    pass

project = RepositoryProject(Project)
