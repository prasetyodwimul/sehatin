from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuthSessionModel, UserModel
from app.models.base import utcnow

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32


def _peppered(password: str) -> bytes:
    pepper = get_settings().auth_pepper
    return (password + pepper).encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(_peppered(password), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN)
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$", 5)
        if scheme != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_b64.encode("ascii"))
        actual = hashlib.scrypt(_peppered(password), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_user_by_email(db: Session, email: str) -> UserModel | None:
    return db.scalar(select(UserModel).where(UserModel.email == normalize_email(email)))


def create_user(db: Session, *, email: str, password: str) -> UserModel:
    user = UserModel(email=normalize_email(email), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user


def token_hash(token: str) -> str:
    return hmac.new(get_settings().auth_pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def create_session(db: Session, user: UserModel) -> tuple[str, AuthSessionModel]:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    now = utcnow()
    session = AuthSessionModel(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        expires_at=now + timedelta(minutes=settings.auth_session_minutes),
    )
    db.add(session)
    db.flush()
    return raw_token, session


def resolve_session(db: Session, raw_token: str | None) -> UserModel | None:
    if not raw_token:
        return None
    now = utcnow()
    session = db.scalar(
        select(AuthSessionModel).where(
            AuthSessionModel.token_hash == token_hash(raw_token),
            AuthSessionModel.revoked_at.is_(None),
            AuthSessionModel.expires_at > now,
        )
    )
    if not session:
        return None
    return db.get(UserModel, session.user_id)


def revoke_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    session = db.scalar(select(AuthSessionModel).where(AuthSessionModel.token_hash == token_hash(raw_token)))
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
