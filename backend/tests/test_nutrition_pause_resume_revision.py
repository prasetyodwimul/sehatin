from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base


@pytest.fixture()
def pause_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'pause-revision.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        yield factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _register(client: TestClient, email: str) -> None:
    response = client.post("/api/auth/register", json={"email": email, "password": "SehatinPass123"})
    assert response.status_code == 201, response.text


def _assessment(stage: str) -> dict:
    if stage == "mpasi":
        return {
            "stage": "mpasi",
            "age_months": 8,
            "sex": "male",
            "weight_kg": 8.2,
            "height_cm": 69.0,
            "feeding_mode": "breastmilk",
        }
    if stage == "elderly":
        return {
            "stage": "elderly",
            "age_years": 70,
            "sex": "female",
            "weight_kg": 55.0,
            "height_cm": 155.0,
        }
    return {
        "stage": "toddler",
        "age_months": 36,
        "sex": "female",
        "weight_kg": 14.0,
        "height_cm": 95.0,
    }


def _create(client: TestClient, stage: str) -> tuple[str, dict]:
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment(stage), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1")
    assert day.status_code == 200, day.text
    return program_id, day.json()["day"]


def _partial_checks(day: dict) -> list[bool]:
    count = len(day["checklist"])
    if count <= 1:
        return [False] * count
    return [True] + [False] * (count - 1)


@pytest.mark.parametrize("stage", ["mpasi", "toddler"])
def test_child_sick_pauses_without_completing_or_losing_progress(pause_db, stage: str):
    client = TestClient(app, client=(f"pause-{stage}", 51101))
    _register(client, f"pause-{stage}@example.com")
    program_id, day = _create(client, stage)
    checks = _partial_checks(day)

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": checks,
            "has_complaint": None,
            "child_condition": "sick",
            "reaction": "none",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["program_status"] == "PAUSED"
    assert body["day_completed"] is False
    assert body["checklist_state"] == checks
    assert body["adaptation"]["decision"] == "PAUSE"

    detail = client.get(f"/api/nutrition/program/{program_id}")
    assert detail.status_code == 200, detail.text
    program = detail.json()
    assert program["status"] == "PAUSED"
    assert program["current_day"] == 1
    assert program["days"][0]["status"] == "IN_PROGRESS"
    assert program["days"][0]["checklist_state"] == checks
    assert program["days"][0]["completed"] is False
    assert program["days"][1]["status"] == "LOCKED"


def test_safety_pause_requires_recovery_check_and_still_unwell_stays_paused(pause_db):
    client = TestClient(app, client=("pause-recovery", 51102))
    _register(client, "pause-recovery@example.com")
    program_id, day = _create(client, "toddler")
    checks = _partial_checks(day)

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": checks, "child_condition": "fever", "reaction": "none"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["program_status"] == "PAUSED"

    missing_check = client.post(f"/api/nutrition/program/{program_id}/resume", json={"confirm": True})
    assert missing_check.status_code == 422

    still_unwell = client.post(
        f"/api/nutrition/program/{program_id}/resume",
        json={"confirm": True, "recovery_status": "still_unwell"},
    )
    assert still_unwell.status_code == 200, still_unwell.text
    assert still_unwell.json()["status"] == "PAUSED"

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    assert detail["current_day"] == 1
    assert detail["days"][0]["checklist_state"] == checks
    assert detail["days"][0]["status"] == "IN_PROGRESS"
    assert detail["days"][1]["status"] == "LOCKED"


def test_improved_resume_returns_active_same_day_and_preserves_progress(pause_db):
    client = TestClient(app, client=("pause-improved", 51103))
    _register(client, "pause-improved@example.com")
    program_id, day = _create(client, "mpasi")
    checks = _partial_checks(day)

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": checks, "child_condition": "diarrhea", "reaction": "none"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["program_status"] == "PAUSED"

    resumed = client.post(
        f"/api/nutrition/program/{program_id}/resume",
        json={"confirm": True, "recovery_status": "improved"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "ACTIVE"
    assert resumed.json()["current_day"] == 1

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    assert detail["status"] == "ACTIVE"
    assert detail["current_day"] == 1
    assert detail["days"][0]["checklist_state"] == checks
    assert detail["days"][0]["completed"] is False
    assert detail["days"][1]["status"] == "LOCKED"


@pytest.mark.parametrize("condition", ["unwell", "nausea", "vomiting", "fever", "diarrhea", "dizziness", "pain_discomfort", "difficulty_eating_drinking", "other_concern"])
def test_elderly_uses_shared_pause_state_without_child_condition(pause_db, condition: str):
    client = TestClient(app, client=(f"elderly-{condition}", 51104))
    _register(client, f"elderly-{condition}@example.com")
    program_id, day = _create(client, "elderly")
    checks = _partial_checks(day)

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": checks,
            "health_condition": condition,
            "has_complaint": None,
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["program_status"] == "PAUSED"
    assert body["day_completed"] is False
    assert body["checklist_state"] == checks
    assert body["safety"]["before_adaptation"]["decision"] == "PAUSE"

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    assert detail["stage"] == "elderly"
    assert detail["current_day"] == 1
    assert detail["days"][0]["status"] == "IN_PROGRESS"
    assert detail["days"][1]["status"] == "LOCKED"

    resumed = client.post(
        f"/api/nutrition/program/{program_id}/resume",
        json={"confirm": True, "recovery_status": "improved"},
    )
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "ACTIVE"
    assert resumed.json()["current_day"] == 1


def test_locked_day_remains_distinct_from_paused_current_day(pause_db):
    client = TestClient(app, client=("pause-locked-distinct", 51105))
    _register(client, "pause-locked-distinct@example.com")
    program_id, day = _create(client, "toddler")

    paused = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": _partial_checks(day), "child_condition": "sick", "reaction": "none"},
    )
    assert paused.status_code == 200, paused.text

    current = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    future = client.get(f"/api/nutrition/program/{program_id}/days/2").json()["day"]
    assert current["status"] in {"AVAILABLE", "IN_PROGRESS"}
    assert current["locked"] is False
    assert future["status"] == "LOCKED"
    assert future["locked"] is True
