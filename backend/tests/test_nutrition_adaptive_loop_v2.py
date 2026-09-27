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


DAY_INTERVAL_SECONDS = get_settings().effective_nutrition_day_interval_seconds

def _program_interval(multiplier: float = 1.0) -> timedelta:
    return timedelta(seconds=DAY_INTERVAL_SECONDS * multiplier)

from app.nutrition.adaptive_program import (
    RULE_VERSION,
    calculate_indicators,
    decide_adaptation,
    safety_guard,
)


def _clear() -> dict:
    return {"level": "CLEAR", "blocked": False, "decision": None, "reason": "clear", "user_facing_reason": "clear"}


def _indicators(**overrides) -> dict:
    base = {
        "acceptance_score": 2.5,
        "portion_score": 67.0,
        "trend_window_days": 3,
        "acceptance_trend": 0.5,
        "trend_direction": "STABLE",
        "goal_progress_score": 50.0,
        "goal_metric": "meal_routine",
        "burden_index": 0.0,
        "safety_index": 0.0,
    }
    base.update(overrides)
    return base


def test_adaptive_decision_stable_child_continues():
    result = decide_adaptation(
        safety=_clear(), indicators=_indicators(), current_log={"acceptance": "neutral"}, recent_logs=[], day_number=2
    )
    assert result["decision"] == "CONTINUE"
    assert result["rule_version_id"] == RULE_VERSION["id"]
    assert result["user_facing_reason"]


def test_adaptive_decision_new_food_rejected_repeats_before_new_challenge():
    result = decide_adaptation(
        safety=_clear(), indicators=_indicators(), current_log={"acceptance": "refused", "new_food": True}, recent_logs=[], day_number=2
    )
    assert result["decision"] == "REPEAT"
    assert "coba lagi" in result["user_facing_reason"].lower()


def test_adaptive_decision_repeated_refusal_eases():
    result = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(),
        current_log={"acceptance": "refused", "new_food": False},
        recent_logs=[{"acceptance": "refused"}],
        day_number=3,
    )
    assert result["decision"] == "EASE"


def test_adaptive_decision_improving_low_burden_advances():
    result = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(trend_direction="IMPROVING", acceptance_trend=0.9, burden_index=0.0),
        current_log={"acceptance": "liked"},
        recent_logs=[{"acceptance": "neutral"}, {"acceptance": "liked"}],
        day_number=4,
    )
    assert result["decision"] == "ADVANCE"


def test_sick_condition_pauses_goal_optimization():
    safety = safety_guard({"child_condition": "fever", "reaction": "none"}, {})
    result = decide_adaptation(safety=safety, indicators=_indicators(safety_index=1.0), current_log={"child_condition": "fever"}, recent_logs=[], day_number=2)
    assert safety["blocked"] is True
    assert result["decision"] == "PAUSE"


def test_detected_reaction_without_red_flag_is_observed_not_referred():
    safety = safety_guard({"child_condition": "healthy", "reaction": "detected", "reaction_notes": "muncul ruam ringan"}, {})
    result = decide_adaptation(safety=safety, indicators=_indicators(safety_index=0.0), current_log={"reaction": "detected"}, recent_logs=[], day_number=2)
    assert safety["level"] == "OBSERVE"
    assert safety["blocked"] is False
    assert result["decision"] == "CONTINUE"


def test_explicit_red_flag_text_refers_and_blocks_automatic_adaptation():
    safety = safety_guard({"child_condition": "healthy", "reaction": "detected", "reaction_notes": "anak sulit bernapas setelah makan"}, {})
    result = decide_adaptation(safety=safety, indicators=_indicators(safety_index=1.0), current_log={"reaction": "detected"}, recent_logs=[], day_number=2)
    assert safety["level"] == "SEVERE"
    assert safety["emergency"] is True
    assert safety["red_flags"][0]["code"] == "BREATHING_DIFFICULTY"
    assert "rumah sakit" in safety["recommended_action"].lower()
    assert result["decision"] == "REFER"


def test_prolonged_stable_low_acceptance_does_not_trigger_early_block_review():
    result = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(trend_direction="STABLE", acceptance_trend=0.5, burden_index=0.0),
        current_log={"acceptance": "neutral"},
        recent_logs=[{"acceptance": "neutral"}] * 6,
        day_number=7,
        block_days=14,
    )
    assert result["decision"] == "CONTINUE"
    assert result["reason_code"] == "STABLE_CONTINUATION"


