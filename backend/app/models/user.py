from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    PUBLIC = "PUBLIC"
    OFFICIAL = "OFFICIAL"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            val_upper = value.upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name of user")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 characters)")
    role: UserRole = Field(default=UserRole.PUBLIC, description="Role: PUBLIC or OFFICIAL")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty")
        return cleaned


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    created_at: datetime


class UserInDB(BaseModel):
    id: str
    name: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
