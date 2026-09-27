from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base, NutritionEvaluationModel, NutritionProgramDayModel, NutritionProgramGoalModel, NutritionProgramModel
from app.models.base import utcnow
from app.nutrition.daily_results import DailyResultValidationError, build_daily_task_result, responsive_feeding_adherence
from app.services.nutrition_program_service import STAGE8_RULE_VERSION, _stage8_decision, _stage8_metric_trend


def _responsive_task() -> dict:
    return {
        "key": "responsive",
        "metric_id": "responsive_feeding",
        "input_type": "boolean",
        "target_value": True,
        "unit": "hari",
    }


@pytest.mark.parametrize(("actual", "expected"), [(True, 100.0), (False, 0.0), ("Ya", 100.0), ("Tidak", 0.0), ("YES", 100.0), ("NO", 0.0)])
def test_stage8_responsive_feeding_mapping(actual, expected):
    assert responsive_feeding_adherence(actual) == expected
    row = build_daily_task_result(_responsive_task(), actual, action_completed=True, saved_at=utcnow()).as_dict()
    assert row["adherence"] == expected
    assert row["status"] == ("COMPLETED" if expected == 100 else "PARTIAL")


def test_stage8_responsive_feeding_invalid_string_is_not_silently_scored():
    with pytest.raises(DailyResultValidationError):
        build_daily_task_result(_responsive_task(), "kadang", action_completed=True, saved_at=utcnow())


def test_stage8_other_metric_regression_count_formula_unchanged():
    task = {"key": "meal", "metric_id": "meal_frequency", "input_type": "count", "target_value": 3, "unit": "meals"}
    row = build_daily_task_result(task, 2, action_completed=True, saved_at=utcnow()).as_dict()
    assert row["actual_result"] == 2
    assert row["adherence"] == 66.67


def test_stage8_trend_requires_more_than_one_observation():
    one = _stage8_metric_trend([{"metric_id": "meal_routine", "adherence": 70}], "meal_routine")
    assert one["status"] == "INSUFFICIENT_DATA"
    many = _stage8_metric_trend([
        {"metric_id": "meal_routine", "adherence": 40},
        {"metric_id": "meal_routine", "adherence": 60},
        {"metric_id": "meal_routine", "adherence": 90},
    ], "meal_routine")
    assert many["direction"] == "IMPROVING"
    assert many["recent"] > many["early"]


@pytest.mark.parametrize(
    ("block_complete", "goal_status", "adherence", "trend", "safety", "expected"),
    [
        (False, "NOT_MET", 20, "DECLINING", {"active": False}, "CONTINUE"),
        (True, "MET", 90, "STABLE", {"active": False}, "COMPLETE"),
        (True, "PARTIALLY_MET", 70, "STABLE", {"active": False}, "EXTEND"),
        (True, "NOT_MET", 30, "DECLINING", {"active": False}, "REFRAME"),
        (True, "NOT_MET", 60, "IMPROVING", {"active": False}, "CONTINUE"),
        (True, "MET", 100, "IMPROVING", {"active": True, "decision": "REFER"}, "REFER"),
    ],
)
def test_stage8_decision_contract(block_complete, goal_status, adherence, trend, safety, expected):
    assert _stage8_decision(
        block_complete=block_complete,
        goal_status=goal_status,
        behavioral_adherence=adherence,
        trend_direction=trend,
        safety=safety,
    ) == expected


@pytest.fixture()
def stage8_db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'stage8.db').as_posix()}", connect_args={"check_same_thread": False})
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


def _assessment() -> dict:
    return {
        "stage": "toddler",
        "age_months": 36,
        "sex": "female",
        "weight_kg": 14.0,
        "height_cm": 95.0,
        "meal_routine": "regular",
        "pressure_to_eat": True,
        "responsive_feeding": "rarely",
    }


