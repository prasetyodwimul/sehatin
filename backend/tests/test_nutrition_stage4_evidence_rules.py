import json

import pytest

from app.nutrition.profile_baseline import normalize_baseline
from app.nutrition.program_evidence import EVIDENCE_RULES, evaluate_evidence_rules
from app.schemas.nutrition import NutritionRequest
from app.services.nutrition_service import generate_nutrition_recommendation


def _mpasi(age=8, feeding_mode="breastmilk", meal_frequency=1, **extra):
    return NutritionRequest(
        stage="mpasi",
        age_months=age,
        feeding_mode=feeding_mode,
        sex="female",
        weight_kg=8.0,
        height_cm=68.0,
        meal_frequency=meal_frequency,
        **extra,
    )


def _toddler(age=36, **extra):
    return NutritionRequest(
        stage="toddler",
        age_months=age,
        sex="female",
        weight_kg=14.0,
        height_cm=95.0,
        meal_frequency=3,
        **extra,
    )


def _evaluate(req, metric, baseline_key=None, baseline_override=None):
    baseline = normalize_baseline(req)
    if baseline_key and baseline_override is not None:
        baseline[baseline_key] = baseline_override
    return evaluate_evidence_rules(
        category=req.stage,
        profile=req.model_dump(mode="json"),
        baseline=baseline,
        primary_gap={"metric": metric},
        support_gaps=[],
    )


@pytest.mark.parametrize(
    ("age", "expected_rule"),
    [
        (8, "mpasi_meal_frequency_6_8_bf"),
        (10, "mpasi_meal_frequency_9_11_bf"),
        (15, "mpasi_meal_frequency_12_23_bf"),
    ],
)
def test_mpasi_rule_matching_uses_age_band(age, expected_rule):
    result = _evaluate(_mpasi(age=age, meal_frequency=1), "meal_frequency")
    assert result["status"] == "MATCHED"
    assert result["matched_rules"][0]["rule_id"] == expected_rule


def test_mpasi_out_of_range_age_returns_no_rule_without_inventing_target():
    result = evaluate_evidence_rules(
        category="mpasi",
        profile={"age_months": 5, "feeding_mode": "breastmilk"},
        baseline={"age_months": {"value": 5}, "meal_frequency": {"value": 1}},
        primary_gap={"metric": "meal_frequency"},
        support_gaps=[],
    )
    assert result["status"] == "NO_MATCHING_RULE"
    assert result["targets"] == []
    assert result["evidence_available"] is False


def test_toddler_out_of_range_age_returns_no_rule():
    result = evaluate_evidence_rules(
        category="toddler",
        profile={"age_months": 23},
        baseline={"age_months": {"value": 23}, "meal_routine": {"value": "irregular"}},
        primary_gap={"metric": "meal_routine"},
        support_gaps=[],
    )
    assert result["status"] == "NO_MATCHING_RULE"


def test_same_age_different_feeding_context_selects_context_specific_rule():
    breastfed = _evaluate(_mpasi(age=8, feeding_mode="breastmilk", meal_frequency=1), "meal_frequency")
    formula = _evaluate(_mpasi(age=8, feeding_mode="formula", meal_frequency=1), "meal_frequency")
    assert breastfed["matched_rules"][0]["rule_id"] == "mpasi_meal_frequency_6_8_bf"
    assert formula["matched_rules"][0]["rule_id"] == "mpasi_meal_frequency_6_8_non_bf"
    assert breastfed["primary_target"]["target"] == 2
    assert formula["primary_target"]["target"] == 3


def test_specific_rule_beats_generic_rule_when_both_apply():
    result = _evaluate(_mpasi(age=8, feeding_mode="mixed", meal_frequency=1), "meal_frequency")
    assert result["matched_rules"][0]["rule_id"] == "mpasi_meal_frequency_6_8_bf"
    assert result["matched_rules"][0]["feeding_context"] == ["breastmilk", "mixed"]


def test_baseline_condition_must_be_true_before_rule_matches():
    result = _evaluate(_mpasi(age=8, meal_frequency=3), "meal_frequency")
    assert result["status"] == "NO_MATCHING_RULE"
    assert result["unmatched_metrics"] == ["meal_frequency"]


def test_target_is_measurable_and_preserves_evidence_rule_id():
    result = _evaluate(_mpasi(age=10, meal_frequency=2), "meal_frequency")
    target = result["primary_target"]
    assert target["target"] == 3
    assert target["unit"] == "meals_per_day"
    assert target["evidence_rule_id"] == "mpasi_meal_frequency_9_11_bf"


