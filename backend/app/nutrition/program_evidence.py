"""Evidence-backed behavioral targets for SEHATIN child nutrition programs.

This module translates evidence and explicit product decisions into observable,
measurable caregiver actions. Medical/nutritional thresholds are never invented:
where SEHATIN operationalizes evidence into a product target, the rule metadata
labels it as a product heuristic/observation rather than a clinical cut-off.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RULE_VERSION = "evidence_adaptive_v2"
STAGE5_RULE_VERSION = "personalized_daily_todo_v1"
LAST_REVIEWED = "2026-09-20"

EVIDENCE = {
    "who_cf_2023": {
        "source_name": "World Health Organization",
        "title": "WHO Guideline for complementary feeding of infants and young children 6–23 months (2023)",
        "source_type": "guideline",
        "url": "https://www.who.int/publications/i/item/9789240081864",
        "evidence_level": "authoritative_guideline",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Population guidance for complementary feeding; not a diagnostic standard.",
    },
    "who_iycf_2021": {
        "source_name": "WHO / UNICEF",
        "title": "Indicators for assessing infant and young child feeding practices (2021)",
        "source_type": "indicator_guidance",
        "url": "https://www.who.int/publications/i/item/9789240018389",
        "evidence_level": "authoritative_indicator_guidance",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Used for feeding-practice indicators, not clinical diagnosis.",
    },
    "who_mdd": {
        "source_name": "World Health Organization",
        "title": "WHO minimum dietary diversity: at least 5 of 8 food groups for children 6–23 months",
        "source_type": "indicator_guidance",
        "url": "https://www.who.int/data/nutrition/nlis/info/infant-and-young-child-feeding",
        "evidence_level": "authoritative_indicator_guidance",
        "last_reviewed": LAST_REVIEWED,
        "notes": "The 5-of-8 threshold is an IYCF indicator, not a diagnosis of nutritional status.",
    },
    "kemenkes_mpasi_2024": {
        "source_name": "Kementerian Kesehatan Republik Indonesia",
        "title": "Petunjuk Teknis Pemantauan Praktik MP-ASI Anak Usia 6–23 Bulan (2024)",
        "source_type": "national_guidance",
        "url": "https://ayosehat.kemkes.go.id/petunjuk-teknis-pemantauan-praktik-mp-asi-anak-usia-6-23-bulan",
        "evidence_level": "national_authoritative_guidance",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Applied as feeding-practice guidance for the Indonesian context.",
    },
    "who_responsive": {
        "source_name": "World Health Organization",
        "title": "WHO complementary feeding guidance on responsive feeding, hunger/fullness cues and progressive texture",
        "source_type": "guidance",
        "url": "https://www.who.int/health-topics/complementary-feeding",
        "evidence_level": "authoritative_guidance",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Supports responsive feeding and progressive texture guidance.",
    },
    "toddler_veg_review": {
        "source_name": "Peer-reviewed systematic review",
        "title": "A Systematic Review of Methods for Increasing Vegetable Consumption in Early Childhood (2–5 years)",
        "source_type": "systematic_review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28596931/",
        "evidence_level": "systematic_review",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Supports repeated exposure as a behavioral strategy; SEHATIN does not turn it into a clinical cut-off.",
    },
    "toddler_ssb_review": {
        "source_name": "Peer-reviewed systematic review",
        "title": "A systematic review of strategies to reduce sugar-sweetened beverage consumption among 0-year to 5-year olds",
        "source_type": "systematic_review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30019442/",
        "evidence_level": "systematic_review",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Supports reducing sweetened-beverage exposure.",
    },
    "caregiver_feeding_review": {
        "source_name": "Peer-reviewed systematic review",
        "title": "Caregiver feeding practices and child weight outcomes: a systematic review",
        "source_type": "systematic_review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30982865/",
        "evidence_level": "systematic_review",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Used for caregiver feeding-practice context; not for diagnosis.",
    },
    "toddler_meal_evidence": {
        "source_name": "NICE evidence review",
        "title": "NICE 2025 evidence review — healthy eating and drinking practices, including complementary feeding, 12 months to 5 years",
        "source_type": "evidence_review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/40029959/",
        "evidence_level": "evidence_review",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Supports structured healthy eating/drinking practices.",
    },
    "animal_source_foods_review": {
        "source_name": "Peer-reviewed systematic review and meta-analysis",
        "title": "Animal-source foods as a suitable complementary food for improved physical growth in 6–24-month-old children",
        "source_type": "systematic_review_meta_analysis",
        "url": "https://pubmed.ncbi.nlm.nih.gov/35109944/",
        "evidence_level": "systematic_review_meta_analysis",
        "last_reviewed": LAST_REVIEWED,
        "notes": "Supports animal-source food exposure as a relevant program focus.",
    },
}


def evidence_text(key: str) -> str:
    source = EVIDENCE[key]
    return f"{source['title']} — {source['url']}"


def mpasi_band(age_months: int | None) -> str:
    age = int(age_months or 0)
    if age <= 8:
        return "6–8"
    if age <= 11:
        return "9–11"
    return "12–23"


def mpasi_meal_target(age_months: int | None, feeding_mode: str | None) -> int:
    """Return the explicit A–F meal-frequency decision.

    `breastmilk` and `mixed` both indicate that the child still receives
    breast milk. Formula/other non-breastfed modes use the higher frequency path
    defined in the A–F product decision.
    """
    age = int(age_months or 0)
    if feeding_mode in {"breastmilk", "mixed"}:
        return 2 if age <= 8 else 3
    return 3 if age <= 8 else 4


MPASI_CONCERN_METRIC = {
    "low_animal_source_food_exposure": "animal_source_food",
    "low_food_diversity": "dietary_diversity",
    "feeding_routine_issue": "meal_frequency",
    "texture_issue": "texture",
    "food_refusal": "food_response",
    "responsive_feeding_issue": "responsive_feeding",
}

TODDLER_CONCERN_METRIC = {
    "limited_variety": "vegetable_fruit_exposure",
    "low_vegetable_exposure": "vegetable_fruit_exposure",
    "sweetened_beverage_exposure": "sweet_beverage",
    "low_self_feeding": "self_feeding",
    "pressure_feeding": "responsive_feeding",
    "irregular_meal_routine": "meal_routine",
    "food_refusal": "food_response",
}


def preferred_mpasi_metric(profile: dict[str, Any]) -> str:
    concern = str(profile.get("primary_concern") or "")
    if concern in MPASI_CONCERN_METRIC:
        return MPASI_CONCERN_METRIC[concern]
    meal_frequency = profile.get("meal_frequency")
    target = mpasi_meal_target(profile.get("age_months"), profile.get("feeding_mode"))
    if isinstance(meal_frequency, int) and meal_frequency < target:
        return "meal_frequency"
    if profile.get("texture_refusal"):
        return "texture"
    if profile.get("food_refusal"):
        return "food_response"
    if int(profile.get("animal_source_food_days") or 0) < 7:
        return "animal_source_food"
    if int(profile.get("fruit_vegetable_days") or 0) < 7:
        return "fruit_vegetable"
    if int(profile.get("recent_food_group_count") or 0) < 5:
        return "dietary_diversity"
    if profile.get("responsive_feeding") in {"rarely", "sometimes"}:
        return "responsive_feeding"
    return "meal_frequency"


def preferred_toddler_metric(profile: dict[str, Any]) -> str:
    concern = str(profile.get("primary_concern") or "")
    if concern in TODDLER_CONCERN_METRIC:
        return TODDLER_CONCERN_METRIC[concern]
    if profile.get("meal_routine") in {"irregular", "mixed"}:
        return "meal_routine"
    if int(profile.get("sweet_beverage_days") or 0) > 0:
        return "sweet_beverage"
    if profile.get("pressure_to_eat"):
        return "responsive_feeding"
    if profile.get("food_refusal"):
        return "food_response"
    if not profile.get("self_feeding_opportunity"):
        return "self_feeding"
    if int(profile.get("fruit_vegetable_days") or 0) < 7:
        return "vegetable_fruit_exposure"
    if int(profile.get("animal_source_food_days") or 0) < 7:
        return "protein_presence"
    return "vegetable_fruit_exposure"


def _rule_metadata(
    *,
    stage: str,
    metric: str,
    profile: dict[str, Any],
    source_key: str,
    target: float | str | bool | None,
    unit: str,
    description: str,
    rule_kind: str,
    rule_id: str | None = None,
) -> dict[str, Any]:
    source = EVIDENCE[source_key]
    if stage == "mpasi":
        age_range = f"{mpasi_band(profile.get('age_months'))} months"
    elif stage == "toddler":
        age_range = "24–59 months"
    else:
        age_range = "60+ years"
    return {
        "rule_id": rule_id or f"{stage}_{metric}",
        "category": stage.upper(),
        "age_range": age_range,
        "metric": metric,
        "threshold_or_target": target,
        "target_unit": unit,
        "description": description,
        "source_name": source["source_name"],
        "source_type": source["source_type"],
        "source_url": source["url"],
        "evidence_level": source["evidence_level"],
        "last_reviewed": source["last_reviewed"],
        "notes": source["notes"],
        "rule_kind": rule_kind,
    }


def target_for_metric(stage: str, metric: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Build one metric target with explicit evidence/product metadata."""
    if stage == "mpasi":
        band = mpasi_band(profile.get("age_months"))
        meals = mpasi_meal_target(profile.get("age_months"), profile.get("feeding_mode"))
        breastfed = profile.get("feeding_mode") in {"breastmilk", "mixed"}
        meal_rule_id = f"mpasi_meal_frequency_{band.replace('–', '_')}_{'bf' if breastfed else 'non_bf'}"
        mapping: dict[str, dict[str, Any]] = {
            "meal_frequency": {
                "input_type": "count",
                "target_value": float(meals),
                "unit": "waktu makan",
                "target_label": f"Minimal {meals} kali makan pendamping hari ini.",
                "action": f"Berikan makan pendamping sesuai target {meals} kali hari ini.",
                "result_prompt": "Berapa kali makan pendamping benar-benar diberikan hari ini?",
                "why": "Frekuensi mengikuti kelompok usia dan feeding mode yang dipilih.",
                "source": "who_cf_2023",
                "rule_kind": "evidence_based_rule",
                "rule_id": meal_rule_id,
            },
            "animal_source_food": {
                "input_type": "count",
                "target_value": 1.0,
                "unit": "kesempatan",
                "target_label": "1 kesempatan sumber pangan hewani hari ini.",
                "action": "Tawarkan satu sumber pangan hewani pada satu kesempatan makan hari ini.",
                "result_prompt": "Berapa kesempatan pangan hewani benar-benar ditawarkan?",
                "why": "Paparan pangan hewani dipantau sebagai perilaku pendukung pola makan beragam.",
                "source": "animal_source_foods_review",
                "rule_kind": "product_operationalization",
            },
            "fruit_vegetable": {
                "input_type": "count",
                "target_value": 1.0,
                "unit": "kesempatan",
                "target_label": "1 kesempatan sayur atau buah hari ini.",
                "action": "Tawarkan sayur atau buah pada setidaknya satu kesempatan makan hari ini.",
                "result_prompt": "Berapa kesempatan sayur/buah benar-benar ditawarkan?",
                "why": "Variasi makanan padat gizi dipantau sebagai perilaku harian.",
                "source": "who_cf_2023",
                "rule_kind": "product_operationalization",
            },
            "dietary_diversity": {
                "input_type": "count",
                "target_value": 5.0,
                "unit": "kelompok pangan",
                "target_label": "Minimal 5 dari 8 kelompok pangan pada hari pemantauan.",
                "action": "Catat jumlah kelompok pangan berbeda yang dikonsumsi anak hari ini.",
                "result_prompt": "Berapa kelompok pangan berbeda yang tercatat hari ini?",
                "why": "Indikator minimum dietary diversity WHO/UNICEF menggunakan sedikitnya 5 dari 8 kelompok pangan.",
                "source": "who_mdd",
                "rule_kind": "evidence_based_indicator",
                "rule_id": "mpasi_mdd_5_of_8",
            },
            "responsive_feeding": {
                "input_type": "boolean",
                "target_value": True,
                "unit": "hari",
                "target_label": "Responsive feeding diterapkan hari ini.",
                "action": "Respons tanda lapar/kenyang dan hindari memaksa anak makan hari ini.",
                "result_prompt": "Apakah responsive feeding diterapkan hari ini?",
                "why": "Merespons tanda lapar/kenyang dan tidak memaksa merupakan bagian dari responsive feeding.",
                "source": "who_responsive",
                "rule_kind": "evidence_based_behavior",
            },
            "texture": {
                "input_type": "boolean",
                "target_value": 1.0,
                "unit": "hari",
                "target_label": f"Tekstur sesuai kemampuan makan usia {band} bulan.",
                "action": "Sajikan tekstur yang sesuai kemampuan makan anak hari ini.",
                "result_prompt": "Apakah tekstur yang disajikan sesuai tahap dan dapat dicoba anak?",
                "why": "Konsistensi/tekstur makanan ditingkatkan bertahap sesuai kemampuan anak.",
                "source": "who_cf_2023",
                "rule_kind": "evidence_based_behavior",
            },
            "food_response": {
                "input_type": "choice",
                "target_value": "accepted",
                "unit": "respons",
                "target_label": "Catat respons anak terhadap satu paparan makanan/tekstur fokus.",
                "action": "Tawarkan satu paparan makanan/tekstur fokus tanpa memaksa, lalu catat respons anak.",
                "result_prompt": "Bagaimana respons anak pada paparan fokus hari ini?",
                "why": "Respons dicatat sebagai observasi agar paparan berikutnya dapat disesuaikan tanpa mengubah riwayat.",
                "source": "who_responsive",
                "rule_kind": "product_observation",
                "options": [
                    {"value": "accepted", "label": "Diterima"},
                    {"value": "partial", "label": "Sebagian"},
                    {"value": "refused", "label": "Ditolak"},
                ],
                "adherence_map": {"accepted": 100.0, "partial": 50.0, "refused": 0.0},
            },
        }
        spec = mapping.get(metric, mapping["meal_frequency"])
    elif stage == "toddler":
        mapping = {
            "meal_routine": {
                "input_type": "count",
                "target_value": 3.0,
                "unit": "makan utama",
                "target_label": "3 waktu makan utama terjadwal hari ini.",
                "action": "Sediakan tiga waktu makan utama yang relatif terjadwal hari ini.",
                "result_prompt": "Berapa waktu makan utama yang benar-benar berlangsung?",
                "why": "SEHATIN mengoperasionalkan rutinitas 3 makan utama sebagai target perilaku harian, bukan batas klinis.",
                "source": "toddler_meal_evidence",
                "rule_kind": "product_operationalization",
            },
            "sweet_beverage": {
                "input_type": "boolean",
                "target_value": 0.0,
                "unit": "hari",
                "target_label": "Tidak ada paparan minuman berpemanis hari ini.",
                "action": "Hindari menawarkan minuman berpemanis hari ini dan prioritaskan air.",
                "result_prompt": "Apakah minuman berpemanis ditawarkan hari ini?",
                "why": "Mengurangi paparan minuman berpemanis adalah target perilaku yang dapat dipantau.",
                "source": "toddler_ssb_review",
                "rule_kind": "evidence_supported_behavior",
            },
            "vegetable_fruit_exposure": {
                "input_type": "count",
                "target_value": 1.0,
                "unit": "kesempatan",
                "target_label": "Minimal 1 kesempatan mencoba sayur atau buah hari ini.",
                "action": "Tawarkan sayur atau buah pada satu kesempatan makan tanpa memaksa.",
                "result_prompt": "Berapa kesempatan sayur/buah benar-benar ditawarkan?",
                "why": "Paparan berulang merupakan strategi yang didukung untuk meningkatkan penerimaan sayur pada anak usia dini.",
                "source": "toddler_veg_review",
                "rule_kind": "product_operationalization",
            },
            "responsive_feeding": {
                "input_type": "boolean",
                "target_value": True,
                "unit": "hari",
                "target_label": "Respons lapar/kenyang dilakukan tanpa memaksa.",
                "action": "Ikuti tanda lapar/kenyang dan hindari tekanan untuk menghabiskan makanan.",
                "result_prompt": "Apakah makan berlangsung tanpa tekanan untuk menghabiskan makanan?",
                "why": "Responsive feeding berfokus pada tanda lapar/kenyang dan menghindari tekanan makan.",
                "source": "caregiver_feeding_review",
                "rule_kind": "evidence_supported_behavior",
            },
            "self_feeding": {
                "input_type": "count",
                "target_value": 1.0,
                "unit": "kesempatan",
                "target_label": "Minimal 1 kesempatan makan mandiri sesuai kemampuan.",
                "action": "Berikan satu kesempatan makan mandiri yang sesuai kemampuan anak.",
                "result_prompt": "Berapa kesempatan makan mandiri yang benar-benar diberikan?",
                "why": "Kesempatan makan mandiri dipantau sebagai kebiasaan yang dapat diamati.",
                "source": "caregiver_feeding_review",
                "rule_kind": "product_operationalization",
            },
            "protein_presence": {
                "input_type": "count",
                "target_value": 1.0,
                "unit": "makan utama",
                "target_label": "Sumber protein hadir pada minimal 1 makan utama.",
                "action": "Sertakan sumber protein pada setidaknya satu makan utama hari ini.",
                "result_prompt": "Pada berapa makan utama sumber protein benar-benar tersedia?",
                "why": "Protein dipantau sebagai bagian dari pola makan beragam.",
                "source": "who_cf_2023",
                "rule_kind": "product_operationalization",
            },
            "food_response": {
                "input_type": "choice",
                "target_value": "accepted",
                "unit": "respons",
                "target_label": "Catat respons terhadap satu paparan makanan fokus.",
                "action": "Tawarkan satu makanan fokus tanpa memaksa, lalu catat respons anak.",
                "result_prompt": "Bagaimana respons anak pada paparan makanan fokus hari ini?",
                "why": "Penerimaan makanan dipantau sebagai observasi untuk menentukan dukungan/paparan berikutnya.",
                "source": "toddler_veg_review",
                "rule_kind": "product_observation",
                "options": [
                    {"value": "accepted", "label": "Diterima"},
                    {"value": "partial", "label": "Sebagian"},
                    {"value": "refused", "label": "Ditolak"},
                ],
                "adherence_map": {"accepted": 100.0, "partial": 50.0, "refused": 0.0},
            },
        }
        spec = mapping.get(metric, mapping["vegetable_fruit_exposure"])
    else:
        return {
            "input_type": "boolean",
            "target_value": 1.0,
            "unit": "hari",
            "target_label": "Ikuti panduan nutrisi harian yang tersimpan.",
            "action": "Ikuti panduan nutrisi harian yang tersimpan.",
            "result_prompt": "Apakah panduan dapat diterapkan hari ini?",
            "why": "Target produk legacy untuk modul lansia.",
            "evidence": [],
            "evidence_rule": None,
            "options": [],
            "adherence_map": {},
        }

    evidence_key = str(spec["source"])
    rule = _rule_metadata(
        stage=stage,
        metric=metric,
        profile=profile,
        source_key=evidence_key,
        target=spec.get("target_value"),
        unit=str(spec.get("unit") or ""),
        description=str(spec.get("why") or ""),
        rule_kind=str(spec.get("rule_kind") or "product_operationalization"),
        rule_id=spec.get("rule_id"),
    )
    return {
        **spec,
        "evidence": [evidence_text(evidence_key)],
        "evidence_rule": rule,
        "options": spec.get("options", []),
        "adherence_map": spec.get("adherence_map", {}),
    }


