from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import AuthSessionModel, Base, NutritionProgramDayModel, NutritionProgramModel, UserModel
from app.models.base import utcnow
from app.services.auth_service import create_session, create_user, verify_password


DAY_INTERVAL_SECONDS = get_settings().effective_nutrition_day_interval_seconds

def _program_interval(multiplier: float = 1.0) -> timedelta:
    return timedelta(seconds=DAY_INTERVAL_SECONDS * multiplier)


def _move_program_to_day(program, day_number: int, duration_days: int) -> None:
    # Keep tests valid for both production-like 24h windows and accelerated demo windows.
    program.started_at = utcnow() - _program_interval(day_number - 1) - timedelta(seconds=2)
    program.ends_at = program.started_at + _program_interval(duration_days - 1)



@pytest.fixture()
def db_runtime(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'guided.db').as_posix()}",
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


def _assessment(stage: str = "toddler") -> dict:
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


def _register(client: TestClient, email: str, password: str = "SehatinPass123"):
    response = client.post("/api/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response


def _completed_checklist(client: TestClient, program_id: str, day_number: int) -> list[bool]:
    """Build a completion payload from the authoritative day plan.

    Elderly task counts are adaptive, so regression tests must not assume the
    legacy three-item checklist.
    """
    response = client.get(f"/api/nutrition/program/{program_id}/days/{day_number}")
    assert response.status_code == 200, response.text
    checklist = response.json()["day"].get("checklist") or []
    assert checklist, response.text
    return [True] * len(checklist)


def test_auth_register_hashes_password_and_duplicate_email_is_rejected(db_runtime):
    client = TestClient(app)
    first = _register(client, "caregiver@example.com")
    assert first.json()["user"]["email"] == "caregiver@example.com"
    assert "sehatin_session" in first.cookies

    with db_runtime() as db:
        user = db.scalar(select(UserModel).where(UserModel.email == "caregiver@example.com"))
        assert user is not None
        assert user.password_hash != "SehatinPass123"
        assert user.password_hash.startswith("scrypt$")
        assert verify_password("SehatinPass123", user.password_hash)

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "caregiver@example.com", "password": "DifferentPass123"},
    )
    assert duplicate.status_code == 409
    assert "password" not in duplicate.text.lower()


def test_auth_password_rules_login_logout_and_expiry(db_runtime):
    client = TestClient(app)
    invalid = client.post("/api/auth/register", json={"email": "a@example.com", "password": "short"})
    assert invalid.status_code == 422

    _register(client, "login@example.com")
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    wrong = client.post("/api/auth/login", json={"email": "login@example.com", "password": "WrongPass123"})
    assert wrong.status_code == 401
    assert "tidak sesuai" in wrong.json()["error"]["message"].lower()

    good = client.post("/api/auth/login", json={"email": "login@example.com", "password": "SehatinPass123"})
    assert good.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    # Expired server-side session must invalidate the HttpOnly cookie token.
    with db_runtime() as db:
        session = db.scalar(select(AuthSessionModel).order_by(AuthSessionModel.created_at.desc()))
        assert session is not None
        session.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_anthropometric_validation_valid_warning_invalid(db_runtime):
    client = TestClient(app)

    valid_baby = client.post("/api/nutrition/validate", json=_assessment("mpasi"))
    assert valid_baby.status_code == 200
    assert valid_baby.json()["status"] == "VALID"
    assert valid_baby.json()["references"][0]["source"] == "World Health Organization"

    warning_baby = client.post(
        "/api/nutrition/validate",
        json={**_assessment("mpasi"), "weight_kg": 13.0},
    )
    assert warning_baby.status_code == 200
    assert warning_baby.json()["status"] == "WARNING"
    assert warning_baby.json()["can_process"] is True
    assert "referensi" in warning_baby.json()["message"].lower()

    invalid_baby = client.post(
        "/api/nutrition/validate",
        json={**_assessment("mpasi"), "weight_kg": 80.0},
    )
    assert invalid_baby.status_code == 200
    assert invalid_baby.json()["status"] == "INVALID"
    assert invalid_baby.json()["can_process"] is False

    valid_toddler = client.post("/api/nutrition/validate", json=_assessment("toddler"))
    assert valid_toddler.json()["status"] == "VALID"

    valid_elderly = client.post("/api/nutrition/validate", json=_assessment("elderly"))
    assert valid_elderly.json()["status"] == "VALID"
    assert any(item["indicator"] == "body_mass_index_context" for item in valid_elderly.json()["indicators"])

    impossible_elderly = client.post(
        "/api/nutrition/validate",
        json={**_assessment("elderly"), "weight_kg": 180.0, "height_cm": 140.0},
    )
    assert impossible_elderly.json()["status"] == "INVALID"


