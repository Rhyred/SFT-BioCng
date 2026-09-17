from pydantic import BaseModel, ConfigDict, UUID4, model_validator
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.username and not self.email:
            raise ValueError("Either 'username' or 'email' must be provided.")
        return self

class UserBase(BaseModel):
    email: str
    username: str
    name: str
    role: str = "operator"
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID4
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class LoginUser(BaseModel):
    id: str
    name: str
    role: str
    email: Optional[str] = None
    username: Optional[str] = None

class LoginResponse(BaseModel):
    token: str
    user: LoginUser
