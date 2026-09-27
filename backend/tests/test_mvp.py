import pytest
from fastapi.testclient import TestClient

from app.blood.demo_provider import DemoBloodProvider
from app.blood.service import BloodService
from app.main import app
from app.schemas.nutrition import NutritionRequest
from app.services.nutrition_service import generate_nutrition_recommendation
from app.trust_engine.confidence_score import agreement_score, claim_support_score
from app.trust_engine.evidence_ranker import weighted_evidence_score
from app.trust_engine.trust_engine import analyze_claim

client = TestClient(app)


def test_nutrition_mpasi_calculation_is_structured():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 8, "feeding_mode": "breastmilk", "sex": "male", "weight_kg": 8.2, "height_cm": 69.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == "mpasi"
    assert "200 kkal" in body["estimated_needs"]["energi_dari_mpasi"]
    assert body["priority_nutrients"]
    assert "edukatif" in body["disclaimer"].lower()


def test_nutrition_validation_rejects_wrong_stage_age():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 30},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_INPUT"


def test_nutrition_medical_context_adds_limitation():
    result = generate_nutrition_recommendation(
        NutritionRequest(stage="elderly", age_years=67, sex="female", weight_kg=55, height_cm=155, medical_context="diabetes")
    )
    assert any("personalisasi dibatasi" in note.lower() for note in result.safety_notes)


def test_blood_demo_provider_is_explicitly_demo():
    provider = DemoBloodProvider()
    facilities = provider.list_facilities()
    assert provider.is_demo is True
    assert facilities
    assert all(item.demo_data for item in facilities)
    assert all("demonstrasi" in item.data_source.lower() for item in facilities)


def test_blood_filtering_by_type_rhesus_and_city():
    service = BloodService(DemoBloodProvider())
    facilities = service.list_facilities(blood_type="O", rhesus="+", city="Bandung")
    assert len(facilities) == 1
    assert facilities[0].city == "Bandung"
    assert len(facilities[0].inventory) == 1
    assert facilities[0].inventory[0].blood_type == "O"
    assert facilities[0].inventory[0].rhesus == "+"


def test_blood_api_filtering_and_not_found_error_shape():
    response = client.get("/api/blood/facilities", params={"blood_type": "AB", "rhesus": "+"})
    assert response.status_code == 200
    assert all(item["inventory"] for item in response.json())
    assert all(inv["blood_type"] == "AB" for f in response.json() for inv in f["inventory"])

    missing = client.get("/api/blood/facilities/missing")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


def test_evidence_weighting_is_deterministic():
    score = weighted_evidence_score(authority=1.0, quality=0.9, recency=0.8, relevance=0.7)
    assert score == pytest.approx(0.865, abs=0.001)


def test_agreement_rewards_independent_publishers():
    assert agreement_score({"WHO", "CDC"}, set()) == 1.0
    assert agreement_score({"WHO"}, set()) == 0.7


def test_claim_support_score_is_low_when_only_contradicting_evidence_exists():
    assert claim_support_score([], [0.9, 0.85]) == 0


def test_health_checker_does_not_guess_unknown_claim():
    response = client.post(
        "/api/health-checker/analyze",
        json={"text": "Klaim kesehatan yang tidak ada dalam corpus contoh ini."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert body["sources_checked"] == 0
    assert body["trust_score"] == 0


def test_health_checker_returns_structured_contradicting_evidence():
    response = client.post(
        "/api/health-checker/analyze",
        json={"text": "Antibiotik bisa menyembuhkan flu karena virus."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "CONTRADICTED"
    assert len(body["contradicting_evidence"]) >= 2
    assert body["score_breakdown"]["independent_publishers"] >= 2
    assert body["evidence_confidence"] > body["trust_score"]
    assert all(item["retrieved_at"] for item in body["contradicting_evidence"])


def test_health_checker_understands_simple_negation_direction():
    result = analyze_claim("Antibiotik tidak dapat menyembuhkan flu karena virus.")
    assert result.verdict == "SUPPORTED"
    assert result.supporting_evidence
    assert result.trust_score > 50


def test_health_checker_input_length_error_is_safe():
    response = client.post("/api/health-checker/analyze", json={"text": "pendek"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INPUT"