def test_recommendation_includes_server_validation_and_rejects_impossible_input(db_runtime):
    client = TestClient(app)
    good = client.post("/api/nutrition/recommendation", json=_assessment("toddler"))
    assert good.status_code == 200
    assert good.json()["validation"]["status"] == "VALID"

    invalid = client.post(
        "/api/nutrition/recommendation",
        json={**_assessment("elderly"), "weight_kg": 180.0, "height_cm": 140.0},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "INVALID_INPUT"


def test_guided_program_calendar_save_persistence_completion_and_ownership(db_runtime):
    client_a = TestClient(app)
    client_b = TestClient(app)
    _register(client_a, "user-a@example.com")
    _register(client_b, "user-b@example.com")

    created = client_a.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    assert created.json()["status"] == "ACTIVE"
    assert created.json()["duration_days"] == 7
    assert created.json()["progress_percent"] == 0
    assert created.json()["completed_tasks"] == 0

    own = client_a.get(f"/api/nutrition/program/{program_id}")
    assert own.status_code == 200
    assert len(own.json()["days"]) == 7
    assert own.json()["days"][0]["locked"] is False
    assert own.json()["days"][1]["locked"] is True
    assert own.json()["profile"]["stage"] == "toddler"

    # Program ownership is enforced; another authenticated user sees 404.
    assert client_b.get(f"/api/nutrition/program/{program_id}").status_code == 404
    assert client_b.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": [True, True, True], "has_complaint": False},
    ).status_code == 404

    # Backend locking cannot be bypassed with a manual API request.
    locked = client_a.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 2, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "PROGRAM_DAY_LOCKED"

    # Partial checklist persists but does not advance the day.
    partial = client_a.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": [True, True, False]},
    )
    assert partial.status_code == 200
    assert partial.json()["saved"] is True
    assert partial.json()["day_completed"] is False
    assert partial.json()["days_completed"] == 0
    assert partial.json()["current_day"] == 1
    assert partial.json()["completed_tasks"] == 2

    # Completion is authoritative only after DB commit.
    completed_day_one = client_a.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True, True, True],
            "has_complaint": False,
            "meal_label": "Makan siang",
            "meal_notes": "Panduan dapat diterapkan.",
        },
    )
    assert completed_day_one.status_code == 200
    body = completed_day_one.json()
    assert body["saved"] is True
    assert body["day_completed"] is True
    assert body["days_completed"] == 1
    assert body["completed_tasks"] == 3
    # Completing a day does not advance calendar time.
    assert body["current_day"] == 1
    assert body["progress_percent"] == 14.29
    assert body["program_status"] == "ACTIVE"
    assert body["saved_at"]

    # Move calendar time to Day 2. Day 2 unlocks because time advanced, not because
    # completing Day 1 changed current_day.
    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        _move_program_to_day(program, 2, 7)
        db.commit()

    # Day 3 is still future-locked.
    day_three = client_a.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 3, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert day_three.status_code == 409
    assert day_three.json()["error"]["code"] == "PROGRAM_DAY_LOCKED"

    # Detail/list reload from the database, including checklist and meal note.
    reloaded = client_a.get(f"/api/nutrition/program/{program_id}")
    assert reloaded.status_code == 200
    assert reloaded.json()["days"][0]["checklist_state"] == [True, True, True]
    assert reloaded.json()["days"][0]["meal_notes"] == "Panduan dapat diterapkan."
    assert reloaded.json()["days"][1]["locked"] is False
    assert reloaded.json()["days"][2]["locked"] is True
    listed = client_a.get("/api/nutrition/program")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == program_id
    assert listed.json()[0]["current_day"] == 2

    # Complete the rest while advancing calendar time one day at a time.
    for day_number in range(2, 8):
        with db_runtime() as db:
            program = db.get(NutritionProgramModel, program_id)
            _move_program_to_day(program, day_number, 7)
            db.commit()
        saved = client_a.post(
            f"/api/nutrition/program/{program_id}/daily-log",
            json={"day_number": day_number, "checklist_state": [True, True, True], "has_complaint": False},
        )
        assert saved.status_code == 200, saved.text

    finished = client_a.get(f"/api/nutrition/program/{program_id}")
    assert finished.status_code == 200
    assert finished.json()["status"] == "COMPLETED"
    assert finished.json()["completed_at"] is not None
    assert finished.json()["days_completed"] == 7
    assert finished.json()["current_day"] == 7
    assert finished.json()["progress_percent"] == 100

    blocked_after_completion = client_a.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 7, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert blocked_after_completion.status_code == 409
    assert blocked_after_completion.json()["error"]["code"] == "PROGRAM_COMPLETED"

    evaluation = client_a.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["meal_log_count"] == 1
    assert evaluation.json()["guidance_completion"] == 100
    assert "bukan kondisi kesehatan atau diagnosis" in evaluation.json()["summary"].lower()

    # Logout removes access, login restores the same DB-backed program.
    assert client_a.post("/api/auth/logout").status_code == 204
    assert client_a.get(f"/api/nutrition/program/{program_id}").status_code == 401
    login = client_a.post("/api/auth/login", json={"email": "user-a@example.com", "password": "SehatinPass123"})
    assert login.status_code == 200
    restored = client_a.get("/api/nutrition/program")
    assert restored.status_code == 200
    assert restored.json()[0]["status"] == "COMPLETED"
    assert restored.json()[0]["progress_percent"] == 100



def test_program_progress_goal_progress_missed_and_inactivity_are_separate(db_runtime):
    from app.models import NutritionProgramModel

    client = TestClient(app, client=("metrics-client", 50000))
    _register(client, "metrics@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    day1 = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": _completed_checklist(client, program_id, 1), "has_complaint": False},
    )
    assert day1.status_code == 200
    first = day1.json()
    assert first["days_completed"] == 1
    assert first["progress_percent"] == 7.14
    assert first["goals"][0]["target"] == 10
    assert first["goals"][0]["actual"] == 1
    assert first["goals"][0]["progress_percentage"] == 10.0

    # Simulate returning on calendar Day 4. Day 2 and Day 3 become missed,
    # while completion remains based only on saved completed days.
    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        _move_program_to_day(program, 4, 14)
        program.last_activity_at = utcnow() - _program_interval(4)
        db.commit()

    detail = client.get(f"/api/nutrition/program/{program_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["current_day"] == 4
    assert data["days_completed"] == 1
    assert data["missed_days"] == 2
    assert data["progress_percent"] == 7.14
    assert data["inactive_days"] == 3
    assert data["days"][1]["missed"] is True
    assert data["days"][2]["missed"] is True
    assert data["days"][3]["locked"] is False

    past = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 2, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert past.status_code == 409
    assert past.json()["error"]["code"] == "PROGRAM_DAY_CLOSED"

    day4 = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 4, "checklist_state": _completed_checklist(client, program_id, 4), "has_complaint": False},
    )
    assert day4.status_code == 200
    assert day4.json()["days_completed"] == 2
    assert day4.json()["missed_days"] == 2
    assert day4.json()["progress_percent"] == 14.29