@dataclass(frozen=True)
class EvidenceRuleDefinition:
    """Immutable Stage 4 rule definition.

    Stage 4 evaluates normalized Stage 3 baseline values only. Rule definitions
    never mutate during a request/session, which keeps target selection auditable
    and deterministic.
    """

    id: str
    category: str
    metric: str
    baseline_key: str
    comparator: str
    condition_value: Any
    target_value: Any
    target_unit: str
    rationale: str
    source_key: str
    priority: int = 100
    age_min: int | None = None
    age_max: int | None = None
    age_band: str | None = None
    feeding_context: tuple[str, ...] = ()
    rule_kind: str = "EVIDENCE_BASED"
    product_note: str | None = None
    status: str = "ACTIVE"


def _authoritative_level(source_key: str, rule_kind: str) -> str:
    if rule_kind == "PRODUCT_HEURISTIC":
        return "PRODUCT_HEURISTIC"
    source_type = str(EVIDENCE[source_key].get("source_type") or "").lower()
    if any(token in source_type for token in ("guideline", "guidance", "government", "national")):
        return "AUTHORITATIVE"
    return "SCIENTIFIC"


def _stage4_source(source_key: str, rule_kind: str) -> dict[str, Any]:
    source = EVIDENCE[source_key]
    return {
        "source_name": source["source_name"],
        "source_type": source["source_type"],
        "source_url": source["url"],
        "evidence_level": _authoritative_level(source_key, rule_kind),
        "source_evidence_level": source["evidence_level"],
        "last_reviewed": source["last_reviewed"],
    }


