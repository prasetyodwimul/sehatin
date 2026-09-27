from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import UserModel
from app.services.auth_service import resolve_session


def get_current_user(
    session_cookie: str | None = Cookie(default=None, alias="sehatin_session"),
    db: Session = Depends(get_db),
) -> UserModel:
    try:
        user = resolve_session(db, session_cookie)
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Layanan akun belum tersedia. Coba lagi nanti.")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Silakan login untuk melanjutkan fitur tersimpan.")
    return user


def optional_current_user(
    session_cookie: str | None = Cookie(default=None, alias="sehatin_session"),
    db: Session = Depends(get_db),
) -> UserModel | None:
    try:
        return resolve_session(db, session_cookie)
    except Exception:
        return None