def test_guided_program_requires_consent_and_refuses_safety_limited_assessment(db_runtime):
    client = TestClient(app)
    _register(client, "safety@example.com")

    no_consent = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("mpasi"), "consent_to_save": False, "duration_days": 7},
    )
    assert no_consent.status_code == 400

    unsafe = _assessment("elderly")
    unsafe["medical_context"] = "penyakit ginjal"
    limited = client.post(
        "/api/nutrition/program",
        json={"assessment": unsafe, "consent_to_save": True, "duration_days": 7},
    )
    assert limited.status_code == 409
    assert "tenaga kesehatan" in limited.json()["error"]["message"].lower()


def test_who_reference_is_versioned_external_data():
    from app.nutrition_validation.who_reference import DATA_FILE, WHO_CHILD_GROWTH_META, weight_for_age_band

    assert DATA_FILE.name == "who_child_growth_2006_v1.json"
    assert DATA_FILE.exists()
    assert WHO_CHILD_GROWTH_META["source"] == "World Health Organization"
    assert WHO_CHILD_GROWTH_META["version"] == "WHO Child Growth Standards 2006"
    assert WHO_CHILD_GROWTH_META["purpose"] == "screening_reference_only"
    assert weight_for_age_band("male", 6) is not None
    assert weight_for_age_band("female", 60) is not None


