"""Stage 3 nutrition profile normalization, behavioral gap detection and target candidates.

This module is deliberately deterministic. It turns category-specific assessment
answers into structured baseline values that can be consumed by later program
rules. It does not diagnose disease or nutritional status.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.nutrition.program_evidence import EVIDENCE, mpasi_band, mpasi_meal_target, target_for_metric


def calculate_age_months(date_of_birth: date, assessment_date: date) -> int:
    if date_of_birth > assessment_date:
        raise ValueError("Tanggal lahir tidak boleh setelah tanggal assessment")
    months = (assessment_date.year - date_of_birth.year) * 12 + assessment_date.month - date_of_birth.month
    if assessment_date.day < date_of_birth.day:
        months -= 1
    return max(0, months)


def child_age_band(stage: str, age_months: int) -> str:
    if stage == "mpasi":
        return mpasi_band(age_months)
    if stage == "toddler":
        return "24–59"
    return ""


def _value(value: Any, value_type: str, *, unit: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"value": value, "type": value_type}
    if unit:
        row["unit"] = unit
    return row


def _evidence(source_key: str) -> dict[str, Any]:
    source = EVIDENCE[source_key]
    return {
        "source_name": source["source_name"],
        "source_type": source["source_type"],
        "source_url": source["url"],
        "evidence_level": source["evidence_level"],
        "last_reviewed": source["last_reviewed"],
    }


def normalize_baseline(req: Any) -> dict[str, Any]:
    if req.stage not in {"mpasi", "toddler"}:
        return {}

    age_months = int(req.age_months or 0)
    food_groups = list(req.recent_food_groups or [])
    food_group_count = req.recent_food_group_count
    if food_group_count is None and food_groups:
        food_group_count = len(food_groups)

    food_rejection = req.food_rejection
    if food_rejection is None:
        food_rejection = "frequent" if req.food_refusal else "none"

    feeding_difficulty = req.feeding_difficulty or "none"
    baseline: dict[str, Any] = {
        "category": req.stage,
        "date_of_birth": req.date_of_birth.isoformat() if req.date_of_birth else None,
        "assessment_date": (req.assessment_date or date.today()).isoformat(),
        "age_months": _value(age_months, "count", unit="months"),
        "age_band": _value(child_age_band(req.stage, age_months), "enum"),
        "meal_frequency": _value(req.meal_frequency, "count", unit="meals_per_day"),
        "snack_frequency": _value(req.snack_frequency, "count", unit="snacks_per_day"),
        "protein_exposure": _value(req.animal_source_food_days, "count", unit="days_per_7_days"),
        "fruit_vegetable_exposure": _value(req.fruit_vegetable_days, "count", unit="days_per_7_days"),
        "food_variety": _value(food_groups, "multi_select"),
        "food_group_count": _value(food_group_count, "count", unit="groups"),
        "responsive_feeding": _value(req.responsive_feeding, "enum"),
        "food_rejection": _value(food_rejection, "enum"),
        "food_rejection_details": _value(list(req.food_rejection_details or []), "multi_select"),
        "feeding_difficulty": _value(feeding_difficulty, "enum"),
        "feeding_difficulty_details": _value(list(req.feeding_difficulty_details or []), "multi_select"),
        "meal_routine": _value(req.meal_routine, "enum"),
        "barriers": _value(list(req.barriers or []), "multi_select"),
        "primary_concerns": _value([req.primary_concern] if req.primary_concern else [], "multi_select"),
    }

    if req.stage == "mpasi":
        baseline.update({
            "feeding_context": _value(req.feeding_mode, "enum"),
            "mpasi_history": _value(req.mpasi_history, "enum"),
            "feeding_method": _value(req.feeding_method, "enum"),
            "texture": _value(req.texture_level, "enum"),
            "texture_concern": _value(bool(req.texture_refusal), "boolean"),
            "safety_hygiene": _value(req.safety_hygiene_ok, "boolean"),
        })
    else:
        sweetened = req.sweetened_beverage_exposure
        if sweetened is None:
            sweetened = bool((req.sweet_beverage_days or 0) > 0)
        baseline.update({
            "self_feeding": _value(bool(req.self_feeding_opportunity), "boolean"),
            "pressure_to_eat": _value(bool(req.pressure_to_eat), "boolean"),
            "meal_distraction": _value(bool(req.screen_during_meals) or req.meal_environment == "distracted", "boolean"),
            "meal_environment": _value(req.meal_environment, "enum"),
            "mealtime_duration": _value(req.mealtime_duration_minutes, "count", unit="minutes"),
            "food_preferences": _value(list(req.food_preferences or []), "multi_select"),
            "sweetened_beverage": _value(bool(sweetened), "boolean"),
            "sweetened_beverage_frequency": _value(req.sweet_beverage_days, "count", unit="days_per_7_days"),
            "water_primary_beverage": _value(req.water_primary_beverage, "boolean"),
            "repeated_exposure": _value(req.repeated_exposure_days, "count", unit="days_per_7_days"),
        })

    baseline["evidence"] = {
        "age_band": _evidence("who_cf_2023" if req.stage == "mpasi" else "toddler_meal_evidence"),
        "dietary_diversity": _evidence("who_mdd") if req.stage == "mpasi" else _evidence("toddler_veg_review"),
        "responsive_feeding": _evidence("who_responsive" if req.stage == "mpasi" else "caregiver_feeding_review"),
    }
    return baseline


def _baseline_value(baseline: dict[str, Any], key: str) -> Any:
    value = baseline.get(key)
    return value.get("value") if isinstance(value, dict) else value


def detect_gaps(req: Any, baseline: dict[str, Any]) -> list[dict[str, Any]]:
    if req.stage not in {"mpasi", "toddler"}:
        return []

    gaps: list[dict[str, Any]] = []

    def add(gap_id: str, metric: str, label: str, *, tier: int, severity: int, baseline_key: str, expected: str, rationale: str) -> None:
        spec = target_for_metric(req.stage, metric, req.model_dump(mode="json"))
        gaps.append({
            "id": gap_id,
            "metric": metric,
            "label": label,
            "baseline": _baseline_value(baseline, baseline_key),
            "expected": expected,
            "priority_tier": tier,
            "severity": severity,
            "rationale": rationale,
            "evidence": spec.get("evidence_rule"),
        })

    if req.stage == "mpasi":
        age = int(req.age_months or 0)
        meals = int(req.meal_frequency or 0)
        meal_target = mpasi_meal_target(age, req.feeding_mode)
        groups = _baseline_value(baseline, "food_group_count")
        rejection = str(_baseline_value(baseline, "food_rejection") or "none")
        difficulty = str(_baseline_value(baseline, "feeding_difficulty") or "none")

        texture_issue = bool(req.texture_refusal) or (age >= 12 and req.texture_level == "smooth_mashed")
        if texture_issue:
            add("mpasi_texture_concern", "texture", "Tekstur perlu disesuaikan dengan kemampuan makan", tier=1, severity=3, baseline_key="texture", expected="Tekstur berkembang bertahap sesuai kemampuan anak.", rationale="Ini adalah concern feeding/texture untuk panduan perilaku, bukan diagnosis.")
        if difficulty == "significant":
            add("mpasi_feeding_difficulty", "food_response", "Kesulitan makan sering menghambat proses makan", tier=1, severity=2, baseline_key="feeding_difficulty", expected="Kesulitan makan tidak mendominasi sebagian besar kesempatan makan.", rationale="Kesulitan yang dilaporkan diprioritaskan sebelum optimasi kebiasaan lain.")
        if meals and meals < meal_target:
            add("mpasi_meal_frequency", "meal_frequency", "Frekuensi makan berada di bawah target program", tier=2, severity=3, baseline_key="meal_frequency", expected=f"Sekurang-kurangnya {meal_target} kesempatan makan pendamping per hari untuk konteks yang dipilih.", rationale="Target mengikuti age band dan feeding context yang dipilih.")
        if isinstance(groups, int) and groups < 5:
            add("mpasi_dietary_diversity", "dietary_diversity", "Keragaman kelompok pangan masih terbatas", tier=2, severity=2, baseline_key="food_group_count", expected="Indikator pemantauan menggunakan sedikitnya 5 dari 8 kelompok pangan.", rationale="Ini adalah indikator praktik pemberian makan WHO/UNICEF, bukan diagnosis status gizi.")
        if int(req.animal_source_food_days or 0) == 0:
            add("mpasi_protein_exposure", "animal_source_food", "Belum ada paparan sumber pangan hewani pada periode yang dicatat", tier=2, severity=2, baseline_key="protein_exposure", expected="Ada kesempatan menawarkan sumber pangan hewani dalam pola makan beragam.", rationale="Paparan dipakai sebagai fokus perilaku program, bukan cut-off klinis.")
        if int(req.fruit_vegetable_days or 0) == 0:
            add("mpasi_fruit_vegetable", "fruit_vegetable", "Belum ada kesempatan sayur atau buah pada periode yang dicatat", tier=3, severity=2, baseline_key="fruit_vegetable_exposure", expected="Ada kesempatan menawarkan sayur atau buah sebagai bagian variasi pangan.", rationale="Fokus pada kesempatan paparan, bukan kewajiban menghabiskan porsi.")
        if rejection == "frequent":
            add("mpasi_food_rejection", "food_response", "Penolakan makanan sering terjadi", tier=3, severity=3, baseline_key="food_rejection", expected="Respons makanan dipantau melalui paparan tanpa paksaan.", rationale="Penolakan berulang diprioritaskan sebagai behavioral feeding issue.")
        if req.responsive_feeding in {"rarely", "sometimes"}:
            add("mpasi_responsive_feeding", "responsive_feeding", "Responsive feeding masih dapat diperkuat", tier=4, severity=1 if req.responsive_feeding == "sometimes" else 2, baseline_key="responsive_feeding", expected="Respons lapar/kenyang diikuti tanpa memaksa.", rationale="Responsive feeding adalah praktik pemberian makan, bukan penilaian kesehatan anak.")
    else:
        rejection = str(_baseline_value(baseline, "food_rejection") or "none")
        difficulty = str(_baseline_value(baseline, "feeding_difficulty") or "none")
        if difficulty == "significant":
            add("toddler_feeding_difficulty", "food_response", "Kesulitan makan sering menghambat rutinitas", tier=1, severity=2, baseline_key="feeding_difficulty", expected="Kesulitan makan tidak mendominasi sebagian besar kesempatan makan.", rationale="Kesulitan yang dilaporkan ditinjau sebelum optimasi kebiasaan lain.")
        if req.meal_routine in {"irregular", "mixed"}:
            add("toddler_meal_routine", "meal_routine", "Rutinitas makan belum konsisten", tier=2, severity=3 if req.meal_routine == "irregular" else 2, baseline_key="meal_routine", expected="Waktu makan utama memiliki pola yang relatif konsisten.", rationale="Ini adalah target kebiasaan makan, bukan target medis.")
        if bool(_baseline_value(baseline, "sweetened_beverage")):
            add("toddler_sweetened_beverage", "sweet_beverage", "Paparan minuman berpemanis masih tercatat", tier=2, severity=3, baseline_key="sweetened_beverage_frequency", expected="Kurangi paparan minuman berpemanis dan prioritaskan air.", rationale="Fokus berupa perubahan paparan minuman yang dapat diamati.")
        if bool(req.pressure_to_eat):
            add("toddler_pressure_feeding", "responsive_feeding", "Tekanan saat makan perlu dikurangi", tier=3, severity=3, baseline_key="pressure_to_eat", expected="Ikuti tanda lapar/kenyang tanpa memaksa anak menghabiskan makanan.", rationale="Target diarahkan pada praktik caregiver yang dapat diubah.")
        if rejection == "frequent":
            add("toddler_food_rejection", "food_response", "Penolakan makanan sering terjadi", tier=3, severity=3, baseline_key="food_rejection", expected="Paparan makanan dilakukan bertahap tanpa memaksa dan respons dicatat.", rationale="Penolakan diperlakukan sebagai feeding behavior, bukan diagnosis.")
        if bool(req.screen_during_meals) or req.meal_environment == "distracted":
            add("toddler_meal_distraction", "responsive_feeding", "Distraksi saat makan masih sering terjadi", tier=3, severity=2, baseline_key="meal_distraction", expected="Kesempatan makan memberi ruang untuk fokus pada makan dan sinyal lapar/kenyang.", rationale="Distraksi adalah konteks perilaku saat makan.")
        if not bool(req.self_feeding_opportunity):
            add("toddler_self_feeding", "self_feeding", "Kesempatan makan mandiri masih terbatas", tier=4, severity=2, baseline_key="self_feeding", expected="Ada kesempatan makan mandiri sesuai kemampuan anak.", rationale="Kesempatan makan mandiri dipantau sebagai kebiasaan yang dapat diamati.")
        if int(req.fruit_vegetable_days or 0) == 0:
            add("toddler_fruit_vegetable", "vegetable_fruit_exposure", "Kesempatan sayur atau buah belum tercatat", tier=4, severity=2, baseline_key="fruit_vegetable_exposure", expected="Ada kesempatan mencoba sayur atau buah tanpa paksaan.", rationale="Paparan berulang digunakan sebagai strategi perilaku.")
        if int(req.animal_source_food_days or 0) == 0:
            add("toddler_protein", "protein_presence", "Sumber protein belum tercatat pada periode pengamatan", tier=4, severity=1, baseline_key="protein_exposure", expected="Sumber protein hadir sebagai bagian pola makan beragam.", rationale="Ini adalah fokus pola makan, bukan indikator diagnosis.")

    gaps.sort(key=lambda row: (int(row["priority_tier"]), -int(row["severity"]), str(row["id"])))
    return gaps


def _metric_baseline(metric: str, baseline: dict[str, Any]) -> Any:
    mapping = {
        "meal_frequency": "meal_frequency",
        "animal_source_food": "protein_exposure",
        "fruit_vegetable": "fruit_vegetable_exposure",
        "dietary_diversity": "food_group_count",
        "responsive_feeding": "responsive_feeding",
        "texture": "texture",
        "food_response": "food_rejection",
        "meal_routine": "meal_routine",
        "sweet_beverage": "sweetened_beverage_frequency",
        "vegetable_fruit_exposure": "fruit_vegetable_exposure",
        "self_feeding": "self_feeding",
        "protein_presence": "protein_exposure",
    }
    return _baseline_value(baseline, mapping.get(metric, metric))


def target_candidate(req: Any, baseline: dict[str, Any], metric: str, priority: int) -> dict[str, Any]:
    spec = target_for_metric(req.stage, metric, req.model_dump(mode="json"))
    return {
        "id": f"stage3_{req.stage}_{metric}",
        "metric": metric,
        "baseline": _metric_baseline(metric, baseline),
        "target": spec.get("target_value"),
        "unit": spec.get("unit") or "behavioral_observation",
        "priority": priority,
        "rationale": spec.get("why") or "Target kandidat dibentuk dari baseline assessment.",
        "label": spec.get("target_label") or metric.replace("_", " ").title(),
        "evidence": spec.get("evidence_rule"),
    }


def build_stage3_profile(req: Any) -> dict[str, Any]:
    if req.stage not in {"mpasi", "toddler"}:
        return {"baseline": {}, "gaps": [], "primary_gap": None, "primary_target": None, "support_targets": []}

    baseline = normalize_baseline(req)
    gaps = detect_gaps(req, baseline)

    if gaps:
        primary_gap = gaps[0]
        ordered_metrics = [str(row["metric"]) for row in gaps]
    else:
        fallback_metric = "responsive_feeding" if req.stage == "mpasi" else "meal_routine"
        spec = target_for_metric(req.stage, fallback_metric, req.model_dump(mode="json"))
        primary_gap = {
            "id": f"{req.stage}_maintenance_opportunity",
            "metric": fallback_metric,
            "label": "Tidak ada gap perilaku besar dari data yang diisi; gunakan satu kebiasaan terukur sebagai fokus pemeliharaan.",
            "baseline": _metric_baseline(fallback_metric, baseline),
            "expected": spec.get("target_label"),
            "priority_tier": 4,
            "severity": 0,
            "rationale": "Product heuristic untuk memilih fokus yang dapat diukur ketika tidak ada gap besar terdeteksi.",
            "evidence": spec.get("evidence_rule"),
        }
        ordered_metrics = [fallback_metric]

    fallback_support = (
        ["animal_source_food", "dietary_diversity", "responsive_feeding", "fruit_vegetable"]
        if req.stage == "mpasi"
        else ["vegetable_fruit_exposure", "responsive_feeding", "self_feeding", "protein_presence"]
    )
    metrics: list[str] = []
    for metric in ordered_metrics + fallback_support:
        if metric not in metrics:
            metrics.append(metric)
    primary_metric = metrics[0]
    support_metrics = metrics[1:4]

    return {
        "baseline": baseline,
        "gaps": gaps,
        "primary_gap": primary_gap,
        "primary_target": target_candidate(req, baseline, primary_metric, 1),
        "support_targets": [target_candidate(req, baseline, metric, index + 2) for index, metric in enumerate(support_metrics)],
    }
