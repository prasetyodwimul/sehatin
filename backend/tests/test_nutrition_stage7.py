from __future__ import annotations

from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Base, NutritionProgramDayModel, NutritionProgramModel
from app.models.base import utcnow
from app.nutrition.adaptive_program import RULE_VERSION, calculate_indicators, decide_adaptation, plan_adjustments, safety_guard


DAY_INTERVAL_SECONDS = get_settings().effective_nutrition_day_interval_seconds


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
        "history_days_available": 3,
        "recent_adherence_average": 80.0,
    }
    base.update(overrides)
    return base


def test_stage7_no_prior_history_uses_safe_continue_default():
    indicators = calculate_indicators(
        {"acceptance": "liked", "portion": "partial", "parent_difficulty": "easy", "child_condition": "healthy"},
        [],
        goal_metric="meal_routine",
        task_adherence={},
        recent_adherence_history=[],
    )
    decision = decide_adaptation(
        safety=_clear(), indicators=indicators, current_log={"acceptance": "liked"}, recent_logs=[], day_number=1, block_days=14
    )
    assert indicators["history_days_available"] == 0
    assert decision["decision"] == "CONTINUE"
    assert decision["reason_code"] == "INSUFFICIENT_HISTORY"


@pytest.mark.parametrize("days", [1, 2, 3, 7])
def test_stage7_history_windows_are_supported_without_assuming_missing_days(days: int):
    logs = [{"acceptance": "neutral", "portion": "partial", "parent_difficulty": "easy"} for _ in range(days)]
    indicators = calculate_indicators(
        {"acceptance": "liked", "portion": "partial", "parent_difficulty": "easy"},
        logs,
        goal_metric="meal_routine",
        task_adherence={"primary": 100},
        recent_adherence_history=[50.0 + index for index in range(days)],
    )
    assert indicators["history_days_available"] == min(days, 7)
    assert indicators["current_adherence"] == 100.0
    assert indicators["recent_adherence_average"] is not None


def test_stage7_safety_overrides_otherwise_good_performance():
    safety = safety_guard(
        {"child_condition": "healthy", "reaction": "detected", "reaction_notes": "anak sulit bernapas setelah makan"}, {}
    )
    decision = decide_adaptation(
        safety=safety,
        indicators=_indicators(trend_direction="IMPROVING", acceptance_trend=1.0, burden_index=0.0, recent_adherence_average=100.0),
        current_log={"acceptance": "liked"},
        recent_logs=[{"acceptance": "neutral"}, {"acceptance": "liked"}],
        day_number=5,
    )
    assert decision["decision"] == "REFER"
    assert decision["reason_code"] == "SAFETY_RED_FLAG"
    assert decision["decision"] != "ADVANCE"
    assert decision["explanation"]["what_next"]


def test_stage7_high_burden_plus_low_adherence_eases_but_single_hard_day_does_not_overreact():
    ease = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(burden_index=1.0, recent_adherence_average=40.0),
        current_log={"acceptance": "neutral", "parent_difficulty": "difficult"},
        recent_logs=[{"acceptance": "neutral", "parent_difficulty": "difficult"}],
        day_number=4,
    )
    assert ease["decision"] == "EASE"
    assert plan_adjustments("EASE", {})["difficulty"] == "LOWER"

    one_day = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(burden_index=1.0, recent_adherence_average=None, history_days_available=0, trend_direction="INSUFFICIENT_DATA"),
        current_log={"acceptance": "neutral", "parent_difficulty": "difficult"},
        recent_logs=[],
        day_number=1,
    )
    assert one_day["decision"] == "CONTINUE"