def test_goal_history_and_adaptive_extension(db_runtime):
    from app.models import NutritionProgramModel

    client = TestClient(app)
    _register(client, "journey@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    detail = client.get(f"/api/nutrition/program/{program_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["goals"]
    assert "hasil aktual" in body["goals"][0]["measurement_method"].lower()
    assert body["goals"][0]["unit"] == "hari berhasil"
    assert body["days"][0]["action_details"]["completion_criteria"]
    assert body["days"][0]["meal_guidance_details"]["example"]
    assert body["assessment_snapshot"]["stage"] == "elderly"

    # Complete two calendar days only, then simulate the planned duration ending.
    for day_number in (1, 2):
        if day_number == 2:
            with db_runtime() as db:
                program = db.get(NutritionProgramModel, program_id)
                _move_program_to_day(program, 2, 7)
                db.commit()
        saved = client.post(
            f"/api/nutrition/program/{program_id}/daily-log",
            json={"day_number": day_number, "checklist_state": _completed_checklist(client, program_id, day_number), "has_complaint": False},
        )
        assert saved.status_code == 200, saved.text

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        program.ends_at = utcnow() - _program_interval()
        db.commit()

    evaluation = client.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert evaluation.status_code == 200, evaluation.text
    data = evaluation.json()
    assert data["details"]["goal_status"] in {"PARTIALLY_MET", "NOT_MET"}
    assert data["details"]["can_extend"] is True

    info = client.get(f"/api/nutrition/program/{program_id}/extension-recommendation")
    assert info.status_code == 200, info.text
    assert info.json()["remaining_gap"] > 0
    assert info.json()["recommended_days"] >= 7

    not_confirmed = client.post(f"/api/nutrition/program/{program_id}/extend", json={"confirm": False})
    assert not_confirmed.status_code == 400

    extended = client.post(f"/api/nutrition/program/{program_id}/extend", json={"confirm": True})
    assert extended.status_code == 201, extended.text
    extension_id = extended.json()["id"]
    assert extension_id != program_id
    assert extended.json()["parent_program_id"] == program_id
    assert extended.json()["cycle_number"] == 2

    history = client.get("/api/nutrition/history")
    assert history.status_code == 200
    ids = {row["id"] for row in history.json()}
    assert {program_id, extension_id}.issubset(ids)

    detail_history = client.get(f"/api/nutrition/history/{extension_id}")
    assert detail_history.status_code == 200
    assert len(detail_history.json()["extension_history"]) == 2


def test_history_ownership_is_backend_enforced(db_runtime):
    owner = TestClient(app)
    other = TestClient(app)
    _register(owner, "history-owner@example.com")
    _register(other, "history-other@example.com")
    created = owner.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]
    assert other.get(f"/api/nutrition/history/{program_id}").status_code == 404


def test_14_day_program_progress_exact_acceptance_examples_and_goal_8_of_10(db_runtime):
    from app.models import NutritionProgramDayModel

    client = TestClient(app, client=("progress-formula-client", 50020))
    _register(client, "progress-formula@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    def set_completed_days(count: int) -> None:
        with db_runtime() as db:
            rows = list(
                db.scalars(
                    select(NutritionProgramDayModel)
                    .where(NutritionProgramDayModel.program_id == program_id)
                    .order_by(NutritionProgramDayModel.day_number)
                )
            )
            for index, row in enumerate(rows, start=1):
                done = index <= count
                row.completed = done
                row.checklist_state = [done] * len(row.checklist or [])
                row.completed_at = utcnow() if done else None
            db.commit()

    for completed, expected in ((1, 7.14), (7, 50.0), (10, 71.43), (14, 100.0)):
        set_completed_days(completed)
        response = client.get(f"/api/nutrition/program/{program_id}/progress")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["days_completed"] == completed
        assert body["total_days"] == 14
        assert body["progress_percent"] == expected

    # Goal achievement remains separate from program progress: 8/10 = 80%,
    # while program progress for 8/14 is 57.14%.
    set_completed_days(8)
    response = client.get(f"/api/nutrition/program/{program_id}/progress")
    body = response.json()
    assert body["progress_percent"] == 57.14
    assert body["goals"][0]["target"] == 10
    assert body["goals"][0]["actual"] == 8
    assert body["goals"][0]["progress_percentage"] == 80.0


def test_goal_evaluation_met_partial_not_met_and_extension_visibility(db_runtime):
    from app.models import NutritionProgramDayModel

    client = TestClient(app, client=("goal-eval-client", 50021))
    _register(client, "goal-eval@example.com")

    def create_with_actual(actual_days: int) -> str:
        created = client.post(
            "/api/nutrition/program",
            json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 14},
        )
        assert created.status_code == 201, created.text
        program_id = created.json()["id"]
        with db_runtime() as db:
            program = db.get(NutritionProgramModel, program_id)
            rows = list(
                db.scalars(
                    select(NutritionProgramDayModel)
                    .where(NutritionProgramDayModel.program_id == program_id)
                    .order_by(NutritionProgramDayModel.day_number)
                )
            )
            for index, row in enumerate(rows, start=1):
                done = index <= actual_days
                row.completed = done
                row.checklist_state = [done] * len(row.checklist or [])
                row.completed_at = utcnow() if done else None
            program.status = "COMPLETED"
            program.completed_at = utcnow()
            program.ends_at = utcnow() - _program_interval()
            db.commit()
        return program_id

    cases = [
        (10, "MET", False),
        (7, "PARTIALLY_MET", True),
        (3, "NOT_MET", True),
    ]
    for actual, expected_status, should_extend in cases:
        program_id = create_with_actual(actual)
        evaluation = client.get(f"/api/nutrition/program/{program_id}/evaluation")
        assert evaluation.status_code == 200, evaluation.text
        assert evaluation.json()["details"]["goal_status"] == expected_status
        assert evaluation.json()["details"]["can_extend"] is should_extend

        extension_info = client.get(f"/api/nutrition/program/{program_id}/extension-recommendation")
        if should_extend:
            assert extension_info.status_code == 200, extension_info.text
            assert extension_info.json()["remaining_gap"] == 10 - actual
        else:
            assert extension_info.status_code == 409
            assert extension_info.json()["error"]["code"] == "EXTENSION_NOT_NEEDED"


def test_extension_tracks_cycle_progress_and_total_goal_achievement(db_runtime):
    from app.models import NutritionProgramDayModel

    client = TestClient(app, client=("extension-total-client", 50022))
    _register(client, "extension-total@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201
    original_id = created.json()["id"]

    with db_runtime() as db:
        original = db.get(NutritionProgramModel, original_id)
        days = list(db.scalars(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == original_id).order_by(NutritionProgramDayModel.day_number)))
        for index, row in enumerate(days, start=1):
            done = index <= 7
            row.completed = done
            row.checklist_state = [done] * len(row.checklist or [])
            row.completed_at = utcnow() if done else None
        original.status = "COMPLETED"
        original.completed_at = utcnow()
        original.ends_at = utcnow() - _program_interval()
        db.commit()

    extension_info = client.get(f"/api/nutrition/program/{original_id}/extension-recommendation")
    assert extension_info.status_code == 200, extension_info.text
    assert extension_info.json()["previous_actual"] == 7
    assert extension_info.json()["previous_target"] == 10
    assert extension_info.json()["remaining_gap"] == 3
    assert extension_info.json()["cumulative_actual"] == 7
    assert extension_info.json()["cumulative_target"] == 10
    assert extension_info.json()["cumulative_progress"] == 70.0

    extended = client.post(f"/api/nutrition/program/{original_id}/extend", json={"confirm": True})
    assert extended.status_code == 201, extended.text
    extension_id = extended.json()["id"]
    assert extended.json()["goal"]["target"] == 3
    assert extended.json()["cumulative_goal"]["actual"] == 7
    assert extended.json()["cumulative_goal"]["target"] == 10

    def set_extension_actual(count: int) -> None:
        with db_runtime() as db:
            rows = list(db.scalars(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == extension_id).order_by(NutritionProgramDayModel.day_number)))
            for index, row in enumerate(rows, start=1):
                done = index <= count
                row.completed = done
                row.checklist_state = [done] * len(row.checklist or [])
                row.completed_at = utcnow() if done else None
            db.commit()

    set_extension_actual(2)
    progress = client.get(f"/api/nutrition/program/{extension_id}/progress")
    assert progress.status_code == 200
    body = progress.json()
    assert body["goals"][0]["actual"] == 2
    assert body["goals"][0]["target"] == 3
    assert body["goals"][0]["progress_percentage"] == 66.7
    assert body["cumulative_goal"]["actual"] == 9
    assert body["cumulative_goal"]["target"] == 10
    assert body["cumulative_goal"]["progress_percentage"] == 90.0

    set_extension_actual(3)
    progress = client.get(f"/api/nutrition/program/{extension_id}/progress").json()
    assert progress["cumulative_goal"]["actual"] == 10
    assert progress["cumulative_goal"]["progress_percentage"] == 100.0
    assert progress["cumulative_goal"]["status"] == "MET"


