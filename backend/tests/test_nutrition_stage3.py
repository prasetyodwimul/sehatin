import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.nutrition import NutritionRequest
from app.services.nutrition_service import generate_nutrition_recommendation

client = TestClient(app)
ASSESSMENT_DATE = "2026-09-24"


def _mpasi(dob: str, **extra):
    return {
        "stage": "mpasi",
        "date_of_birth": dob,
        "assessment_date": ASSESSMENT_DATE,
        "feeding_mode": "breastmilk",
        "sex": "female",
        "weight_kg": 8.2,
        "height_cm": 69.0,
        "meal_frequency": 2,
        **extra,
    }


def _toddler(dob: str, **extra):
    return {
        "stage": "toddler",
        "date_of_birth": dob,
        "assessment_date": ASSESSMENT_DATE,
        "sex": "female",
        "weight_kg": 14.0,
        "height_cm": 95.0,
        "meal_frequency": 3,
        **extra,
    }


def test_mpasi_accepts_valid_profile_and_calculates_age_from_dates():
    response = client.post("/api/nutrition/recommendation", json=_mpasi("2026-01-24"))
    assert response.status_code == 200
    body = response.json()
    assert body["baseline"]["age_months"] == {"value": 8, "type": "count", "unit": "months"}
    assert body["baseline"]["age_band"]["value"] == "6–8"


@pytest.mark.parametrize(
    ("dob", "band"),
    [
        ("2026-03-24", "6–8"),
        ("2026-01-24", "6–8"),
        ("2025-12-24", "9–11"),
        ("2025-10-24", "9–11"),
        ("2025-09-24", "12–23"),
        ("2024-10-24", "12–23"),
    ],
)
def test_mpasi_age_bands_are_deterministic(dob, band):
    req = NutritionRequest(**_mpasi(dob))
    result = generate_nutrition_recommendation(req)
    assert req.age_months is not None
    assert result.baseline["age_band"]["value"] == band


@pytest.mark.parametrize("dob", ["2026-04-24", "2024-09-24"])
def test_mpasi_rejects_out_of_product_age(dob):
    response = client.post("/api/nutrition/recommendation", json=_mpasi(dob))
    assert response.status_code == 422


@pytest.mark.parametrize(("dob", "age"), [("2024-09-24", 24), ("2021-10-24", 59)])
def test_toddler_accepts_24_to_59_month_profile(dob, age):
    req = NutritionRequest(**_toddler(dob))
    assert req.age_months == age
    result = generate_nutrition_recommendation(req)
    assert result.baseline["age_band"]["value"] == "24–59"


@pytest.mark.parametrize("dob", ["2024-10-24", "2021-09-24"])
def test_toddler_rejects_out_of_product_age(dob):
    response = client.post("/api/nutrition/recommendation", json=_toddler(dob))
    assert response.status_code == 422


def test_stage3_baseline_preserves_count_boolean_enum_and_multi_select():
    req = NutritionRequest(**_toddler(
        "2023-09-24",
        meal_frequency=3,
        recent_food_groups=["grains", "eggs", "other_produce"],
        responsive_feeding="usually",
        self_feeding_opportunity=True,
        sweetened_beverage_exposure=False,
        sweet_beverage_days=4,
    ))
    result = generate_nutrition_recommendation(req)
    baseline = result.baseline
    assert baseline["meal_frequency"] == {"value": 3, "type": "count", "unit": "meals_per_day"}
    assert baseline["self_feeding"] == {"value": True, "type": "boolean"}
    assert baseline["responsive_feeding"] == {"value": "usually", "type": "enum"}
    assert baseline["food_variety"] == {"value": ["grains", "eggs", "other_produce"], "type": "multi_select"}
    assert baseline["food_group_count"]["value"] == 3
    assert req.sweet_beverage_days == 0


def test_conditional_detail_is_cleared_when_parent_enum_is_none():
    req = NutritionRequest(**_toddler(
        "2023-09-24",
        food_rejection="none",
        food_rejection_details=["brokoli"],
        feeding_difficulty="none",
        feeding_difficulty_details=["tekstur"],
    ))
    assert req.food_rejection_details == []
    assert req.feeding_difficulty_details == []


def test_primary_gap_and_target_are_deterministic_and_traceable():
    payload = _toddler(
        "2023-09-24",
        meal_routine="irregular",
        sweetened_beverage_exposure=True,
        sweet_beverage_days=5,
        pressure_to_eat=True,
        self_feeding_opportunity=False,
    )
    first = generate_nutrition_recommendation(NutritionRequest(**payload))
    second = generate_nutrition_recommendation(NutritionRequest(**payload))
    assert first.primary_gap == second.primary_gap
    assert first.primary_gap["metric"] == "meal_routine"
    assert first.primary_target["metric"] == first.primary_gap["metric"]
    assert 2 <= len(first.support_targets) <= 4
    evidence = first.primary_target["evidence"]
    for key in ("source_name", "source_type", "source_url", "evidence_level", "last_reviewed"):
        assert evidence[key]


def test_stage3_output_uses_behavioral_language_not_diagnosis():
    result = generate_nutrition_recommendation(NutritionRequest(**_mpasi(
        "2025-09-24",
        meal_frequency=1,
        recent_food_groups=["grains"],
        food_rejection="frequent",
        feeding_difficulty="some",
    )))
    text = " ".join([
        result.primary_gap["label"],
        result.primary_gap["rationale"],
        result.primary_target["label"],
        *(target["label"] for target in result.support_targets),
    ]).lower()
    for forbidden in ("kekurangan gizi", "anak tidak sehat", "diagnosis penyakit", "status gizi buruk"):
        assert forbidden not in text