def test_stage7_repeat_keeps_goal_and_advance_has_one_challenge_guardrail():
    repeat = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(),
        current_log={"acceptance": "refused", "new_food": True},
        recent_logs=[],
        day_number=3,
    )
    assert repeat["decision"] == "REPEAT"
    assert plan_adjustments("REPEAT", {})["new_challenges"] == []

    advance = decide_adaptation(
        safety=_clear(),
        indicators=_indicators(trend_direction="IMPROVING", acceptance_trend=0.9, recent_adherence_average=90.0, history_days_available=3),
        current_log={"acceptance": "liked", "new_food": False},
        recent_logs=[{"acceptance": "neutral"}, {"acceptance": "liked"}],
        day_number=5,
    )
    assert advance["decision"] == "ADVANCE"
    adjustment = plan_adjustments("ADVANCE", {})
    assert adjustment["max_new_challenges"] == 1
    assert len(adjustment["new_challenges"]) == 1


def test_stage7_rule_version_is_snapshotted_and_old_decision_does_not_mutate():
    v1 = deepcopy(RULE_VERSION)
    v1.update({"id": "adaptive-test-v1", "version": "1.0"})
    v2 = deepcopy(RULE_VERSION)
    v2.update({"id": "adaptive-test-v2", "version": "2.0"})
    first = decide_adaptation(
        safety=_clear(), indicators=_indicators(), current_log={"acceptance": "neutral"}, recent_logs=[], day_number=2, rule_version=v1
    )
    second = decide_adaptation(
        safety=_clear(), indicators=_indicators(), current_log={"acceptance": "neutral"}, recent_logs=[], day_number=3, rule_version=v2
    )
    assert first["rule_version"]["id"] == "adaptive-test-v1"
    assert second["rule_version"]["id"] == "adaptive-test-v2"
    assert first["rule_version"]["id"] == "adaptive-test-v1"


def test_stage7_same_input_is_deterministic_and_explainable():
    kwargs = dict(
        safety=_clear(),
        indicators=_indicators(trend_direction="IMPROVING", acceptance_trend=0.9, recent_adherence_average=90.0),
        current_log={"acceptance": "liked"},
        recent_logs=[{"acceptance": "neutral"}, {"acceptance": "liked"}],
        day_number=5,
        block_days=14,
    )
    first = decide_adaptation(**kwargs)
    second = decide_adaptation(**kwargs)
    assert first == second
    for key in ("decision", "reason_code", "reason_text", "evidence_refs", "indicator_snapshot", "rule_version", "explanation"):
        assert key in first
    assert first["explanation"]["what_changed"]
    assert first["explanation"]["why"]
    assert first["explanation"]["what_next"]


@pytest.fixture()
def stage7_db(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'stage7.db').as_posix()}", connect_args={"check_same_thread": False})
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
    return {"stage": "toddler", "age_months": 36, "sex": "female", "weight_kg": 14.0, "height_cm": 95.0, "meal_routine": "irregular"}


def _complete_payload(day: dict, **overrides) -> dict:
    payload = {
        "day_number": day["day_number"],
        "checklist_state": [True] * len(day["checklist"]),
        "has_complaint": False,
        "portion": "partial",
        "acceptance": "liked",
        "new_food": False,
        "reaction": "none",
        "child_condition": "healthy",
        "caregiver_adherence": "yes",
        "parent_difficulty": "easy",
    }
    payload.update(overrides)
    return payload


