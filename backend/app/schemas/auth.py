from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
AVATAR_DATA_URL_RE = re.compile(r"^data:image/(?:png|jpeg|jpg|webp);base64,[A-Za-z0-9+/=\s]+$")
MAX_AVATAR_DATA_URL_LENGTH = 1_500_000


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not EMAIL_RE.match(email):
            raise ValueError("Format email tidak valid")
        return email

    @field_validator("password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        if not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value) or not re.search(r"\d", value):
            raise ValueError("Password minimal 10 karakter dan harus memuat huruf besar, huruf kecil, serta angka")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    avatar_data_url: str | None = Field(default=None, max_length=MAX_AVATAR_DATA_URL_LENGTH)
    bio: str | None = Field(default=None, max_length=240)

    @field_validator("full_name", "display_name", "bio")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("avatar_data_url")
    @classmethod
    def validate_avatar(cls, value: str | None) -> str | None:
        if value is None:
            return None
        avatar = value.strip()
        if not avatar:
            return None
        if len(avatar) > MAX_AVATAR_DATA_URL_LENGTH or not AVATAR_DATA_URL_RE.fullmatch(avatar):
            raise ValueError("Foto profil harus berupa PNG, JPG, atau WebP yang valid dan berukuran kecil")
        return avatar


class AuthUserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    full_name: str | None = None
    display_name: str | None = None
    avatar_data_url: str | None = None
    bio: str | None = None


class AuthResponse(BaseModel):
    user: AuthUserResponse
    message: str
