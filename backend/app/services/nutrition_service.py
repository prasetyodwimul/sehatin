from app.nutrition.calculator import age_band_label, calculate_estimated_needs, meal_pattern
from app.nutrition.profile_baseline import build_stage3_profile
from app.nutrition.elderly_condition_context import build_elderly_health_context
from app.nutrition.elderly_lifestyle_context import build_elderly_lifestyle_context
from app.nutrition.elderly_goal_context import build_elderly_program_goal
from app.nutrition.program_evidence import evaluate_evidence_rules
from app.nutrition.recommendations import food_groups, priority_nutrients, recommendations, sample_menu
from app.nutrition.references import public_reference_labels
from app.nutrition.rules import build_input_summary, build_safety_notes, personalization_is_limited
from app.schemas.nutrition import NutritionRequest, NutritionResponse
from app.nutrition_validation import validate_anthropometrics


CATEGORY_LABELS = {
    "mpasi": "MPASI 6–23 bulan",
    "toddler": "Nutrisi anak 24–59 bulan",
    "elderly": "Nutrisi lansia 60+ tahun",
}


def suggested_goals(req: NutritionRequest, stage3: dict | None = None, stage4: dict | None = None) -> list[dict]:
    """Backward-compatible Guided Program candidates sourced from Stage 3.

    Stage 3 only identifies candidate metrics. The 14-day successful-day goal is
    retained here because it is an existing Stage 4+ program contract, not a new
    daily plan created by Stage 3.
    """
    if req.stage == "elderly":
        health_context = build_elderly_health_context(req)
        lifestyle_context = build_elderly_lifestyle_context(req)
        return [build_elderly_program_goal(
            req.model_dump(mode="json"),
            health_context=health_context,
            lifestyle_context=lifestyle_context,
            duration_days=14,
        )]

    stage3 = stage3 or build_stage3_profile(req)
    stage4 = stage4 or {}
    evidence_targets = list(stage4.get("targets") or [])
    candidates = evidence_targets or [stage3.get("primary_target"), *(stage3.get("support_targets") or [])]
    goals: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        metric = str(candidate.get("metric") or "")
        if not metric or metric in seen:
            continue
        seen.add(metric)
        goals.append({
            "goal_key": metric,
            "title": str(candidate.get("label") or metric.replace("_", " ").title()),
            "description": str(candidate.get("rationale") or "Goal dipilih dari profile dan baseline assessment."),
            "baseline": 0,
            "target": 10,
            "unit": "successful target days",
            "measurement_method": f"daily metric adherence for {metric}",
            "duration": 14,
            "priority": len(goals) + 1,
            "status": "NOT_STARTED",
        })
        if len(goals) >= 3:
            break
    return goals


def generate_nutrition_recommendation(req: NutritionRequest, validation: dict | None = None) -> NutritionResponse:
    validation = validation or validate_anthropometrics(
        stage=req.stage, age_months=req.age_months, age_years=req.age_years, sex=req.sex, weight_kg=req.weight_kg, height_cm=req.height_cm
    )
    limited = personalization_is_limited(req)
    if limited:
        summary = (
            "Data berhasil divalidasi, tetapi personalisasi dibatasi karena terdapat kondisi yang dapat memerlukan penilaian klinis. "
            "Hasil hanya berisi informasi umum dan rekomendasi edukatif yang lebih aman."
        )
    else:
        summary = (
            "Estimasi dan rekomendasi edukatif dipilih berdasarkan kelompok usia, pola makan, alergi/batasan yang dimasukkan, "
            "serta referensi kebutuhan gizi populasi yang sesuai."
        )

    stage3 = build_stage3_profile(req)
    stage4 = evaluate_evidence_rules(
        category=req.stage,
        profile=req.model_dump(mode="json"),
        baseline=stage3["baseline"],
        primary_gap=stage3["primary_gap"],
        support_gaps=list(stage3.get("gaps") or [])[1:],
    )
    health_context = build_elderly_health_context(req)
    elderly_context = build_elderly_lifestyle_context(req)
    if req.stage == "elderly" and health_context.get("has_condition") and not limited:
        labels = ", ".join(health_context.get("condition_labels") or [])
        summary = (
            f"Rekomendasi edukatif disesuaikan dengan konteks kesehatan yang dilaporkan ({labels}) tanpa menyimpulkan diagnosis. "
            "Fokus tetap pada pola makan, pilihan makanan, dan kebiasaan yang aman untuk edukasi umum."
        )
    recs = recommendations(req)
    return NutritionResponse(
        stage=req.stage,
        category=CATEGORY_LABELS[req.stage],
        age_band=age_band_label(req),
        personalization_status="limited_for_safety" if limited else "personalized_education",
        validation=validation,
        input_summary=build_input_summary(req),
        summary=summary,
        estimated_needs=calculate_estimated_needs(req),
        meal_pattern=meal_pattern(req),
        priority_nutrients=priority_nutrients(req),
        food_groups=food_groups(req),
        recommendations=recs,
        sample_menu=sample_menu(req),
        guidance=[
            "Gunakan hasil sebagai informasi umum dan contoh pola makan, bukan target medis individual.",
            "Perhatikan respons lapar/kenyang, toleransi makanan, keamanan tekstur, dan variasi pangan yang sesuai usia.",
        ],
        safety_notes=build_safety_notes(req),
        disclaimer=(
            "Angka yang ditampilkan adalah estimasi/referensi kecukupan populasi dan rekomendasi edukatif, bukan diagnosis atau resep diet medis. "
            "Untuk gangguan pertumbuhan, penyakit, alergi berat, atau masalah menelan, gunakan penilaian tenaga kesehatan."
        ),
        references=public_reference_labels(req),
        suggested_goals=suggested_goals(req, stage3, stage4),
        baseline=stage3["baseline"],
        detected_gaps=stage3["gaps"],
        primary_gap=stage3["primary_gap"],
        primary_target=stage3["primary_target"],
        support_targets=stage3["support_targets"],
        evidence_rule_evaluation=stage4,
        health_context=health_context,
        elderly_context=elderly_context,
    )
