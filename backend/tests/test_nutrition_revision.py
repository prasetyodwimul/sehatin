from fastapi.testclient import TestClient

from app.main import app
from app.schemas.nutrition import NutritionRequest
from app.services.nutrition_service import generate_nutrition_recommendation

client = TestClient(app)


def test_mpasi_requires_feeding_mode():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 8},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"


def test_mpasi_rejects_under_six_months():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 1, "feeding_mode": "breastmilk"},
    )
    assert response.status_code == 422


def test_mpasi_age_bands_are_materially_different():
    six = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 6, "feeding_mode": "breastmilk", "sex": "female", "weight_kg": 7.3, "height_cm": 66.0},
    ).json()
    twelve = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 12, "feeding_mode": "breastmilk", "sex": "female", "weight_kg": 8.9, "height_cm": 74.0},
    ).json()

    assert six["age_band"] == "MPASI 6-8 bulan"
    assert twelve["age_band"] == "MPASI 12-23 bulan"
    assert "200 kkal" in six["estimated_needs"]["energi_dari_mpasi"]
    assert "550 kkal" in twelve["estimated_needs"]["energi_dari_mpasi"]
    assert six["meal_pattern"]["texture"] != twelve["meal_pattern"]["texture"]
    assert six["sample_menu"] != twelve["sample_menu"]


def test_mpasi_formula_does_not_fake_complementary_energy_number():
    body = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 8, "feeding_mode": "formula", "sex": "male", "weight_kg": 8.2, "height_cm": 69.0},
    ).json()
    assert "Tidak dihitung sebagai angka tunggal" in body["estimated_needs"]["energi_dari_mpasi"]


def test_toddler_akg_changes_at_four_year_band():
    age_36 = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "toddler", "age_months": 36, "sex": "female", "weight_kg": 14.0, "height_cm": 95.0},
    ).json()
    age_48 = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "toddler", "age_months": 48, "sex": "male", "weight_kg": 16.0, "height_cm": 103.0},
    ).json()
    assert age_36["estimated_needs"]["energi_referensi"] == "1350 kkal/hari"
    assert age_48["estimated_needs"]["energi_referensi"] == "1400 kkal/hari"
    assert age_36["estimated_needs"]["protein_referensi"] == "20 g/hari"
    assert age_48["estimated_needs"]["protein_referensi"] == "25 g/hari"


def test_elderly_requires_sex_for_akg_selection():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "elderly", "age_years": 70},
    )
    assert response.status_code == 422


def test_elderly_reference_differs_by_sex_and_age():
    male = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "elderly", "age_years": 70, "sex": "male", "weight_kg": 65, "height_cm": 168},
    ).json()
    female = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "elderly", "age_years": 70, "sex": "female", "weight_kg": 55, "height_cm": 155},
    ).json()
    assert male["estimated_needs"]["energi_referensi"] == "1800 kkal/hari"
    assert female["estimated_needs"]["energi_referensi"] == "1550 kkal/hari"


def test_elderly_weight_adds_general_protein_orientation_only_when_safe():
    healthy = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "elderly", "age_years": 70, "sex": "female", "weight_kg": 55, "height_cm": 155},
    ).json()
    kidney = client.post(
        "/api/nutrition/recommendation",
        json={
            "stage": "elderly",
            "age_years": 70,
            "sex": "female",
            "weight_kg": 55,
            "height_cm": 155,
            "medical_context": "penyakit ginjal",
        },
    ).json()
    assert "protein_berdasarkan_berat" in healthy["estimated_needs"]
    assert "protein_berdasarkan_berat" not in kidney["estimated_needs"]
    assert kidney["personalization_status"] == "limited_for_safety"


def test_dysphagia_disables_specific_menu_personalization():
    body = client.post(
        "/api/nutrition/recommendation",
        json={
            "stage": "elderly",
            "age_years": 75,
            "sex": "male",
            "weight_kg": 65,
            "height_cm": 168,
            "swallowing_difficulty": True,
        },
    ).json()
    assert body["personalization_status"] == "limited_for_safety"
    assert body["sample_menu"]
    assert "diketahui aman" in body["sample_menu"][0].lower()
    assert "tidak dibuat" not in body["sample_menu"][0].lower()
    assert any("IDDSI" in ref for ref in body["references"])


def test_allergy_filters_matching_menu_examples():
    result = generate_nutrition_recommendation(
        NutritionRequest(
            stage="toddler",
            age_months=36,
            sex="female",
            weight_kg=14,
            height_cm=95,
            allergies=["telur", "ikan", "susu"],
        )
    )
    joined = " ".join(result.sample_menu).lower()
    assert "telur" not in joined
    assert "ikan" not in joined
    assert "yogurt" not in joined


def test_public_nutrition_response_does_not_expose_internal_source_metadata():
    body = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "toddler", "age_months": 30, "sex": "female", "weight_kg": 13.0, "height_cm": 91.0},
    ).json()
    assert "sources" not in body
    assert "assumptions" not in body
