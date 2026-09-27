from __future__ import annotations

from app.nutrition.profile_baseline import normalize_baseline, target_candidate
from app.nutrition.program_evidence import (
    STAGE5_RULE_VERSION,
    evaluate_evidence_rules,
    generate_personalized_daily_todos,
)
from app.schemas.nutrition import NutritionRequest
from app.services.nutrition_service import generate_nutrition_recommendation


def _toddler(**extra) -> NutritionRequest:
    payload = dict(
        stage="toddler",
        age_months=36,
        sex="female",
        weight_kg=14.0,
        height_cm=95.0,
        meal_frequency=3,
    )
    payload.update(extra)
    return NutritionRequest(**payload)


def _mpasi(**extra) -> NutritionRequest:
    payload = dict(
        stage="mpasi",
        age_months=8,
        feeding_mode="breastmilk",
        sex="female",
        weight_kg=8.0,
        height_cm=68.0,
        meal_frequency=1,
    )
    payload.update(extra)
    return NutritionRequest(**payload)


def _stage5(req: NutritionRequest, primary_metric: str, supports: list[str] | None = None):
    baseline = normalize_baseline(req)
    primary_gap = {"id": f"gap_{primary_metric}", "metric": primary_metric}
    support_gaps = [{"id": f"gap_{metric}", "metric": metric} for metric in (supports or [])]
    stage4 = evaluate_evidence_rules(
        category=req.stage,
        profile=req.model_dump(mode="json"),
        baseline=baseline,
        primary_gap=primary_gap,
        support_gaps=support_gaps,
    )
    primary_target = target_candidate(req, baseline, primary_metric, 1)
    support_targets = [target_candidate(req, baseline, metric, i + 2) for i, metric in enumerate(supports or [])]
    return generate_personalized_daily_todos(
        stage=req.stage,
        profile=req.model_dump(mode="json"),
        day_number=1,
        baseline=baseline,
        primary_gap=primary_gap,
        primary_target=primary_target,
        support_targets=support_targets,
        evidence_rule_evaluation=stage4,
    )


def test_meal_routine_primary_gap_generates_meal_routine_primary_action():
    result = _stage5(
        _toddler(meal_routine="irregular", fruit_vegetable_days=0, self_feeding_opportunity=False),
        "meal_routine",
        ["vegetable_fruit_exposure", "self_feeding"],
    )
    assert result["status"] == "READY"
    assert result["tasks"][0]["metric_id"] == "meal_routine"
    assert result["tasks"][0]["priority"] == 1


def test_protein_primary_gap_generates_protein_action():
    result = _stage5(_toddler(animal_source_food_days=0), "protein_presence")
    task = result["tasks"][0]
    assert task["metric_id"] == "protein_presence"
    assert "protein" in task["action_text"].lower()


def test_food_variety_primary_gap_generates_exposure_action():
    result = _stage5(_toddler(fruit_vegetable_days=0), "vegetable_fruit_exposure")
    task = result["tasks"][0]
    assert task["metric_id"] == "vegetable_fruit_exposure"
    assert "sayur" in task["action_text"].lower() or "buah" in task["action_text"].lower()


def test_same_input_generates_same_daily_todo():
    req = _mpasi(recent_food_groups=["grains"], animal_source_food_days=0)
    first = _stage5(req, "meal_frequency", ["dietary_diversity", "animal_source_food"])
    second = _stage5(req, "meal_frequency", ["dietary_diversity", "animal_source_food"])
    assert first == second


def test_primary_is_priority_one_and_supports_follow_in_order():
    result = _stage5(
        _toddler(meal_routine="irregular", fruit_vegetable_days=0, self_feeding_opportunity=False),
        "meal_routine",
        ["vegetable_fruit_exposure", "self_feeding"],
    )
    assert [task["priority"] for task in result["tasks"]] == [1, 2, 3]
    assert result["tasks"][0]["metric"] == "meal_routine"


