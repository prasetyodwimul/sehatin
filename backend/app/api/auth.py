from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models import UserModel
from app.schemas.auth import AuthResponse, AuthUserResponse, LoginRequest, ProfileUpdateRequest, RegisterRequest
from app.services.auth_service import create_session, create_user, find_user_by_email, revoke_session, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: UserModel) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        full_name=user.full_name,
        display_name=user.display_name,
        avatar_data_url=user.avatar_data_url,
        bio=user.bio,
    )


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="sehatin_session",
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        if find_user_by_email(db, payload.email):
            raise HTTPException(status_code=409, detail="Email sudah digunakan.")
        user = create_user(db, email=payload.email, password=payload.password)
        token, _ = create_session(db, user)
        db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email sudah digunakan.")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Pendaftaran belum dapat diproses. Coba lagi nanti.")
    _set_session_cookie(response, token)
    return AuthResponse(user=_user_response(user), message="Akun berhasil dibuat. Data nutrisi hanya akan disimpan saat kamu memilih Save & Start Guided Program.")


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        user = find_user_by_email(db, payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password tidak sesuai.")
        token, _ = create_session(db, user)
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Login belum dapat diproses. Coba lagi nanti.")
    _set_session_cookie(response, token)
    return AuthResponse(user=_user_response(user), message="Login berhasil.")


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    raw_token = request.cookies.get("sehatin_session")
    try:
        revoke_session(db, raw_token)
        db.commit()
    except Exception:
        db.rollback()
    response.delete_cookie("sehatin_session", path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthUserResponse)
def me(user: UserModel = Depends(get_current_user)) -> AuthUserResponse:
    return _user_response(user)


@router.patch("/profile", response_model=AuthUserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthUserResponse:
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(user, field, value)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Profil belum dapat disimpan. Coba lagi nanti.")
    return _user_response(user)