def test_evidence_metadata_is_traceable():
    req = _mpasi(age=12, meal_frequency=3, recent_food_groups=["grains", "eggs"])
    result = _evaluate(req, "dietary_diversity")
    evidence = result["matched_rules"][0]["evidence"]
    for key in ("source_name", "source_type", "source_url", "evidence_level", "last_reviewed"):
        assert evidence[key]
    assert result["matched_rules"][0]["rule_id"] == "mpasi_dietary_diversity_5_of_8"


def test_authoritative_and_product_heuristic_are_not_mislabeled():
    guideline = _evaluate(_mpasi(age=12, recent_food_groups=["grains"], meal_frequency=3), "dietary_diversity")
    heuristic = _evaluate(_toddler(meal_routine="irregular"), "meal_routine")
    assert guideline["matched_rules"][0]["evidence"]["evidence_level"] == "AUTHORITATIVE"
    assert heuristic["matched_rules"][0]["evidence"]["evidence_level"] == "PRODUCT_HEURISTIC"
    assert heuristic["matched_rules"][0]["product_note"]


def test_toddler_habit_rules_match_without_diagnosis():
    cases = [
        (_toddler(meal_routine="irregular"), "meal_routine", "toddler_meal_routine"),
        (_toddler(sweetened_beverage_exposure=True, sweet_beverage_days=4), "sweet_beverage", "toddler_sweetened_beverage"),
        (_toddler(fruit_vegetable_days=0), "vegetable_fruit_exposure", "toddler_food_variety_exposure"),
        (_toddler(food_rejection="frequent"), "food_response", "toddler_food_rejection"),
    ]
    for req, metric, expected_rule in cases:
        result = _evaluate(req, metric)
        assert result["matched_rules"][0]["rule_id"] == expected_rule
        text = json.dumps(result, ensure_ascii=False).lower()
        for forbidden in ("anak tidak sehat", "kekurangan gizi", "diagnosis penyakit", "status gizi buruk"):
            assert forbidden not in text



def test_stage3_feeding_difficulty_metric_has_stage4_rule_for_both_child_categories():
    mpasi = _evaluate(_mpasi(age=12, meal_frequency=3, feeding_difficulty="significant"), "food_response")
    toddler = _evaluate(_toddler(feeding_difficulty="significant"), "food_response")
    assert mpasi["matched_rules"][0]["rule_id"] == "mpasi_feeding_difficulty_observation"
    assert toddler["matched_rules"][0]["rule_id"] == "toddler_feeding_difficulty_observation"
    assert mpasi["matched_rules"][0]["evidence"]["evidence_level"] == "PRODUCT_HEURISTIC"
    assert toddler["matched_rules"][0]["evidence"]["evidence_level"] == "PRODUCT_HEURISTIC"

def test_no_matching_rule_returns_structured_fallback_for_unsupported_metric():
    result = _evaluate(_toddler(), "mealtime_duration")
    assert result["status"] == "NO_MATCHING_RULE"
    assert result["evidence_available"] is False
    assert result["unmatched_metrics"] == ["mealtime_duration"]
    assert "Belum ada panduan terstruktur" in result["message"]


def test_rule_output_is_deterministic_for_same_profile_and_baseline():
    req = _toddler(meal_routine="irregular", pressure_to_eat=True)
    baseline = normalize_baseline(req)
    kwargs = dict(
        category="toddler",
        profile=req.model_dump(mode="json"),
        baseline=baseline,
        primary_gap={"metric": "meal_routine"},
        support_gaps=[{"metric": "responsive_feeding"}],
    )
    assert evaluate_evidence_rules(**kwargs) == evaluate_evidence_rules(**kwargs)


def test_rule_registry_is_immutable_tuple_of_frozen_definitions():
    assert isinstance(EVIDENCE_RULES, tuple)
    with pytest.raises(Exception):
        EVIDENCE_RULES[0].priority = 999  # type: ignore[misc]


def test_recommendation_exposes_stage4_trace_without_new_endpoint():
    result = generate_nutrition_recommendation(_toddler(meal_routine="irregular", pressure_to_eat=True))
    trace = result.evidence_rule_evaluation
    assert trace["status"] == "MATCHED"
    assert trace["primary_target"]["evidence_rule_id"] == "toddler_meal_routine"
    assert result.suggested_goals[0]["goal_key"] == "meal_routine"


def test_unavailable_or_conflicting_metric_is_not_fabricated():
    result = _evaluate(_toddler(mealtime_duration_minutes=90), "mealtime_duration")
    assert result["status"] == "NO_MATCHING_RULE"
    assert result["matched_rules"] == []
    assert result["primary_target"] is None