def test_default_meaningful_case_produces_three_to_five_actions():
    result = _stage5(
        _mpasi(recent_food_groups=["grains"], animal_source_food_days=0, fruit_vegetable_days=0),
        "meal_frequency",
        ["dietary_diversity", "animal_source_food", "fruit_vegetable"],
    )
    assert 3 <= len(result["tasks"]) <= 5


def test_count_has_numeric_target_and_unit_from_matching_rule():
    result = _stage5(_mpasi(), "meal_frequency")
    task = result["tasks"][0]
    assert task["input_type"] == "count"
    assert isinstance(task["target_value"], (int, float))
    assert task["unit"] == "meals_per_day"
    assert task["target_value"] == 2


def test_boolean_is_not_treated_as_count():
    result = _stage5(_toddler(pressure_to_eat=True), "responsive_feeding")
    task = result["tasks"][0]
    assert task["input_type"] == "boolean"
    assert isinstance(task["target_value"], (bool, int, float))
    assert task["input_type"] != "count"


def test_choice_has_allowed_options():
    result = _stage5(_toddler(food_rejection="frequent"), "food_response")
    task = result["tasks"][0]
    assert task["input_type"] == "choice"
    assert {row["value"] for row in task["options"]} >= {"accepted", "partial", "refused"}


def test_every_evidence_based_action_has_evidence_rule_id_and_trace():
    result = _stage5(
        _mpasi(recent_food_groups=["grains"], animal_source_food_days=0),
        "meal_frequency",
        ["dietary_diversity", "animal_source_food"],
    )
    for task in result["tasks"]:
        assert task["evidence_rule_id"]
        assert task["evidence_rule"]["source_name"]
        assert task["evidence_rule"]["source_url"]
        assert task["personalization_trace"]["evidence_rule_id"] == task["evidence_rule_id"]


def test_no_stage4_rule_does_not_fabricate_target():
    result = _stage5(_toddler(mealtime_duration_minutes=90), "mealtime_duration")
    assert result["status"] == "NO_MATCHING_RULE"
    assert result["tasks"] == []
    assert "Target" in result["message"]


def test_stage5_does_not_calculate_adherence():
    result = _stage5(_mpasi(), "meal_frequency")
    task = result["tasks"][0]
    assert "adherence" not in task
    assert task["result"] is None
    assert task["current_result"] is None


def test_stage5_initial_status_is_not_started():
    result = _stage5(_mpasi(), "meal_frequency")
    assert all(task["status"] == "NOT_STARTED" for task in result["tasks"])
    assert all(task["stage5_engine_version"] == STAGE5_RULE_VERSION for task in result["tasks"])


def test_stage4_qualitative_target_is_explicitly_product_operationalized():
    result = _stage5(_toddler(meal_routine="irregular"), "meal_routine")
    task = result["tasks"][0]
    assert task["stage4_target"] == "regular"
    assert task["target_origin"] == "PRODUCT_OPERATIONALIZATION"
    assert task["evidence_rule_id"] == "toddler_meal_routine"


def test_mpasi_feeding_context_changes_count_target_through_stage4():
    breastfed = _stage5(_mpasi(feeding_mode="breastmilk"), "meal_frequency")
    formula = _stage5(_mpasi(feeding_mode="formula"), "meal_frequency")
    assert breastfed["tasks"][0]["target_value"] == 2
    assert formula["tasks"][0]["target_value"] == 3
    assert breastfed["tasks"][0]["evidence_rule_id"] != formula["tasks"][0]["evidence_rule_id"]


def test_recommendation_guest_flow_still_requires_no_auth_and_contains_stage4_inputs():
    result = generate_nutrition_recommendation(_toddler(meal_routine="irregular"))
    assert result.baseline
    assert result.primary_gap
    assert result.primary_target
    assert result.evidence_rule_evaluation["status"] == "MATCHED"