def _rule(
    rule_id: str,
    category: str,
    metric: str,
    baseline_key: str,
    comparator: str,
    condition_value: Any,
    target_value: Any,
    target_unit: str,
    rationale: str,
    source_key: str,
    *,
    priority: int,
    age_min: int | None = None,
    age_max: int | None = None,
    age_band: str | None = None,
    feeding_context: tuple[str, ...] = (),
    rule_kind: str = "EVIDENCE_BASED",
    product_note: str | None = None,
) -> EvidenceRuleDefinition:
    return EvidenceRuleDefinition(
        id=rule_id,
        category=category,
        metric=metric,
        baseline_key=baseline_key,
        comparator=comparator,
        condition_value=condition_value,
        target_value=target_value,
        target_unit=target_unit,
        rationale=rationale,
        source_key=source_key,
        priority=priority,
        age_min=age_min,
        age_max=age_max,
        age_band=age_band,
        feeding_context=feeding_context,
        rule_kind=rule_kind,
        product_note=product_note,
    )


# Stage 4 rule registry. Keep this immutable at runtime. Numeric targets are only
# encoded when already supported by the existing evidence/configuration layer.
# Product operationalisations remain explicitly labelled PRODUCT_HEURISTIC.
EVIDENCE_RULES: tuple[EvidenceRuleDefinition, ...] = (
    # MPASI meal-frequency rules: context-specific rules outrank generic rules.
    _rule("mpasi_meal_frequency_6_8_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 2, 2, "meals_per_day", "Frekuensi makan pendamping dinilai berdasarkan usia dan konteks pemberian susu yang tersimpan.", "who_cf_2023", priority=10, age_min=6, age_max=8, age_band="6–8", feeding_context=("breastmilk", "mixed")),
    _rule("mpasi_meal_frequency_9_11_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 3, 3, "meals_per_day", "Frekuensi makan pendamping dinilai berdasarkan usia dan konteks pemberian susu yang tersimpan.", "who_cf_2023", priority=10, age_min=9, age_max=11, age_band="9–11", feeding_context=("breastmilk", "mixed")),
    _rule("mpasi_meal_frequency_12_23_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 3, 3, "meals_per_day", "Frekuensi makan pendamping dinilai berdasarkan usia dan konteks pemberian susu yang tersimpan.", "who_cf_2023", priority=10, age_min=12, age_max=23, age_band="12–23", feeding_context=("breastmilk", "mixed")),
    _rule("mpasi_meal_frequency_6_8_non_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 3, 3, "meals_per_day", "SEHATIN menggunakan konteks non-breastfed untuk memilih target operasional yang sudah dipakai Nutrition Engine.", "who_cf_2023", priority=9, age_min=6, age_max=8, age_band="6–8", feeding_context=("formula", "other"), rule_kind="PRODUCT_HEURISTIC", product_note="Angka operasional mempertahankan keputusan produk existing dan tidak diklaim sebagai cut-off klinis WHO."),
    _rule("mpasi_meal_frequency_9_11_non_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 4, 4, "meals_per_day", "SEHATIN menggunakan konteks non-breastfed untuk memilih target operasional yang sudah dipakai Nutrition Engine.", "who_cf_2023", priority=9, age_min=9, age_max=11, age_band="9–11", feeding_context=("formula", "other"), rule_kind="PRODUCT_HEURISTIC", product_note="Angka operasional mempertahankan keputusan produk existing dan tidak diklaim sebagai cut-off klinis WHO."),
    _rule("mpasi_meal_frequency_12_23_non_bf", "mpasi", "meal_frequency", "meal_frequency", "<", 4, 4, "meals_per_day", "SEHATIN menggunakan konteks non-breastfed untuk memilih target operasional yang sudah dipakai Nutrition Engine.", "who_cf_2023", priority=9, age_min=12, age_max=23, age_band="12–23", feeding_context=("formula", "other"), rule_kind="PRODUCT_HEURISTIC", product_note="Angka operasional mempertahankan keputusan produk existing dan tidak diklaim sebagai cut-off klinis WHO."),
    _rule("mpasi_meal_frequency_6_8_generic", "mpasi", "meal_frequency", "meal_frequency", "<", 2, 2, "meals_per_day", "Fallback usia 6–8 bulan bila feeding context tidak memiliki rule yang lebih spesifik.", "who_cf_2023", priority=30, age_min=6, age_max=8, age_band="6–8"),
    _rule("mpasi_meal_frequency_9_11_generic", "mpasi", "meal_frequency", "meal_frequency", "<", 3, 3, "meals_per_day", "Fallback usia 9–11 bulan bila feeding context tidak memiliki rule yang lebih spesifik.", "who_cf_2023", priority=30, age_min=9, age_max=11, age_band="9–11"),
    _rule("mpasi_meal_frequency_12_23_generic", "mpasi", "meal_frequency", "meal_frequency", "<", 3, 3, "meals_per_day", "Fallback usia 12–23 bulan bila feeding context tidak memiliki rule yang lebih spesifik.", "who_cf_2023", priority=30, age_min=12, age_max=23, age_band="12–23"),
    _rule("mpasi_dietary_diversity_5_of_8", "mpasi", "dietary_diversity", "food_group_count", "<", 5, 5, "food_groups", "Indikator keragaman pangan digunakan untuk menilai praktik pemberian makan, bukan status gizi atau diagnosis.", "who_mdd", priority=20, age_min=6, age_max=23),
    _rule("mpasi_responsive_feeding", "mpasi", "responsive_feeding", "responsive_feeding", "in", ("rarely", "sometimes"), "usually", "feeding_practice", "Responsive feeding menekankan respons terhadap tanda lapar/kenyang dan menghindari paksaan makan.", "who_responsive", priority=25, age_min=6, age_max=23),
    _rule("mpasi_texture_progression", "mpasi", "texture", "texture_concern", "==", True, "progressive_age_appropriate", "feeding_practice", "Tekstur ditingkatkan bertahap sesuai kemampuan makan anak; output ini adalah panduan feeding, bukan diagnosis perkembangan.", "who_responsive", priority=15, age_min=6, age_max=23),
    _rule("mpasi_animal_source_food_opportunity", "mpasi", "animal_source_food", "protein_exposure", "<=", 0, 1, "behavioral_opportunity", "SEHATIN memprioritaskan satu target terukur untuk membuka kesempatan pangan hewani sebagai bagian pola makan beragam.", "animal_source_foods_review", priority=40, age_min=6, age_max=23, rule_kind="PRODUCT_HEURISTIC", product_note="Jumlah kesempatan adalah operational target SEHATIN; sumber mendukung relevansi pangan hewani, bukan angka harian universal."),
    _rule("mpasi_fruit_vegetable_opportunity", "mpasi", "fruit_vegetable", "fruit_vegetable_exposure", "<=", 0, 1, "behavioral_opportunity", "SEHATIN mengubah gap paparan menjadi satu target perilaku yang dapat diamati tanpa mewajibkan anak menghabiskan makanan.", "who_cf_2023", priority=45, age_min=6, age_max=23, rule_kind="PRODUCT_HEURISTIC", product_note="Satu kesempatan adalah simplifikasi target produk, bukan cut-off klinis."),
    _rule("mpasi_feeding_difficulty_observation", "mpasi", "food_response", "feeding_difficulty", "==", "significant", "review_feeding_context", "feeding_practice", "Kesulitan makan yang sering menghambat proses makan diprioritaskan sebagai konteks feeding yang perlu ditinjau, tanpa membuat diagnosis.", "who_responsive", priority=5, age_min=6, age_max=23, rule_kind="PRODUCT_HEURISTIC", product_note="Stage 4 hanya menandai kebutuhan review feeding context; tidak memberi diagnosis atau terapi."),
    _rule("mpasi_food_rejection_observation", "mpasi", "food_response", "food_rejection", "==", "frequent", "observe_without_pressure", "feeding_practice", "Penolakan makanan diperlakukan sebagai feeding behavior; fokus pada paparan tanpa paksaan dan pencatatan respons.", "who_responsive", priority=35, age_min=6, age_max=23),

    # Toddler habit-oriented rules.
    _rule("toddler_meal_routine", "toddler", "meal_routine", "meal_routine", "in", ("irregular", "mixed"), "regular", "meal_routine", "Rutinitas makan diposisikan sebagai healthy-eating habit, bukan target medis.", "toddler_meal_evidence", priority=15, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Label regular adalah operational target SEHATIN; evidence mendukung structured healthy-eating practice."),
    _rule("toddler_sweetened_beverage", "toddler", "sweet_beverage", "sweetened_beverage", "==", True, False, "exposure", "Target menurunkan paparan minuman berpemanis sebagai kebiasaan yang dapat diamati.", "toddler_ssb_review", priority=10, age_min=24, age_max=59),
    _rule("toddler_food_variety_exposure", "toddler", "vegetable_fruit_exposure", "fruit_vegetable_exposure", "<=", 0, 1, "behavioral_opportunity", "Repeated offering digunakan sebagai strategi perilaku untuk membangun penerimaan makanan tanpa paksaan.", "toddler_veg_review", priority=30, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Satu kesempatan adalah target produk agar dapat diukur; evidence mendukung repeated offering, bukan angka harian universal."),
    _rule("toddler_self_feeding", "toddler", "self_feeding", "self_feeding", "==", False, True, "feeding_practice", "Kesempatan makan mandiri dipantau sebagai kebiasaan yang dapat diamati sesuai kemampuan anak.", "caregiver_feeding_review", priority=40, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Boolean opportunity adalah operational target SEHATIN."),
    _rule("toddler_pressure_to_eat", "toddler", "responsive_feeding", "pressure_to_eat", "==", True, False, "feeding_practice", "Fokus diarahkan pada pengurangan tekanan saat makan dan respons terhadap tanda lapar/kenyang.", "caregiver_feeding_review", priority=10, age_min=24, age_max=59),
    _rule("toddler_distraction_during_meals", "toddler", "responsive_feeding", "meal_distraction", "==", True, False, "meal_distraction", "Mengurangi distraksi membantu caregiver mengamati proses makan dan tanda lapar/kenyang dengan lebih baik.", "caregiver_feeding_review", priority=20, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Prioritas distraksi adalah keputusan produk berbasis konteks feeding behavior."),
    _rule("toddler_protein_presence", "toddler", "protein_presence", "protein_exposure", "<=", 0, 1, "behavioral_opportunity", "Sumber protein dipakai sebagai bagian pola makan beragam; SEHATIN mengubah gap menjadi target yang dapat diamati.", "animal_source_foods_review", priority=45, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Satu kesempatan adalah target produk, bukan recommendation klinis universal."),
    _rule("toddler_feeding_difficulty_observation", "toddler", "food_response", "feeding_difficulty", "==", "significant", "review_feeding_context", "feeding_practice", "Kesulitan makan yang sering menghambat rutinitas diperlakukan sebagai feeding context yang perlu ditinjau, bukan diagnosis medis.", "caregiver_feeding_review", priority=5, age_min=24, age_max=59, rule_kind="PRODUCT_HEURISTIC", product_note="Stage 4 hanya menandai review feeding context dan tidak menentukan kondisi medis."),
    _rule("toddler_food_rejection", "toddler", "food_response", "food_rejection", "==", "frequent", "observe_without_pressure", "feeding_practice", "Penolakan makanan ditangani sebagai feeding behavior melalui paparan bertahap tanpa klaim diagnosis.", "toddler_veg_review", priority=25, age_min=24, age_max=59),
)


def _stage4_baseline_value(baseline: dict[str, Any], key: str) -> Any:
    row = baseline.get(key)
    return row.get("value") if isinstance(row, dict) else row


def _compare(value: Any, comparator: str, expected: Any) -> bool:
    try:
        if comparator == "<":
            return value is not None and float(value) < float(expected)
        if comparator == "<=":
            return value is not None and float(value) <= float(expected)
        if comparator == ">":
            return value is not None and float(value) > float(expected)
        if comparator == ">=":
            return value is not None and float(value) >= float(expected)
    except (TypeError, ValueError):
        return False
    if comparator == "==":
        return value == expected
    if comparator == "!=":
        return value != expected
    if comparator == "in":
        return value in expected
    if comparator == "not_in":
        return value not in expected
    return False


def _rule_specificity(rule: EvidenceRuleDefinition, metric_rank: int) -> tuple[int, int, int, int, str]:
    # Smaller tuple sorts first: context + age-band specificity beat generic,
    # followed by the requested metric order and explicit priority.
    context_penalty = 0 if rule.feeding_context else 1
    age_band_penalty = 0 if rule.age_band else 1
    age_range_width = (rule.age_max - rule.age_min) if rule.age_min is not None and rule.age_max is not None else 999
    return (context_penalty, age_band_penalty, metric_rank, rule.priority + age_range_width, rule.id)


def _serialize_evidence_rule(rule: EvidenceRuleDefinition, *, baseline_value: Any) -> dict[str, Any]:
    source = _stage4_source(rule.source_key, rule.rule_kind)
    return {
        "rule_id": rule.id,
        "category": rule.category,
        "age_min": rule.age_min,
        "age_max": rule.age_max,
        "age_band": rule.age_band,
        "feeding_context": list(rule.feeding_context),
        "metric": rule.metric,
        "condition": f"{rule.baseline_key} {rule.comparator} {rule.condition_value!r}",
        "comparator": rule.comparator,
        "condition_value": rule.condition_value,
        "baseline_key": rule.baseline_key,
        "baseline_value": baseline_value,
        "target_value": rule.target_value,
        "target_unit": rule.target_unit,
        "rationale": rule.rationale,
        "priority": rule.priority,
        "rule_kind": rule.rule_kind,
        "product_note": rule.product_note,
        "status": rule.status,
        "evidence": source,
        "source": source,
    }


def _target_from_stage4_rule(rule_payload: dict[str, Any], baseline_value: Any, priority: int) -> dict[str, Any]:
    evidence = dict(rule_payload["evidence"])
    return {
        "id": f"stage4_{rule_payload['rule_id']}",
        "metric": rule_payload["metric"],
        "baseline": baseline_value,
        "target": rule_payload["target_value"],
        "unit": rule_payload["target_unit"],
        "priority": priority,
        "rationale": rule_payload["rationale"],
        "label": str(rule_payload["metric"]).replace("_", " ").title(),
        "interpretation": f"Baseline {rule_payload['baseline_key']} memenuhi kondisi rule {rule_payload['condition']}.",
        "evidence_rule_id": rule_payload["rule_id"],
        "evidence": evidence,
        "rule_kind": rule_payload["rule_kind"],
    }


def evaluate_evidence_rules(
    *,
    category: str,
    profile: dict[str, Any],
    baseline: dict[str, Any],
    primary_gap: dict[str, Any] | None,
    support_gaps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Pure deterministic Stage 4 matcher.

    The matcher consumes Stage 3 output and never rebuilds the profile/baseline.
    It returns an explicit fallback instead of inventing a recommendation when no
    evidence rule matches.
    """
    if category not in {"mpasi", "toddler"}:
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Belum ada Evidence Rule Stage 4 untuk kategori ini.",
            "evidence_available": False,
            "matched_rules": [],
            "unmatched_metrics": [],
            "targets": [],
            "primary_target": None,
            "support_targets": [],
            "engine_version": RULE_VERSION,
        }

    age_months = int(profile.get("age_months") or _stage4_baseline_value(baseline, "age_months") or 0)
    if category == "mpasi" and not 6 <= age_months <= 23:
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Usia berada di luar product boundary MPASI 6–23 bulan.",
            "evidence_available": False,
            "matched_rules": [],
            "unmatched_metrics": [str((primary_gap or {}).get("metric") or "")],
            "targets": [],
            "primary_target": None,
            "support_targets": [],
            "engine_version": RULE_VERSION,
        }
    if category == "toddler" and not 24 <= age_months <= 59:
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Usia berada di luar product boundary Toddler 24–59 bulan.",
            "evidence_available": False,
            "matched_rules": [],
            "unmatched_metrics": [str((primary_gap or {}).get("metric") or "")],
            "targets": [],
            "primary_target": None,
            "support_targets": [],
            "engine_version": RULE_VERSION,
        }

    age_band = mpasi_band(age_months) if category == "mpasi" else "24–59"
    feeding_context = str(profile.get("feeding_mode") or _stage4_baseline_value(baseline, "feeding_context") or "")
    gap_rows = [row for row in [primary_gap, *(support_gaps or [])] if row]
    metrics: list[str] = []
    for row in gap_rows:
        metric = str(row.get("metric") or "")
        if metric and metric not in metrics:
            metrics.append(metric)

    matched_rules: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for metric_rank, metric in enumerate(metrics):
        candidates: list[tuple[EvidenceRuleDefinition, Any]] = []
        for rule in EVIDENCE_RULES:
            if rule.status != "ACTIVE" or rule.category != category or rule.metric != metric:
                continue
            if rule.age_min is not None and age_months < rule.age_min:
                continue
            if rule.age_max is not None and age_months > rule.age_max:
                continue
            if rule.age_band and rule.age_band != age_band:
                continue
            if rule.feeding_context and feeding_context not in rule.feeding_context:
                continue
            baseline_value = _stage4_baseline_value(baseline, rule.baseline_key)
            if not _compare(baseline_value, rule.comparator, rule.condition_value):
                continue
            candidates.append((rule, baseline_value))

        if not candidates:
            unmatched.append(metric)
            continue
        candidates.sort(key=lambda item: _rule_specificity(item[0], metric_rank))
        selected, baseline_value = candidates[0]
        payload = _serialize_evidence_rule(selected, baseline_value=baseline_value)
        matched_rules.append(payload)
        targets.append(_target_from_stage4_rule(payload, baseline_value, len(targets) + 1))

    primary_metric = str((primary_gap or {}).get("metric") or "")
    primary_target = next((target for target in targets if target["metric"] == primary_metric), None)
    support_targets = [target for target in targets if target is not primary_target][:4]
    if not matched_rules:
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Belum ada panduan terstruktur untuk kombinasi data ini.",
            "evidence_available": False,
            "matched_rules": [],
            "unmatched_metrics": unmatched or metrics,
            "targets": [],
            "primary_target": None,
            "support_targets": [],
            "engine_version": RULE_VERSION,
        }
    return {
        "status": "MATCHED",
        "message": "Evidence Rule Stage 4 berhasil dicocokkan secara deterministik.",
        "evidence_available": True,
        "matched_rules": matched_rules,
        "unmatched_metrics": unmatched,
        "targets": targets,
        "primary_target": primary_target,
        "support_targets": support_targets,
        "engine_version": RULE_VERSION,
        "age_band": age_band,
        "feeding_context": feeding_context or None,
    }


@dataclass(frozen=True)
class TaskSpec:
    key: str
    id: str
    metric: str
    metric_id: str
    input_type: str
    target_value: float | str | bool | None
    unit: str
    target_label: str
    action: str
    action_text: str
    result_prompt: str
    when: str
    why: str
    mode: str
    evidence: list[str]
    evidence_rule: dict[str, Any] | None
    success_criteria: str
    priority: int
    day_applicability: str
    current_result: Any
    status: str
    options: list[dict[str, str]]
    adherence_map: dict[str, float]


def _task(metric: str, spec: dict[str, Any], day_number: int, stage: str, priority: int) -> TaskSpec:
    key = f"{metric}_d{day_number}"
    if spec["input_type"] == "count":
        success = f"Target tercapai bila hasil minimal {float(spec['target_value']):.0f} {spec['unit']}."
    elif spec["input_type"] == "boolean":
        expected = bool(spec.get("target_value"))
        success = f"Target tercapai bila hasil {'Ya' if expected else 'Tidak'} sesuai definisi metric."
    else:
        success = "Status hasil mengikuti mapping observasi pada rule/config program; bukan skor medis."
    return TaskSpec(
        key=key,
        id=key,
        metric=metric,
        metric_id=metric,
        input_type=spec["input_type"],
        target_value=spec.get("target_value"),
        unit=spec.get("unit", ""),
        target_label=spec["target_label"],
        action=spec.get("action") or spec["target_label"],
        action_text=spec.get("action") or spec["target_label"],
        result_prompt=spec.get("result_prompt") or "Catat hasil aktual hari ini.",
        when="Hari ini, sebelum menekan Simpan progress.",
        why=spec["why"],
        mode=str((spec.get("evidence_rule") or {}).get("rule_kind") or "behavioral_target"),
        evidence=spec["evidence"],
        evidence_rule=spec.get("evidence_rule"),
        success_criteria=success,
        priority=priority,
        day_applicability=f"day_{day_number}",
        current_result=None,
        status="NOT_RECORDED",
        options=spec.get("options", []),
        adherence_map=spec.get("adherence_map", {}),
    )


BASELINE_ACTIONS: dict[str, str] = {
    "meal_frequency": "Catat jumlah makan pendamping yang benar-benar berlangsung hari ini.",
    "animal_source_food": "Catat berapa kesempatan sumber pangan hewani benar-benar ditawarkan hari ini.",
    "fruit_vegetable": "Catat berapa kesempatan sayur atau buah benar-benar ditawarkan hari ini.",
    "dietary_diversity": "Catat jumlah kelompok pangan berbeda yang benar-benar dikonsumsi hari ini.",
    "responsive_feeding": "Catat apakah tanda lapar/kenyang diikuti tanpa memaksa hari ini.",
    "texture": "Catat apakah tekstur yang diberikan sesuai kemampuan anak hari ini.",
    "meal_routine": "Catat berapa waktu makan utama yang benar-benar berlangsung hari ini.",
    "sweet_beverage": "Catat apakah minuman berpemanis ditawarkan hari ini.",
    "vegetable_fruit_exposure": "Catat berapa kesempatan sayur atau buah benar-benar ditawarkan hari ini.",
    "self_feeding": "Catat berapa kesempatan makan mandiri yang benar-benar diberikan hari ini.",
    "protein_presence": "Catat pada berapa makan utama sumber protein benar-benar tersedia hari ini.",
    "food_response": "Catat respons anak pada satu paparan makanan fokus hari ini.",
}


def _baseline_task(task: dict[str, Any]) -> dict[str, Any]:
    metric = str(task.get("metric") or "")
    action = BASELINE_ACTIONS.get(metric)
    if not action:
        return task
    return {
        **task,
        "action": action,
        "action_text": action,
        "mode": "baseline_observation",
        "day_applicability": "day_1_baseline",
        "status": "NOT_RECORDED",
    }


def _legacy_build_personalized_tasks(
    stage: str,
    profile: dict[str, Any],
    day_number: int,
    primary_metric: str | None = None,
) -> list[dict[str, Any]]:
    """Pre-Stage-5 task builder retained only for backward compatibility.

    Existing/adaptive program paths that do not carry a Stage 3/4 snapshot can
    still render their historical task contract. New program creation should
    use :func:`generate_personalized_daily_todos` through the public wrapper
    below.
    """
    if stage == "elderly":
        return []
    primary = primary_metric or (preferred_mpasi_metric(profile) if stage == "mpasi" else preferred_toddler_metric(profile))
    if stage == "mpasi":
        secondary = {
            "meal_frequency": "animal_source_food",
            "animal_source_food": "fruit_vegetable",
            "fruit_vegetable": "dietary_diversity",
            "dietary_diversity": "responsive_feeding",
            "responsive_feeding": "texture",
            "texture": "dietary_diversity",
            "food_response": "responsive_feeding",
        }.get(primary, "animal_source_food")
        tertiary = {
            "meal_frequency": "responsive_feeding",
            "animal_source_food": "responsive_feeding",
            "fruit_vegetable": "animal_source_food",
            "dietary_diversity": "animal_source_food",
            "responsive_feeding": "animal_source_food",
            "texture": "responsive_feeding",
            "food_response": "animal_source_food",
        }.get(primary, "responsive_feeding")
        baseline_candidates = ["meal_frequency", primary, "food_response", secondary, tertiary]
    else:
        secondary = {
            "meal_routine": "vegetable_fruit_exposure",
            "sweet_beverage": "vegetable_fruit_exposure",
            "vegetable_fruit_exposure": "responsive_feeding",
            "responsive_feeding": "self_feeding",
            "self_feeding": "protein_presence",
            "protein_presence": "vegetable_fruit_exposure",
            "food_response": "vegetable_fruit_exposure",
        }.get(primary, "vegetable_fruit_exposure")
        tertiary = {
            "meal_routine": "responsive_feeding",
            "sweet_beverage": "responsive_feeding",
            "vegetable_fruit_exposure": "self_feeding",
            "responsive_feeding": "protein_presence",
            "self_feeding": "vegetable_fruit_exposure",
            "protein_presence": "responsive_feeding",
            "food_response": "responsive_feeding",
        }.get(primary, "responsive_feeding")
        baseline_candidates = ["meal_routine", primary, "food_response", secondary, tertiary]

    candidates = baseline_candidates if day_number == 1 else [primary, secondary, tertiary]
    metrics: list[str] = []
    for metric in candidates:
        if metric not in metrics:
            metrics.append(metric)
        if len(metrics) >= 3:
            break

    tasks: list[dict[str, Any]] = []
    for priority, metric in enumerate(metrics, start=1):
        spec = target_for_metric(stage, metric, profile)
        task = _task(metric, spec, day_number, stage, priority).__dict__
        tasks.append(_baseline_task(task) if day_number == 1 else task)
    return tasks


def _stage5_rule_payload(rule: dict[str, Any]) -> dict[str, Any]:
    source = dict(rule.get("evidence") or rule.get("source") or {})
    return {
        "rule_id": rule.get("rule_id"),
        "category": rule.get("category"),
        "age_range": rule.get("age_band") or (
            f"{rule.get('age_min')}–{rule.get('age_max')} months"
            if rule.get("age_min") is not None and rule.get("age_max") is not None
            else None
        ),
        "metric": rule.get("metric"),
        "threshold_or_target": rule.get("target_value"),
        "target_unit": rule.get("target_unit"),
        "description": rule.get("rationale"),
        "source_name": source.get("source_name"),
        "source_type": source.get("source_type"),
        "source_url": source.get("source_url"),
        "evidence_level": source.get("evidence_level"),
        "last_reviewed": source.get("last_reviewed"),
        "notes": rule.get("product_note"),
        "rule_kind": rule.get("rule_kind"),
    }


def _stage5_task_from_target(
    *,
    stage: str,
    profile: dict[str, Any],
    day_number: int,
    target: dict[str, Any],
    rule: dict[str, Any],
    priority: int,
    baseline: dict[str, Any],
    gap: dict[str, Any] | None,
) -> dict[str, Any]:
    metric = str(target.get("metric") or rule.get("metric") or "")
    spec = dict(target_for_metric(stage, metric, profile))
    stage4_target = target.get("target")
    stage4_unit = target.get("unit") or rule.get("target_unit")

    # Preserve the existing measurable input contract. When Stage 4 exposes a
    # directly compatible numeric/boolean target, use it verbatim. Qualitative
    # evidence targets (for example `regular` or `usually`) are operationalised
    # through the existing task config and labelled as such rather than being
    # presented as a guideline numeric cut-off.
    direct_target = False
    if spec.get("input_type") == "count" and isinstance(stage4_target, (int, float)) and not isinstance(stage4_target, bool):
        spec["target_value"] = stage4_target
        if stage4_unit:
            spec["unit"] = stage4_unit
        direct_target = True
    elif spec.get("input_type") == "boolean" and isinstance(stage4_target, bool):
        spec["target_value"] = stage4_target
        if stage4_unit:
            spec["unit"] = stage4_unit
        direct_target = True

    rule_payload = _stage5_rule_payload(rule)
    source_url = rule_payload.get("source_url")
    source_name = rule_payload.get("source_name")
    spec["evidence_rule"] = rule_payload
    spec["evidence"] = [f"{source_name} — {source_url}"] if source_name and source_url else []
    spec["why"] = str(target.get("rationale") or rule.get("rationale") or spec.get("why") or "")

    task = _task(metric, spec, day_number, stage, priority).__dict__
    baseline_row = baseline.get(str(rule.get("baseline_key") or metric))
    baseline_value = baseline_row.get("value") if isinstance(baseline_row, dict) else baseline_row
    evidence_rule_id = str(target.get("evidence_rule_id") or rule.get("rule_id") or "") or None
    return {
        **task,
        "result": None,
        "current_result": None,
        "status": "NOT_STARTED",
        "evidence_rule_id": evidence_rule_id,
        "baseline": baseline_value,
        "target_origin": "EVIDENCE_RULE" if direct_target else "PRODUCT_OPERATIONALIZATION",
        "stage4_target": stage4_target,
        "stage4_target_unit": stage4_unit,
        "personalization_trace": {
            "baseline": baseline_value,
            "gap_id": (gap or {}).get("id"),
            "gap_metric": (gap or {}).get("metric"),
            "target_id": target.get("id"),
            "evidence_rule_id": evidence_rule_id,
        },
        "stage5_engine_version": STAGE5_RULE_VERSION,
    }


def generate_personalized_daily_todos(
    *,
    stage: str,
    profile: dict[str, Any],
    day_number: int,
    baseline: dict[str, Any],
    primary_gap: dict[str, Any] | None,
    primary_target: dict[str, Any] | None,
    support_targets: list[dict[str, Any]] | None,
    evidence_rule_evaluation: dict[str, Any] | None,
    primary_metric: str | None = None,
) -> dict[str, Any]:
    """Generate Stage 5 To Do from Stage 3 + Stage 4 output.

    This is a pure deterministic transformation. It never calculates actual
    result/adherence and never invents a target when Stage 4 has no matching
    evidence rule.
    """
    if stage not in {"mpasi", "toddler"}:
        return {
            "status": "NOT_APPLICABLE",
            "message": "Stage 5 Personalized Daily To Do hanya diterapkan pada MPASI/Toddler dalam scope ini.",
            "tasks": [],
            "engine_version": STAGE5_RULE_VERSION,
        }

    stage4 = evidence_rule_evaluation or {}
    if stage4.get("status") != "MATCHED":
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Target belum tersedia karena tidak ada Evidence Rule Stage 4 yang cocok.",
            "tasks": [],
            "engine_version": STAGE5_RULE_VERSION,
        }

    rules_by_id = {str(row.get("rule_id")): row for row in (stage4.get("matched_rules") or []) if row.get("rule_id")}
    stage4_targets = [row for row in (stage4.get("targets") or []) if row and row.get("evidence_rule_id")]
    stage4_primary = stage4.get("primary_target") or None

    # Stage 7 may already request an adaptive primary metric. Reorder only when
    # that metric already has a Stage 4 evidence target; otherwise the caller can
    # use the legacy/adaptive compatibility path rather than fabricating a rule.
    requested_primary = primary_metric or str((stage4_primary or {}).get("metric") or (primary_target or {}).get("metric") or "")
    selected_primary = next((row for row in stage4_targets if str(row.get("metric")) == requested_primary), None)
    if selected_primary is None:
        selected_primary = stage4_primary if stage4_primary and stage4_primary.get("evidence_rule_id") else None
    if selected_primary is None:
        return {
            "status": "NO_MATCHING_RULE",
            "message": "Target utama belum memiliki Evidence Rule Stage 4; To Do tidak difabrikasi.",
            "tasks": [],
            "engine_version": STAGE5_RULE_VERSION,
        }

    ordered_targets: list[dict[str, Any]] = [selected_primary]
    for candidate in [*(stage4.get("support_targets") or []), *stage4_targets]:
        if not candidate or candidate is selected_primary:
            continue
        metric = str(candidate.get("metric") or "")
        if metric and all(str(row.get("metric") or "") != metric for row in ordered_targets):
            ordered_targets.append(candidate)
        if len(ordered_targets) >= 5:
            break

    gap_by_metric = {str((primary_gap or {}).get("metric") or ""): primary_gap}
    # Stage 3 support target objects do not contain gap IDs, but retaining target
    # identity is enough for traceability; where no gap object exists the field
    # remains null rather than being invented.
    stage3_targets = [row for row in [primary_target, *(support_targets or [])] if row]
    stage3_target_by_metric = {str(row.get("metric") or ""): row for row in stage3_targets}

    tasks: list[dict[str, Any]] = []
    for priority, target in enumerate(ordered_targets, start=1):
        rule_id = str(target.get("evidence_rule_id") or "")
        rule = rules_by_id.get(rule_id)
        if not rule:
            continue
        metric = str(target.get("metric") or "")
        stage3_target = stage3_target_by_metric.get(metric) or target
        tasks.append(_stage5_task_from_target(
            stage=stage,
            profile=profile,
            day_number=day_number,
            target={**target, "id": stage3_target.get("id") or target.get("id")},
            rule=rule,
            priority=priority,
            baseline=baseline,
            gap=gap_by_metric.get(metric),
        ))

    return {
        "status": "READY" if tasks else "NO_MATCHING_RULE",
        "message": "Personalized Daily To Do dibentuk dari Stage 3 + Stage 4." if tasks else "Target belum tersedia.",
        "tasks": tasks,
        "engine_version": STAGE5_RULE_VERSION,
        "primary_metric": str(tasks[0].get("metric") or "") if tasks else None,
    }


def build_personalized_tasks(
    stage: str,
    profile: dict[str, Any],
    day_number: int,
    primary_metric: str | None = None,
    *,
    personalization: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Public task builder used by the existing Program API.

    With a recommendation snapshot it executes Stage 5. Without one it retains
    the historical task contract for backward compatibility with existing
    programs/tests.
    """
    if personalization and stage in {"mpasi", "toddler"}:
        # Snapshot lama (sebelum Stage 4) tidak memiliki evidence evaluation.
        # Pertahankan kontrak task lama agar existing program tetap dapat dibuka.
        if "evidence_rule_evaluation" not in personalization:
            return _legacy_build_personalized_tasks(stage, profile, day_number, primary_metric)
        stage5 = generate_personalized_daily_todos(
            stage=stage,
            profile=profile,
            day_number=day_number,
            baseline=dict(personalization.get("baseline") or {}),
            primary_gap=personalization.get("primary_gap"),
            primary_target=personalization.get("primary_target"),
            support_targets=list(personalization.get("support_targets") or []),
            evidence_rule_evaluation=dict(personalization.get("evidence_rule_evaluation") or {}),
            primary_metric=primary_metric,
        )
        if stage5["tasks"]:
            return list(stage5["tasks"])
        # Existing Program API historically guaranteed actionable days even for
        # sparse/legacy assessment snapshots. Keep that compatibility contract
        # here, while the pure Stage 5 engine above still returns an explicit
        # NO_MATCHING_RULE and never fabricates an evidence-backed target.
        return _legacy_build_personalized_tasks(stage, profile, day_number, primary_metric)
    return _legacy_build_personalized_tasks(stage, profile, day_number, primary_metric)


def adherence_for_task(task: dict[str, Any], result: Any, checked: bool) -> float:
    input_type = task.get("input_type")
    if input_type == "count":
        try:
            target = float(task.get("target_value") or 0)
            value = max(0.0, float(result or 0))
            return min(100.0, round((value / target) * 100, 1)) if target else (100.0 if value == 0 else 0.0)
        except (TypeError, ValueError):
            return 0.0
    if input_type == "boolean":
        if result is None:
            return 0.0
        expected = bool(task.get("target_value"))
        return 100.0 if bool(result) == expected else 0.0
    if input_type in {"choice", "rating", "observation"}:
        if result is None:
            return 0.0
        mapping = task.get("adherence_map") or {}
        try:
            return max(0.0, min(100.0, float(mapping.get(str(result), 0.0))))
        except (TypeError, ValueError):
            return 0.0
    return 100.0 if checked else 0.0


def task_met(task: dict[str, Any], result: Any, checked: bool) -> bool:
    return adherence_for_task(task, result, checked) >= 100.0


def task_result_status(task: dict[str, Any], result: Any, checked: bool) -> str:
    if result is None or result == "":
        return "NOT_RECORDED"
    adherence = adherence_for_task(task, result, checked)
    if adherence >= 100:
        return "ACHIEVED"
    if adherence > 0:
        return "PARTIAL"
    return "NOT_ACHIEVED"


def behavioral_status(adherence: float) -> str:
    """SEHATIN behavioral-program heuristic, explicitly not a clinical cut-off."""
    if adherence >= 80:
        return "TERCAPAI_KONSISTEN"
    if adherence >= 50:
        return "SEBAGIAN_TERCAPAI"
    return "PERLU_DILANJUTKAN"


def adaptation_for_days(
    stage: str,
    recent_days: list[dict[str, Any]],
    profile: dict[str, Any],
    current_primary: str,
) -> dict[str, Any]:
    """Adaptive pacing after >=3 *saved primary-target observations*.

    <50 / 50–79 / >=80 are SEHATIN product heuristics, never WHO/Kemenkes
    clinical cut-offs. Historical results are inputs only and are never mutated.
    """
    samples = [row for row in recent_days if row]
    observations: list[float] = []
    for row in samples[-3:]:
        for task in row.get("tasks", []):
            if task.get("metric") != current_primary:
                continue
            key = task.get("key")
            if key not in (row.get("task_adherence") or {}):
                continue
            observations.append(float(row["task_adherence"][key]))
            break
    if len(observations) < 3:
        return {
            "decision": "WAIT",
            "reason": "Belum ada 3 hasil primary target yang benar-benar tersimpan.",
            "next_primary_metric": current_primary,
            "rule_version": RULE_VERSION,
            "saved_primary_observations": len(observations),
        }

    average = round(sum(observations[-3:]) / 3, 1)
    progression = {
        "mpasi": ["meal_frequency", "animal_source_food", "fruit_vegetable", "dietary_diversity", "responsive_feeding", "texture", "food_response"],
        "toddler": ["meal_routine", "sweet_beverage", "vegetable_fruit_exposure", "responsive_feeding", "self_feeding", "protein_presence", "food_response"],
    }.get(stage, [current_primary])
    try:
        idx = progression.index(current_primary)
    except ValueError:
        idx = 0

    if average < 50:
        return {
            "decision": "REINFORCE",
            "average_adherence": average,
            "reason": "Pencapaian primary target masih rendah; fokus dipertahankan dan dukungan disederhanakan tanpa menurunkan target evidence-based.",
            "next_primary_metric": current_primary,
            "rule_version": RULE_VERSION,
            "heuristic": "<50% = REINFORCE (SEHATIN product heuristic)",
        }
    if average >= 80:
        next_metric = progression[min(idx + 1, len(progression) - 1)]
        return {
            "decision": "ADVANCE",
            "average_adherence": average,
            "reason": "Primary target cukup konsisten; fokus berikutnya dapat berpindah ke priority berikutnya. Target baru tetap berasal dari rule/config.",
            "next_primary_metric": next_metric,
            "rule_version": RULE_VERSION,
            "heuristic": ">=80% = ADVANCE (SEHATIN product heuristic)",
        }
    return {
        "decision": "MAINTAIN",
        "average_adherence": average,
        "reason": "Primary target belum cukup konsisten untuk berpindah fokus; pertahankan target dan action.",
        "next_primary_metric": current_primary,
        "rule_version": RULE_VERSION,
        "heuristic": "50–79% = MAINTAIN (SEHATIN product heuristic)",
    }