def test_block_review_is_handoff_at_end_of_block_only():
    result = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(trend_direction="STABLE", acceptance_trend=0.5, burden_index=0.0),
        current_log={"acceptance": "neutral"},
        recent_logs=[{"acceptance": "neutral"}] * 7,
        day_number=14,
        block_days=14,
    )
    assert result["decision"] == "BLOCK_REVIEW"
    assert result["reason_code"] == "BLOCK_END_REACHED"
    assert result["next_plan_strategy"] == "BLOCK_REVIEW"


def test_indicator_calculator_uses_daily_log_and_recent_trend_deterministically():
    result = calculate_indicators(
        {"acceptance": "liked", "portion": "partial", "parent_difficulty": "easy", "child_condition": "healthy", "reaction": "none"},
        [{"acceptance": "refused"}, {"acceptance": "neutral"}],
        goal_metric="meal_routine",
        task_adherence={"a": 100, "b": 50},
    )
    assert result["acceptance_score"] == 5.0
    assert result["portion_score"] == 67.0
    assert result["trend_direction"] == "IMPROVING"
    assert result["goal_progress_score"] == 75.0
    assert result["technical_labels"] == {"acceptance_score": "SPH", "portion_score": "SPoH", "goal_progress_score": "SKG"}


@pytest.fixture()
def adaptive_db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'adaptive.db').as_posix()}", connect_args={"check_same_thread": False})
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


def _register(client: TestClient, email: str):
    response = client.post("/api/auth/register", json={"email": email, "password": "SehatinPass123"})
    assert response.status_code == 201, response.text


def _assessment() -> dict:
    return {"stage": "toddler", "age_months": 36, "sex": "female", "weight_kg": 14.0, "height_cm": 95.0, "meal_routine": "irregular"}