def _prepare_completed_responsive_block(factory, program_id: str) -> None:
    now = utcnow()
    with factory() as db:
        program = db.get(NutritionProgramModel, program_id)
        program.status = "COMPLETED"
        program.completed_at = now
        program.ends_at = now - timedelta(seconds=1)
        goal = db.scalar(select(NutritionProgramGoalModel).where(NutritionProgramGoalModel.program_id == program_id).order_by(NutritionProgramGoalModel.priority))
        goal.goal_key = "responsive_feeding"
        goal.title = "Responsive feeding"
        goal.target = 10
        goal.unit = "successful target days"
        days = list(db.scalars(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program_id).order_by(NutritionProgramDayModel.day_number)))
        for index, day in enumerate(days, start=1):
            actual = index <= 10
            # Deliberately store the historical inverse mapping to prove Stage 8
            # corrects evaluation without rewriting the daily record.
            stored_adherence = 0.0 if actual else 100.0
            task = {
                "key": f"responsive_d{index}",
                "metric": "responsive_feeding",
                "metric_id": "responsive_feeding",
                "input_type": "boolean",
                "target_value": 1.0,
                "unit": "hari",
                "target_label": "Responsive feeding diterapkan hari ini.",
            }
            day.checklist = ["Responsive feeding"]
            day.checklist_state = [True]
            day.completed = True
            day.completed_at = now
            day.action_details = {
                "tasks": [task],
                "task_results": {task["key"]: actual},
                "last_saved_at": now.isoformat(),
                "last_saved_task_adherence": {task["key"]: stored_adherence},
                "metric_results": [{
                    "task_id": task["key"],
                    "metric_id": "responsive_feeding",
                    "target": 1.0,
                    "target_value": 1.0,
                    "actual_result": actual,
                    "actual": actual,
                    "unit": "hari",
                    "input_type": "boolean",
                    "status": "PARTIAL" if actual else "COMPLETED",
                    "adherence": stored_adherence,
                    "completed_at": now.isoformat(),
                    "action_completed": True,
                }],
            }
        db.commit()


def test_stage8_day14_review_separates_program_goal_and_is_idempotent(stage8_db):
    client = TestClient(app, client=("stage8-final", 50501))
    _register(client, "stage8-final@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    _prepare_completed_responsive_block(stage8_db, program_id)

    first = client.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert first.status_code == 200, first.text
    details = first.json()["details"]
    review = details["block_review"]
    assert review["block_completed"] is True
    assert review["program_progress"] == {"completed_days": 14, "planned_days": 14, "percent": 100.0}
    assert review["goal_progress"]["actual"] == 10.0
    assert review["goal_progress"]["target"] == 10.0
    assert review["goal_status"] == "MET"
    assert review["decision"] == "COMPLETE"
    metric = next(item for item in review["metrics"] if item["metric"] == "responsive_feeding")
    assert metric["actual"] == 10
    assert metric["adherence"] == 71.4
    corrected_rows = [row for row in details["daily_metric_history"] if row["metric"] == "responsive_feeding"]
    assert corrected_rows[0]["actual_result"] is True and corrected_rows[0]["adherence"] == 100.0
    assert corrected_rows[-1]["actual_result"] is False and corrected_rows[-1]["adherence"] == 0.0

    # Refresh must return the same immutable Stage 8 record, not create another.
    second = client.get(f"/api/nutrition/program/{program_id}/evaluation")
    assert second.status_code == 200
    assert second.json()["details"]["block_review"]["generated_at"] == review["generated_at"]
    block = client.get(f"/api/nutrition/program/{program_id}/block-review")
    assert block.status_code == 200, block.text
    assert block.json()["decision"] == "COMPLETE"
    assert block.json()["program_progress"]["percent"] == 100.0

    with stage8_db() as db:
        count = db.scalar(select(func.count(NutritionEvaluationModel.id)).where(NutritionEvaluationModel.program_id == program_id))
        assert count == 1
        program = db.get(NutritionProgramModel, program_id)
        history = list((program.program_config or {}).get("block_review_history") or [])
        assert len(history) == 1
        assert history[0]["rule_version"] == STAGE8_RULE_VERSION
        day1 = db.scalar(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program_id, NutritionProgramDayModel.day_number == 1))
        # Original historical record is immutable even though evaluation fixes the mapping.
        assert day1.action_details["metric_results"][0]["adherence"] == 0.0


def test_stage8_review_wording_is_behavioral_not_diagnostic(stage8_db):
    client = TestClient(app, client=("stage8-wording", 50502))
    _register(client, "stage8-wording@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    program_id = created.json()["id"]
    _prepare_completed_responsive_block(stage8_db, program_id)
    review = client.get(f"/api/nutrition/program/{program_id}/block-review").json()
    text = " ".join([
        str(review.get("what_improved") or ""),
        str(review.get("what_remains") or ""),
        str(review.get("next_focus") or ""),
        str(review.get("evaluation_framework") or ""),
    ]).lower()
    for forbidden in ("anak sehat", "anak tidak sehat", "status gizi baik", "status gizi buruk", "diagnosis penyakit"):
        assert forbidden not in text