def test_all_program_goal_progress_evaluation_extension_endpoints_enforce_ownership(db_runtime):
    owner = TestClient(app, client=("owner-all-client", 50023))
    other = TestClient(app, client=("other-all-client", 50024))
    _register(owner, "all-owner@example.com")
    _register(other, "all-other@example.com")
    created = owner.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    protected_gets = [
        f"/api/nutrition/program/{program_id}",
        f"/api/nutrition/history/{program_id}",
        f"/api/nutrition/program/{program_id}/progress",
        f"/api/nutrition/program/{program_id}/evaluation",
        f"/api/nutrition/program/{program_id}/extension-recommendation",
        f"/api/nutrition/program/{program_id}/days/1",
    ]
    for path in protected_gets:
        assert other.get(path).status_code == 404, path

    assert other.post(f"/api/nutrition/program/{program_id}/extend", json={"confirm": True}).status_code == 404
    assert other.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": True}).status_code == 404
    assert other.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": [True, True, True], "has_complaint": False},
    ).status_code == 404


def test_current_day_calendar_boundaries_and_final_day_closes_with_missed_days(db_runtime):
    client = TestClient(app, client=("calendar-boundary-client", 50025))
    _register(client, "calendar-boundary@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 14},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    # Backend owns current_day from program dates: Day 1, 2, 13, and 14.
    for offset, expected_day in ((0, 1), (1, 2), (12, 13), (13, 14)):
        with db_runtime() as db:
            program = db.get(NutritionProgramModel, program_id)
            _move_program_to_day(program, expected_day, 14)
            program.status = "ACTIVE"
            program.completed_at = None
            db.commit()
        progress = client.get(f"/api/nutrition/program/{program_id}/progress")
        assert progress.status_code == 200
        assert progress.json()["current_day"] == expected_day

    # On calendar Day 14, completing Day 14 closes the duration even if the
    # previous calendar days were missed; those missed days do not become completed.
    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        _move_program_to_day(program, 14, 14)
        db.commit()
    final_save = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 14, "checklist_state": _completed_checklist(client, program_id, 14), "has_complaint": False},
    )
    assert final_save.status_code == 200, final_save.text
    final = final_save.json()
    assert final["program_status"] == "COMPLETED"
    assert final["completed_at"] is not None
    assert final["days_completed"] == 1
    assert final["missed_days"] == 13
    assert final["progress_percent"] == 7.14

    evaluation = client.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["details"]["goal_status"] == "NOT_MET"
    assert evaluation.json()["details"]["can_extend"] is True


def test_daily_progress_closes_at_midnight_for_all_nutrition_stages(db_runtime):
    from datetime import timedelta
    from app.models import NutritionProgramModel
    from app.models.base import utcnow

    for index, stage in enumerate(("mpasi", "toddler", "elderly")):
        client = TestClient(app, client=(f"midnight-{stage}", 50300 + index))
        _register(client, f"midnight-{stage}@example.com")
        created = client.post(
            "/api/nutrition/program",
            json={"assessment": _assessment(stage), "consent_to_save": True, "duration_days": 14},
        )
        assert created.status_code == 201, created.text
        program_id = created.json()["id"]

        # Put Day 1 on the previous local calendar date. In the normal 24-hour
        # schedule, the next local midnight closes Day 1 and opens Day 2.
        with db_runtime() as db:
            program = db.get(NutritionProgramModel, program_id)
            now = utcnow()
            program.started_at = now - timedelta(days=1)
            program.ends_at = program.started_at + timedelta(days=13)
            program.status = "ACTIVE"
            program.completed_at = None
            db.commit()

        detail = client.get(f"/api/nutrition/program/{program_id}")
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["current_day"] == 2
        assert body["days"][0]["status"] == "MISSED"
        assert body["days"][0]["missed"] is True
        assert body["days"][0]["locked"] is False
        assert body["days"][1]["status"] in {"AVAILABLE", "IN_PROGRESS"}

        # The backend also rejects any attempt to modify the expired daily progress.
        blocked = client.post(
            f"/api/nutrition/program/{program_id}/daily-log",
            json={"day_number": 1, "checklist_state": [], "has_complaint": False},
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "PROGRAM_DAY_CLOSED"


def test_program_auto_finalizes_only_after_planned_end_calendar_date(db_runtime):
    client = TestClient(app, client=("after-end-client", 50026))
    _register(client, "after-end@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 14},
    )
    program_id = created.json()["id"]

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        program.started_at = utcnow() - _program_interval(14) - timedelta(seconds=2)
        program.ends_at = program.started_at + _program_interval(13)
        program.status = "ACTIVE"
        program.completed_at = None
        db.commit()

    progress = client.get(f"/api/nutrition/program/{program_id}/progress")
    assert progress.status_code == 200
    body = progress.json()
    assert body["current_day"] == 14
    assert body["program_status"] == "COMPLETED"
    assert body["completed_at"] is not None
    assert body["days_completed"] == 0
    assert body["missed_days"] == 14
    assert body["progress_percent"] == 0.0


def test_day_availability_uses_backend_schedule_and_countdown(db_runtime):
    client = TestClient(app, client=("unlock-client", 50100))
    _register(client, "unlock@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    day1 = client.get(f"/api/nutrition/program/{program_id}/days/1")
    day2 = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day1.status_code == 200
    assert day1.json()["day"]["status"] == "AVAILABLE"
    assert day2.status_code == 200
    assert day2.json()["day"]["status"] == "LOCKED"
    # In the normal schedule Day 2 opens at the next local midnight, not 24h
    # after the exact program start time.
    remaining = day2.json()["day"]["remaining_seconds"]
    assert 0 < remaining <= 86400
    assert day2.json()["day"]["recommended_action"] == ""
    assert day2.json()["day"]["checklist"] == []

    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert saved.status_code == 200
    assert saved.json()["day_completed"] is True
    # Completion does not fast-forward the schedule.
    day2_after = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day2_after.json()["day"]["status"] == "LOCKED"
    assert day2_after.json()["day"]["remaining_seconds"] > 0

    # Move the authoritative schedule forward by one full interval.
    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        _move_program_to_day(program, 2, 7)
        db.commit()

    day2_open = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day2_open.status_code == 200
    assert day2_open.json()["day"]["status"] == "AVAILABLE"
    assert day2_open.json()["day"]["recommended_action"]
    day3 = client.get(f"/api/nutrition/program/{program_id}/days/3")
    assert day3.json()["day"]["status"] == "LOCKED"


def test_cancel_plan_preserves_history_and_blocks_future_updates(db_runtime):
    owner = TestClient(app, client=("cancel-owner", 50101))
    other = TestClient(app, client=("cancel-other", 50102))
    _register(owner, "cancel-owner@example.com")
    _register(other, "cancel-other@example.com")
    created = owner.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("elderly"), "consent_to_save": True, "duration_days": 7},
    )
    program_id = created.json()["id"]

    assert owner.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": False}).status_code == 400
    assert other.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": True}).status_code == 404

    cancelled = owner.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": True})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancelled_at"] is not None

    history = owner.get("/api/nutrition/history")
    assert history.status_code == 200
    row = next(item for item in history.json() if item["id"] == program_id)
    assert row["status"] == "CANCELLED"
    assert row["cancelled_at"] is not None

    write = owner.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={"day_number": 1, "checklist_state": [True, True, True], "has_complaint": False},
    )
    assert write.status_code == 409
    assert write.json()["error"]["code"] == "PROGRAM_CANCELLED"

    evaluation = owner.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["details"]["can_extend"] is False

    future_day = owner.get(f"/api/nutrition/program/{program_id}/days/2")
    assert future_day.status_code == 200
    assert future_day.json()["day"]["status"] == "LOCKED"
    assert future_day.json()["day"]["recommended_action"] == ""


