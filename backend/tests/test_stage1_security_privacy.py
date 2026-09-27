from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.database import get_engine, reset_database_caches, session_scope
from app.main import app
from app.models import Base, NutritionProgramModel, NutritionRequestModel


@pytest.fixture()
def isolated_persistence_db(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'stage1.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("PERSISTENCE_ENABLED", "true")
    monkeypatch.setenv("PERSIST_ANONYMOUS_NUTRITION_PERSONAL_DATA", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    reset_database_caches()
    Base.metadata.create_all(get_engine())
    try:
        yield
    finally:
        reset_database_caches()
        get_settings.cache_clear()


def _assessment() -> dict:
    return {
        "stage": "toddler",
        "age_months": 36,
        "sex": "female",
        "weight_kg": 14.0,
        "height_cm": 95.0,
    }


def test_guest_recommendation_does_not_persist_personal_record_by_default(isolated_persistence_db):
    client = TestClient(app, client=("stage1-guest", 50301))
    response = client.post("/api/nutrition/recommendation", json=_assessment())
    assert response.status_code == 200, response.text
    with session_scope() as db:
        count = db.scalar(select(func.count()).select_from(NutritionRequestModel))
    assert count == 0


def test_authenticated_explicit_program_save_still_persists(isolated_persistence_db):
    # Guided Program persistence is explicit/authenticated and must not depend on
    # the anonymous operational persistence switch.
    get_settings().persistence_enabled = False
    client = TestClient(app, client=("stage1-owner", 50302))
    registered = client.post(
        "/api/auth/register",
        json={"email": "stage1-owner@example.com", "password": "SehatinPass123"},
    )
    assert registered.status_code == 201, registered.text
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    with session_scope() as db:
        count = db.scalar(select(func.count()).select_from(NutritionProgramModel))
    assert count == 1


def test_production_rejects_insecure_auth_cookie():
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            environment="production",
            auth_pepper="production-secret-pepper",
            auth_cookie_secure=False,
        )


def test_production_accepts_secure_auth_cookie_and_development_can_be_insecure():
    production = Settings(
        _env_file=None,
        environment="production",
        auth_pepper="production-secret-pepper",
        auth_cookie_secure=True,
    )
    assert production.auth_cookie_secure is True
    development = Settings(_env_file=None, environment="development", auth_cookie_secure=False)
    assert development.auth_cookie_secure is False