def test_stage7_api_persists_auditable_decision_and_structured_next_plan(stage7_db):
    client = TestClient(app, client=("stage7-history", 50401))
    _register(client, "stage7-history@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    saved = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=_complete_payload(day))
    assert saved.status_code == 200, saved.text
    body = saved.json()
    adaptation = body["adaptation"]
    assert adaptation["reason_code"]
    assert adaptation["rule_version"]["id"] == RULE_VERSION["id"]
    assert adaptation["explanation"]["what_next"]
    plan = body["next_day_plan"]
    assert plan["plan_id"]
    assert plan["primary_target_id"]
    assert isinstance(plan["actions"], list)
    assert isinstance(plan["new_challenges"], list)

    with stage7_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        history = list((program.program_config or {}).get("decision_history") or [])
        assert len(history) == 1
        row = history[0]
        for key in ("program_id", "day_id", "decision", "reason", "indicator_snapshot", "safety_state", "rule_version", "previous_plan_id", "next_plan_id", "created_at"):
            assert key in row
        assert row["program_id"] == program_id
        assert row["rule_version"]["id"] == RULE_VERSION["id"]


def test_stage7_pause_happens_even_before_checklist_completion(stage7_db):
    client = TestClient(app, client=("stage7-pause", 50402))
    _register(client, "stage7-pause@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    program_id = created.json()["id"]
    day = client.get(f"/api/nutrition/program/{program_id}/days/1").json()["day"]
    payload = _complete_payload(day, child_condition="fever")
    payload["checklist_state"] = [False] * len(day["checklist"])
    saved = client.post(f"/api/nutrition/program/{program_id}/daily-log", json=payload)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert body["day_completed"] is False
    assert body["adaptation"]["decision"] == "PAUSE"
    assert body["program_status"] == "PAUSED"

    with stage7_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        history = list((program.program_config or {}).get("decision_history") or [])
        assert len(history) == 1
        assert history[0]["decision"]["decision"] == "PAUSE"


def test_stage7_primary_metric_remains_stable_after_advance_plan():
    from app.services.nutrition_program_service import _next_primary_metric

    assert _next_primary_metric("mpasi", "meal_frequency", "ADVANCE") == "meal_frequency"
    assert _next_primary_metric("toddler", "meal_routine", "ADVANCE") == "meal_routine"


def test_stage7_missing_day_records_safe_continue_without_marking_success_or_failure(stage7_db):
    client = TestClient(app, client=("stage7-missed", 50404))
    _register(client, "stage7-missed@example.com")
    created = client.post("/api/nutrition/program", json={"assessment": _assessment(), "consent_to_save": True, "duration_days": 14})
    assert created.status_code == 201, created.text
    program_id = created.json()["id"]

    skipped = client.post(f"/api/nutrition/program/{program_id}/skip-day", json={"confirm": True})
    assert skipped.status_code == 200, skipped.text

    with stage7_db() as db:
        program = db.get(NutritionProgramModel, program_id)
        history = list((program.program_config or {}).get("decision_history") or [])
        assert len(history) == 1
        decision = history[0]["decision"]
        assert decision["decision"] == "CONTINUE"
        assert decision["reason_code"] == "MISSING_DAY_NO_RESULT"
        day1 = db.scalar(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program_id, NutritionProgramDayModel.day_number == 1))
        assert day1.completed is False
        assert (day1.action_details or {}).get("manual_skip") is True


def test_stage7_user_facing_decisions_do_not_make_diagnosis_claims():
    cases = [
        decide_adaptation(safety=_clear(), indicators=_indicators(), current_log={"acceptance": "neutral"}, recent_logs=[], day_number=2),
        decide_adaptation(safety=_clear(), indicators=_indicators(), current_log={"acceptance": "refused", "new_food": True}, recent_logs=[], day_number=2),
        decide_adaptation(
            safety=_clear(),
            indicators=_indicators(trend_direction="IMPROVING", acceptance_trend=0.9, recent_adherence_average=90.0),
            current_log={"acceptance": "liked"},
            recent_logs=[{"acceptance": "neutral"}, {"acceptance": "liked"}],
            day_number=4,
        ),
    ]
    forbidden = ("diagnosis", "status gizi", "anak sehat", "anak tidak sehat", "penyakit")
    for item in cases:
        text = " ".join([
            str(item.get("reason_text") or ""),
            str(item.get("user_facing_reason") or ""),
            str((item.get("explanation") or {}).get("what_changed") or ""),
            str((item.get("explanation") or {}).get("what_next") or ""),
        ]).lower()
        assert not any(term in text for term in forbidden)