def test_cancelled_program_can_be_deleted_but_active_or_foreign_program_cannot(db_runtime):
    owner = TestClient(app, client=("delete-owner", 50110))
    other = TestClient(app, client=("delete-other", 50111))
    _register(owner, "delete-owner@example.com")
    _register(other, "delete-other@example.com")

    created = owner.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("mpasi"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    # Permanent deletion is intentionally gated behind cancellation.
    active_delete = owner.delete(f"/api/nutrition/program/{program_id}")
    assert active_delete.status_code == 409
    assert active_delete.json()["error"]["code"] == "PROGRAM_NOT_CANCELLED"
    assert other.delete(f"/api/nutrition/program/{program_id}").status_code == 404

    cancelled = owner.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": True})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    deleted = owner.delete(f"/api/nutrition/program/{program_id}")
    assert deleted.status_code == 204
    assert owner.get(f"/api/nutrition/program/{program_id}").status_code == 404
    assert owner.get(f"/api/nutrition/history/{program_id}").status_code == 404
    assert all(row["id"] != program_id for row in owner.get("/api/nutrition/history").json())


def test_daily_reflection_and_food_group_state_are_persisted_before_completion(db_runtime):
    client = TestClient(app, client=("reflection-client", 50120))
    _register(client, "reflection@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]

    # All action boxes alone are no longer enough to finalize a day. The user
    # must explicitly answer the daily complaint/reflection question.
    unanswered = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True, True, True],
            "food_group_state": [True, True, False, False, True],
        },
    )
    assert unanswered.status_code == 200
    assert unanswered.json()["day_completed"] is False
    assert unanswered.json()["food_group_state"] == [True, True, False, False, True]
    assert unanswered.json()["has_complaint"] is None

    complaint_without_note = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True, True, True],
            "food_group_state": [True, True, False, False, True],
            "has_complaint": True,
        },
    )
    assert complaint_without_note.status_code == 200
    assert complaint_without_note.json()["day_completed"] is False

    completed = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True, True, True],
            "food_group_state": [True, True, False, False, True],
            "has_complaint": True,
            "complaint_note": "Anak menolak tekstur yang lebih kasar.",
        },
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["day_completed"] is True
    assert body["has_complaint"] is True
    assert body["complaint_note"] == "Anak menolak tekstur yang lebih kasar."

    detail = client.get(f"/api/nutrition/program/{program_id}/days/1")
    assert detail.status_code == 200
    day = detail.json()["day"]
    assert day["food_group_state"] == [True, True, False, False, True]
    assert day["has_complaint"] is True
    assert day["complaint_note"] == "Anak menolak tekstur yang lebih kasar."
    assert "task_results" in day


