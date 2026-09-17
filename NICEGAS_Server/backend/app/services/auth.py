from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.repositories.user import user as user_repo
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginRequest, LoginResponse, LoginUser

class AuthService:
    def authenticate_user(
        self, db: Session, identifier: str, password: str
    ) -> Optional[User]:
        db_user = user_repo.get_by_username_or_email(db, identifier.strip())
        if not db_user:
            return None
        if not verify_password(password, db_user.hashed_password):
            return None
        return db_user

    def login_user(self, db: Session, login_data: LoginRequest) -> LoginResponse:
        identifier = login_data.username or login_data.email
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Username or email is required"}
            )

        db_user = self.authenticate_user(db, identifier, login_data.password)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Username atau password salah"}
            )

        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INACTIVE_USER", "message": "Akun pengguna tidak aktif"}
            )

        token_payload = {
            "sub": str(db_user.id),
            "role": db_user.role,
            "name": db_user.name,
            "email": db_user.email,
            "username": db_user.username,
        }
        access_token = create_access_token(token_payload)

        return LoginResponse(
            token=access_token,
            user=LoginUser(
                id=str(db_user.id),
                name=db_user.name,
                role=db_user.role,
                email=db_user.email,
                username=db_user.username,
            )
        )

auth_service = AuthService()
