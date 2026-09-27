from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Base, NutritionProgramModel
from app.models.base import utcnow
from app.services.auth_service import create_session, create_user
from app.nutrition.daily_results import (
    DailyResultValidationError,
    STAGE6_RULE_VERSION,
    build_daily_task_result,
)


def _count_task(target: int = 3) -> dict:
    return {
        "key": "meal_count",
        "metric_id": "meal_routine",
        "input_type": "count",
        "target_value": target,
        "unit": "meals",
    }


def _boolean_task(target: bool = True) -> dict:
    return {
        "key": "responsive",
        "metric_id": "responsive_feeding",
        "input_type": "boolean",
        "target_value": target,
        "unit": "practice",
    }


def _choice_task() -> dict:
    return {
        "key": "response",
        "metric_id": "food_response",
        "input_type": "choice",
        "target_value": "accepted",
        "unit": "response",
        "options": [
            {"value": "accepted", "label": "Accepted"},
            {"value": "partial", "label": "Partial"},
            {"value": "refused", "label": "Refused"},
        ],
        "adherence_map": {"accepted": 100, "partial": 50, "refused": 0},
    }


def _record(task: dict, value):
    return build_daily_task_result(task, value, action_completed=True, saved_at=utcnow()).as_dict()


@pytest.mark.parametrize(
    ("actual", "expected_adherence", "expected_status"),
    [
        (0, 0.0, "NOT_STARTED"),
        (1, 33.33, "PARTIAL"),
        (2, 66.67, "PARTIAL"),
        (3, 100.0, "COMPLETED"),
        (5, 100.0, "COMPLETED"),
    ],
)
def test_count_adherence_preserves_actual_and_caps_only_adherence(actual, expected_adherence, expected_status):
    row = _record(_count_task(), actual)
    assert row["actual_result"] == actual
    assert row["adherence"] == expected_adherence
    assert row["status"] == expected_status
    if expected_status == "COMPLETED":
        assert row["completed_at"]
    else:
        assert row["completed_at"] is None


def test_boolean_false_is_recorded_not_missing():
    yes = _record(_boolean_task(True), True)
    no = _record(_boolean_task(True), False)
    assert yes["adherence"] == 100.0 and yes["status"] == "COMPLETED"
    assert no["actual_result"] is False
    assert no["adherence"] == 0.0 and no["status"] == "PARTIAL"


def test_choice_uses_single_task_mapping_source():
    accepted = _record(_choice_task(), "accepted")
    partial = _record(_choice_task(), "partial")
    refused = _record(_choice_task(), "refused")
    assert accepted["adherence"] == 100.0
    assert partial["adherence"] == 50.0
    assert refused["adherence"] == 0.0
    assert refused["status"] == "PARTIAL"


def test_observation_and_experience_without_mapping_do_not_invent_score():
    for input_type in ("observation", "simple_experience"):
        task = {
            "key": input_type,
            "metric_id": input_type,
            "input_type": input_type,
            "target_value": "observed",
            "options": [{"value": "observed", "label": "Observed"}],
        }
        row = _record(task, "observed")
        assert row["actual_result"] == "observed"
        assert row["adherence"] is None
        assert row["status"] == "COMPLETED"


@pytest.mark.parametrize("bad", [-1, "abc", "", None, True])
def test_invalid_count_is_rejected(bad):
    with pytest.raises(DailyResultValidationError):
        _record(_count_task(), bad)


def test_invalid_boolean_and_choice_are_rejected():
    non_responsive = {**_boolean_task(), "metric_id": "texture"}
    with pytest.raises(DailyResultValidationError):
        _record(non_responsive, "true")
    with pytest.raises(DailyResultValidationError):
        _record(_choice_task(), "unknown")


@pytest.fixture()
def stage6_runtime(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'stage6.db').as_posix()}",
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


def _authenticate(client: TestClient, factory, email: str):
    with factory() as db:
        user = create_user(db, email=email, password="SehatinPass123")
        raw_token, _ = create_session(db, user)
        db.commit()
    client.cookies.set("sehatin_session", raw_token)


def _assessment() -> dict:
    return {
        "stage": "toddler",
        "age_months": 36,
        "sex": "female",
        "weight_kg": 14.0,
        "height_cm": 95.0,
        "meal_frequency": 3,
        "meal_routine": "irregular",
        "fruit_vegetable_days": 0,
        "self_feeding_opportunity": False,
    }


def _valid_value(task: dict):
    kind = task.get("input_type")
    if kind == "count":
        target = task.get("target_value")
        return int(target) if isinstance(target, (int, float)) and not isinstance(target, bool) else 1
    if kind == "boolean":
        return bool(task.get("target_value"))
    options = task.get("options") or []
    target = task.get("target_value")
    allowed = [str(row.get("value")) for row in options if isinstance(row, dict) and row.get("value") is not None]
    if target is not None and str(target) in allowed:
        return str(target)
    return allowed[0]