def test_safety_hold_only_allows_reassessment_and_archives_held_program(db_runtime):
    client = TestClient(app, client=("safety-review-client", 50130))
    _register(client, "safety-review@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        program.status = "SAFETY_HOLD"
        cfg = dict(program.program_config or {})
        cfg["paused_at"] = utcnow().isoformat()
        cfg["last_adaptation"] = {"source_day": 1, "decision": "REFER"}
        cfg["decision_history"] = [{"day": 1, "decision": {"decision": "REFER"}, "safety": {"before_adaptation": {"blocked": True, "emergency": True}}}]
        program.program_config = cfg
        db.commit()

    blocked = client.post(f"/api/nutrition/program/{program_id}/resume", json={"confirm": True})
    assert blocked.status_code == 409

    old_goal_path = client.post(
        f"/api/nutrition/program/{program_id}/safety-review",
        json={"confirm": True, "action": "smaller_goal"},
    )
    assert old_goal_path.status_code == 422

    reviewed = client.post(
        f"/api/nutrition/program/{program_id}/safety-review",
        json={"confirm": True, "action": "restart_assessment"},
    )
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["status"] == "CANCELLED"

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        assert program.status == "CANCELLED"
        assert program.cancelled_at is not None
        last_review = dict((program.program_config or {}).get("last_safety_review") or {})
        assert last_review.get("action") == "restart_assessment"
        assert last_review.get("result") == "program_archived_for_new_assessment"
        assert last_review.get("reason") == "red_flag_requires_new_assessment"


def test_safety_hold_can_be_archived_through_cancel_for_reassessment(db_runtime):
    client = TestClient(app, client=("safety-cancel-client", 50132))
    _register(client, "safety-cancel@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        program.status = "SAFETY_HOLD"
        cfg = dict(program.program_config or {})
        cfg["paused_at"] = utcnow().isoformat()
        program.program_config = cfg
        db.commit()

    archived = client.post(f"/api/nutrition/program/{program_id}/cancel", json={"confirm": True})
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "CANCELLED"

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        review = dict((program.program_config or {}).get("last_safety_review") or {})
        assert review.get("action") == "restart_assessment"
        assert review.get("result") == "program_archived_for_new_assessment"
        assert review.get("reason") == "red_flag_requires_new_assessment"


def test_day_two_plan_is_generated_from_day_two_and_starts_incomplete(db_runtime):
    client = TestClient(app, client=("day-isolation-client", 50131))
    _register(client, "day-isolation@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    initial = client.get(f"/api/nutrition/program/{program_id}").json()
    day_one = initial["days"][0]
    assert day_one["day_number"] == 1
    assert len(day_one["checklist"]) == 3

    completed = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day_one["checklist"]),
            "has_complaint": False,
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["day_completed"] is True

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        _move_program_to_day(program, 2, 7)
        db.commit()

    day_two_response = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day_two_response.status_code == 200, day_two_response.text
    day_two = day_two_response.json()["day"]
    assert day_two["day_number"] == 2
    # Three actions are intentional: build_personalized_tasks caps the daily
    # behavior plan at three measurable actions. What must not carry over is
    # Day 1 completion state.
    assert len(day_two["checklist"]) == 3
    assert len(day_two["action_details"]["tasks"]) == 3
    assert all(task.get("input_type") for task in day_two["action_details"]["tasks"])
    assert all(task.get("result_prompt") for task in day_two["action_details"]["tasks"])
    assert day_two["checklist_state"] == [False, False, False]
    assert day_two["completed"] is False
    assert day_two["completed_at"] is None
    assert day_two["status"] in {"AVAILABLE", "IN_PROGRESS"}

    # Opening/reloading Day 2 is read-only with respect to completion state.
    again = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert again.status_code == 200
    assert again.json()["day"]["checklist_state"] == [False, False, False]
    assert again.json()["day"]["completed"] is False



def _result_payload_for_tasks(tasks: list[dict]) -> dict[str, object]:
    result: dict[str, object] = {}
    for index, task in enumerate(tasks):
        key = str(task.get("key") or task.get("id") or f"task_{index}")
        input_type = task.get("input_type")
        if input_type == "count":
            target = task.get("target_value")
            result[key] = int(target) if isinstance(target, (int, float)) else 1
        elif input_type == "boolean":
            result[key] = bool(task.get("target_value"))
        elif input_type in {"choice", "rating", "observation"}:
            options = task.get("options") or []
            result[key] = options[0]["value"] if options else str(task.get("target_value") or "recorded")
        else:
            result[key] = True
    return result


def test_structured_child_day_schema_persists_across_day_two_day_three_and_reload(db_runtime):
    from app.models import NutritionProgramDayModel

    client = TestClient(app, client=("structured-day-client", 50132))
    _register(client, "structured-day@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("toddler"), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    day_one = detail["days"][0]
    day_one_tasks = day_one["action_details"]["tasks"]
    assert len(day_one_tasks) == 3
    assert all(task.get("target_label") for task in day_one_tasks)
    assert all(task.get("input_type") for task in day_one_tasks)
    assert all(task.get("result_prompt") for task in day_one_tasks)

    day_one_save = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day_one_tasks),
            "task_results": _result_payload_for_tasks(day_one_tasks),
            "has_complaint": False,
            "portion": "partial",
            "acceptance": "neutral",
            "child_condition": "healthy",
            "new_food": False,
            "reaction": "none",
            "caregiver_adherence": "yes",
            "parent_difficulty": "easy",
        },
    )
    assert day_one_save.status_code == 200, day_one_save.text
    assert day_one_save.json()["day_completed"] is True

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        _move_program_to_day(program, 2, 7)
        db.commit()

        day_two_row = db.scalar(select(NutritionProgramDayModel).where(
            NutritionProgramDayModel.program_id == program_id,
            NutritionProgramDayModel.day_number == 2,
        ))
        assert day_two_row is not None
        # The adaptive loop persisted the real next-day plan. It is not a
        # generic checklist and it starts with an isolated completion state.
        assert len((day_two_row.action_details or {}).get("tasks") or []) == 3
        assert day_two_row.checklist_state == [False, False, False]
        assert day_two_row.completed is False

    day_two = client.get(f"/api/nutrition/program/{program_id}/days/2").json()["day"]
    day_two_tasks = day_two["action_details"]["tasks"]
    assert len(day_two_tasks) == 3
    assert all(task.get("target_label") for task in day_two_tasks)
    assert all(task.get("input_type") for task in day_two_tasks)
    assert all(task.get("result_prompt") for task in day_two_tasks)
    assert day_two["checklist_state"] == [False, False, False]
    assert day_two["completed"] is False
    assert day_two["action_details"].get("generated_from_day") == 1

    day_two_results = _result_payload_for_tasks(day_two_tasks)
    saved_two = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 2,
            "checklist_state": [True] * len(day_two_tasks),
            "task_results": day_two_results,
            "has_complaint": False,
            "portion": "partial",
            "acceptance": "neutral",
            "child_condition": "healthy",
            "new_food": False,
            "reaction": "none",
            "caregiver_adherence": "yes",
            "parent_difficulty": "easy",
        },
    )
    assert saved_two.status_code == 200, saved_two.text
    assert saved_two.json()["day_completed"] is True

    reloaded_two = client.get(f"/api/nutrition/program/{program_id}/days/2").json()["day"]
    assert reloaded_two["task_results"] == day_two_results
    assert reloaded_two["checklist_state"] == [True, True, True]
    assert reloaded_two["completed"] is True

    with db_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        assert program is not None
        _move_program_to_day(program, 3, 7)
        db.commit()

        day_three_row = db.scalar(select(NutritionProgramDayModel).where(
            NutritionProgramDayModel.program_id == program_id,
            NutritionProgramDayModel.day_number == 3,
        ))
        assert day_three_row is not None
        assert len((day_three_row.action_details or {}).get("tasks") or []) == 3
        assert day_three_row.checklist_state == [False, False, False]
        assert day_three_row.completed is False

    day_three = client.get(f"/api/nutrition/program/{program_id}/days/3").json()["day"]
    assert len(day_three["action_details"]["tasks"]) == 3
    assert day_three["action_details"].get("generated_from_day") == 2
    assert day_three["checklist_state"] == [False, False, False]
    assert day_three["completed"] is False
    assert day_three["task_results"] == {}