def test_child_program_generates_day_two_only_after_day_one_log(adaptive_db):
    client = TestClient(app, client=("adaptive-plan", 50201))
    _register(client, "adaptive-plan@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    detail = client.get(f"/api/nutrition/program/{program_id}").json()
    assert detail["adaptive_mode"] is True
    assert detail["days"][0]["recommended_action"]
    assert detail["days"][1]["recommended_action"] == ""
    assert detail["days"][1]["checklist"] == []
    assert detail["rule_version"]["review_status"] == "NEEDS_CLINICAL_VALIDATION"

    day1 = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    saved = client.post(
        f"/api/nutrition/program/{program_id}/daily-log",
        json={
            "day_number": 1,
            "checklist_state": [True] * len(day1["checklist"]),
            "has_complaint": False,
            "portion": "partial",
            "acceptance": "liked",
            "new_food": False,
            "reaction": "none",
            "child_condition": "healthy",
            "caregiver_adherence": "yes",
            "parent_difficulty": "easy",
        },
    )
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["day_completed"] is True
    assert body["adaptation"]["decision"] in {"CONTINUE", "ADVANCE"}
    assert body["adaptation"]["rule_version_id"] == RULE_VERSION["id"]
    assert body["daily_summary"]["tomorrow_preview"]
    assert body["next_day_plan"]["day_number"] == 2

    with adaptive_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        program.started_at = utcnow() - _program_interval() - timedelta(seconds=2)
        program.ends_at = program.started_at + _program_interval(13)
        db.commit()

    day2 = client.get(f"/api/nutrition/program/{program_id}/days/2")
    assert day2.status_code == 200
    row = day2.json()["day"]
    assert row["status"] == "AVAILABLE"
    assert row["recommended_action"]
    assert row["completed"] is False
    assert row["completed_at"] is None
    assert row["checklist_state"] == [False] * len(row["checklist"])
    assert row["action_details"]["generated_from_day"] == 1
    assert row["action_details"]["why_this_plan"]


def test_active_rule_endpoint_and_program_goal_progress_are_separate(adaptive_db):
    client = TestClient(app, client=("adaptive-rules", 50202))
    _register(client, "adaptive-rules@example.com")
    rules = client.get("/api/nutrition/rules/active")
    assert rules.status_code == 200
    assert rules.json()["id"] == RULE_VERSION["id"]
    assert rules.json()["review_status"] == "NEEDS_CLINICAL_VALIDATION"

    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    program_id = created.json()["id"]
    progress = client.get(f"/api/nutrition/program/{program_id}/progress")
    assert progress.status_code == 200
    body = progress.json()
    assert body["progress_percent"] == 0.0
    assert body["goal_progress_percent"] == 0.0
    assert body["total_days"] == 14


def test_advance_guardrail_blocks_consecutive_or_immediate_post_ease_advance():
    improving = _indicators(trend_direction="IMPROVING", acceptance_trend=0.9, burden_index=0.0)
    after_ease = decide_adaptation(safety=_clear(), indicators=improving, current_log={"acceptance": "liked"}, recent_logs=[], day_number=5, previous_decision="EASE")
    consecutive = decide_adaptation(safety=_clear(), indicators=improving, current_log={"acceptance": "liked"}, recent_logs=[], day_number=5, previous_decision="ADVANCE")
    assert after_ease["decision"] == "CONTINUE"
    assert consecutive["decision"] == "CONTINUE"
    assert "guardrail" in after_ease["reason"].lower()


def test_final_daily_progress_series_compares_early_and_recent_saved_results(adaptive_db):
    from app.services.nutrition_program_service import _final_daily_progress_series

    owner = TestClient(app, client=("adaptive-trend-owner", 50208))
    _register(owner, "adaptive-trend-owner@example.com")
    created = owner.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    details = {
        "daily_metric_history": [
            {"day": 1, "adherence": 50},
            {"day": 1, "adherence": 70},
            {"day": 2, "adherence": 70},
            {"day": 3, "adherence": 80},
            {"day": 12, "adherence": 80},
            {"day": 13, "adherence": 90},
            {"day": 14, "adherence": 100},
        ]
    }
    history = [{"day": 2, "decision": {"decision": "CONTINUE"}}]
    with adaptive_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        series, change = _final_daily_progress_series(db, program, details, history)

    assert len(series) == 14
    assert series[0]["adherence_percent"] == 60.0
    assert series[1]["decision"] == "CONTINUE"
    assert series[13]["adherence_percent"] == 100.0
    assert change["early_average"] == 70.0
    assert change["recent_average"] == 90.0
    assert change["delta_points"] == 20.0
    assert change["direction"] == "IMPROVING"


def test_adaptive_state_endpoints_keep_server_side_program_ownership(adaptive_db):
    owner = TestClient(app, client=("adaptive-owner", 50203))
    other = TestClient(app, client=("adaptive-other", 50204))
    _register(owner, "adaptive-owner@example.com")
    _register(other, "adaptive-other@example.com")
    created = owner.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    program_id = created.json()["id"]
    assert other.get(f"/api/nutrition/program/{program_id}/block-review").status_code == 404
    assert other.post(f"/api/nutrition/program/{program_id}/pause", json={"confirm": True}).status_code == 404
    assert other.post(f"/api/nutrition/program/{program_id}/skip-day", json={"confirm": True}).status_code == 404


def test_final_program_result_separates_block_completion_from_goal_and_keeps_audit_history(adaptive_db):
    from sqlalchemy import select
    from app.models import NutritionProgramDayModel

    owner = TestClient(app, client=("adaptive-result-owner", 50205))
    other = TestClient(app, client=("adaptive-result-other", 50206))
    _register(owner, "adaptive-result-owner@example.com")
    _register(other, "adaptive-result-other@example.com")
    created = owner.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    with adaptive_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        days = list(db.scalars(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program_id)))
        now = utcnow()
        for day in days:
            day.completed = True
            day.completed_at = now
        cfg = dict(program.program_config or {})
        cfg["decision_history"] = [{
            "day": 2,
            "indicators": {"acceptance_trend": 0.5, "trend_direction": "STABLE"},
            "decision": {"decision": "CONTINUE", "reason": "stable", "user_facing_reason": "Rencana dipertahankan.", "rule_version_id": RULE_VERSION["id"]},
            "safety": {"before_adaptation": {"blocked": False}, "after_plan_generation": {"blocked": False}},
            "next_plan": {"day_number": 3},
        }]
        program.program_config = cfg
        program.status = "COMPLETED"
        program.completed_at = now
        program.ends_at = now
        db.commit()

    response = owner.get(f"/api/nutrition/program/{program_id}/result")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["program_completion_percent"] == 100.0
    assert body["program_numbers"]["completed_days"] == 14
    assert body["program_numbers"]["adaptation_decisions"] == 1
    assert body["adaptation_history"][0]["decision"] == "CONTINUE"
    # Completing the 14-day block must not manufacture goal success.
    assert body["goal_status"] in {"PARTIALLY_MET", "NOT_MET"}
    assert body["goal_achievement_percent"] < 100.0
    assert body["next_step"]["decision"] in {"EXTEND", "REFRAME"}

    assert other.get(f"/api/nutrition/program/{program_id}/result").status_code == 404