def _payload(tasks: list[dict], *, checks: list[bool] | None = None) -> dict:
    return {
        "day_number": 1,
        "checklist_state": checks if checks is not None else [False] * len(tasks),
        "has_complaint": False,
        "task_results": {str(task["key"]): _valid_value(task) for task in tasks},
    }


def test_api_persists_stage6_metric_results_same_day_update_and_double_save(stage6_runtime):
    client = TestClient(app)
    _authenticate(client, stage6_runtime, "stage6@example.com")
    created = client.post(
        "/api/nutrition/program",
        json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 7},
    )
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    day = detail["days"][0]
    tasks = day["action_details"]["tasks"]
    payload = _payload(tasks)

    first = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=payload)
    assert first.status_code == 200, first.text
    body = first.json()
    assert len(body["metric_results"]) == len(tasks)
    assert body["task_results"]
    assert all(row["stage6_engine_version"] == STAGE6_RULE_VERSION for row in body["metric_results"])
    assert all("actual_result" in row and "status" in row and "input_type" in row for row in body["metric_results"])

    # Unknown client task IDs do not become history rows.
    payload_with_unknown = {**payload, "task_results": {**payload["task_results"], "not_a_real_task": 999}}
    duplicate = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=payload_with_unknown)
    assert duplicate.status_code == 200, duplicate.text
    assert len(duplicate.json()["metric_results"]) == len(tasks)
    assert "not_a_real_task" not in duplicate.json()["task_results"]

    # Duplicate logical saves preserve completed_at instead of manufacturing a
    # second completion event.
    first_completed = {row["task_id"]: row["completed_at"] for row in body["metric_results"] if row["completed_at"]}
    duplicate_completed = {row["task_id"]: row["completed_at"] for row in duplicate.json()["metric_results"] if row["completed_at"]}
    assert duplicate_completed == first_completed

    count_task = next((task for task in tasks if task.get("input_type") == "count"), None)
    if count_task:
        edited_payload = _payload(tasks)
        target = float(count_task["target_value"])
        edited_payload["task_results"][count_task["key"]] = max(0, target - 1)
        edited = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=edited_payload)
        assert edited.status_code == 200, edited.text
        edited_row = next(row for row in edited.json()["metric_results"] if row["task_id"] == count_task["key"])
        assert edited_row["actual_result"] == max(0, target - 1)
        assert edited_row["adherence"] <= 100

    reloaded = client.get(f"/api/nutrition/program/{program_id}/days/1")
    assert reloaded.status_code == 200
    assert len(reloaded.json()["day"]["metric_results"]) == len(tasks)


def test_api_rejects_invalid_result_without_overwriting_previous_save(stage6_runtime):
    client = TestClient(app)
    _authenticate(client, stage6_runtime, "invalid-stage6@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 7})
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}").json()["days"][0]
    tasks = day["action_details"]["tasks"]
    payload = _payload(tasks)
    saved = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=payload)
    assert saved.status_code == 200
    before = saved.json()["task_results"]

    count_task = next((task for task in tasks if task.get("input_type") == "count"), None)
    if not count_task:
        pytest.skip("Generated profile did not contain a COUNT task")
    invalid_payload = _payload(tasks)
    invalid_payload["task_results"][count_task["key"]] = -1
    invalid = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=invalid_payload)
    assert invalid.status_code == 422

    after = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]["task_results"]
    assert after == before


def test_daily_metric_history_keeps_multiple_days(stage6_runtime):
    client = TestClient(app)
    _authenticate(client, stage6_runtime, "history-stage6@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 7})
    program_id = created.json()["id"]
    day1 = client.get(f"/api/nutrition/program/{program_id}").json()["days"][0]
    tasks1 = day1["action_details"]["tasks"]
    first = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=_payload(tasks1))
    assert first.status_code == 200, first.text

    interval = timedelta(seconds=get_settings().effective_nutrition_day_interval_seconds)
    with stage6_runtime() as db:
        program = db.get(NutritionProgramModel, program_id)
        program.started_at = utcnow() - interval - timedelta(seconds=2)
        program.ends_at = program.started_at + interval * (program.duration_days - 1)
        db.commit()

    day2 = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day2.status_code == 200, day2.text
    tasks2 = day2.json()["day"]["action_details"]["tasks"]
    payload2 = _payload(tasks2)
    payload2["day_number"] = 2
    second = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=payload2)
    assert second.status_code == 200, second.text

    evaluation = client.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert evaluation.status_code == 200, evaluation.text
    history = evaluation.json()["details"]["daily_metric_history"]
    days = {row["day"] for row in history}
    assert {1, 2}.issubset(days)
    assert all("task_id" in row and "actual_result" in row and "input_type" in row for row in history)
