from __future__ import annotations

from app.nutrition.safety_red_flags import detect_red_flags


def _codes(text: str) -> set[str]:
    return {str(item["code"]) for item in detect_red_flags(text)}


def test_red_flag_detector_matches_core_who_danger_signs_and_airway_signs():
    assert "BREATHING_DIFFICULTY" in _codes("anak sulit bernapas setelah makan")
    assert "CONVULSION" in _codes("anak kejang")
    assert "ALTERED_CONSCIOUSNESS" in _codes("anak sulit dibangunkan")
    assert "UNABLE_TO_DRINK" in _codes("anak tidak bisa minum")
    assert "VOMITS_EVERYTHING" in _codes("setiap minum muntah")
    assert "AIRWAY_SWELLING" in _codes("lidah bengkak dan sulit menelan")


def test_red_flag_detector_does_not_promote_mild_observation_or_negated_terms():
    assert detect_red_flags("muncul ruam ringan dan anak rewel") == []
    assert detect_red_flags("anak tidak sesak, tidak mengalami kejang, dan tetap bisa minum") == []