@pytest.mark.parametrize("stage", ["mpasi", "toddler"])
def test_child_red_flag_text_triggers_immediate_safety_hold_before_day_completion(db_runtime, stage):
    client = TestClient(app, client=(f"redflag-{stage}", 50240 if stage == "mpasi" else 50241))
    _register(client, f"redflag-{stage}@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment(stage), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    tasks = detail["days"][0]["action_details"]["tasks"]

    response = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [False] * len(tasks),
            "task_results": {},
            "has_complaint": False,
            "reaction": "detected",
            "reaction_notes": "anak sulit bernapas setelah mencoba makanan",
            "child_condition": "healthy",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["day_completed"] is False
    assert body["program_status"] == "SAFETY_HOLD"
    safety = body["safety"]["before_adaptation"]
    assert safety["emergency"] is True
    assert safety["decision"] == "REFER"
    assert any(flag["code"] == "BREATHING_DIFFICULTY" for flag in safety["red_flags"])
    assert "IGD/rumah sakit" in safety["recommended_action"]


@pytest.mark.parametrize("stage", ["mpasi", "toddler"])
def test_child_reported_reaction_requires_detail_but_mild_text_does_not_trigger_hold(db_runtime, stage):
    client = TestClient(app, client=(f"reaction-detail-{stage}", 50242 if stage == "mpasi" else 50243))
    _register(client, f"reaction-detail-{stage}@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment(stage), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    tasks = client.get(f"/api/nutrition/program/{program_id}").json()["days"][0]["action_details"]["tasks"]
    base_payload = {
        "day_number": 1,
        "checklist_state": [False] * len(tasks),
        "task_results": {},
        "has_complaint": False,
        "reaction": "detected",
        "child_condition": "healthy",
    }

    missing = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=base_payload)
    assert missing.status_code == 422
    assert "Jelaskan reaksi" in missing.text

    mild = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={**base_payload, "reaction_notes": "muncul ruam ringan, anak tetap aktif dan tidak sesak"},
    )
    assert mild.status_code == 200, mild.text
    body = mild.json()
    assert body["program_status"] == "ACTIVE"
    assert body["safety"]["before_adaptation"]["level"] == "OBSERVE"
    assert body["safety"]["before_adaptation"]["emergency"] is False


def test_program_display_name_reuses_existing_title_field_without_migration(db_runtime):
    client = TestClient(app)
    with db_runtime() as db:
        user = create_user(db, email="named-program@example.com", password="SehatinPass123")
        raw_token, _ = create_session(db, user)
        db.commit()
    client.cookies.set("sehatin_session", raw_token)

    named = client.post(
        "/api/nutrition/program",
        json={
            "assessment": _assessment("mpasi"),
            "consent_to_save": True,
            "duration_days": 14,
            "display_name": "MPASI Dinda",
        },
    )
    assert named.status_code == 201, named.text
    assert named.json()["title"] == "MPASI Dinda"

    detail = client.get(f"/api/nutrition/program/{named.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "MPASI Dinda"
    assert detail.json()["stage"] == "mpasi"

    fallback = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment("mpasi"), "consent_to_save": True, "duration_days": 14},
    )
    assert fallback.status_code == 201, fallback.text
    assert fallback.json()["title"] == "Program MPASI"
