from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import User
from app.schemas.auth import UserCreate
from app.repositories.base import BaseRepository
from app.core.security import hash_password

class RepositoryUser(BaseRepository[User, UserCreate]):
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_by_username_or_email(self, db: Session, identifier: str) -> Optional[User]:
        return db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

    def create_with_password(self, db: Session, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            hashed_password=hash_password(obj_in.password),
            name=obj_in.name,
            role=obj_in.role,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

user = RepositoryUser(User)
