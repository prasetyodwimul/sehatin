from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    NutritionEvaluationModel,
    NutritionMealLogModel,
    NutritionProfileModel,
    NutritionProgramDayModel,
    NutritionProgramExtensionModel,
    NutritionProgramGoalModel,
    NutritionProgramModel,
    NutritionRecommendationModel,
    NutritionRequestModel,
    UserModel,
)
from app.models.base import utcnow
from app.config import get_settings
from app.nutrition_validation import validate_anthropometrics
from app.nutrition.program_evidence import EVIDENCE, RULE_VERSION, STAGE5_RULE_VERSION, adherence_for_task, behavioral_status, build_personalized_tasks, preferred_mpasi_metric, preferred_toddler_metric, task_result_status, target_for_metric
from app.nutrition.daily_results import STAGE6_RULE_VERSION, DailyResultValidationError, evaluate_daily_results, evaluate_partial_daily_results, responsive_feeding_adherence
from app.nutrition.adaptive_program import RULE_VERSION as ADAPTIVE_RULE_VERSION, calculate_indicators, calculate_elderly_indicators, daily_summary, decide_adaptation, decide_elderly_adaptation, missing_day_decision, plan_adjustments, safety_guard
from app.nutrition.elderly_goal_context import build_elderly_program_goal
from app.nutrition.rules import has_medical_context
from app.schemas.nutrition import NutritionRequest
from app.schemas.nutrition_program import DailyLogRequest
from app.services.nutrition_service import generate_nutrition_recommendation

STAGE8_RULE_VERSION = "nutrition_block_review_v1"

PROGRAM_TEMPLATES = {
    "mpasi": [
        ("Responsive feeding", "Ikuti sinyal lapar dan kenyang tanpa memaksa.", "Gunakan tekstur sesuai tahap usia dan sajikan porsi kecil yang dapat ditambah."),
        ("Protein hewani", "Sertakan sumber protein hewani yang sesuai dan aman.", "Padukan makanan pokok, protein hewani, sayur/buah, dan lemak tambahan sesuai kebutuhan."),
        ("Keragaman", "Kenalkan variasi pangan secara bertahap.", "Pertahankan bahan yang sudah ditoleransi dan tambahkan satu variasi yang sesuai tahap."),
        ("Tekstur aman", "Sesuaikan tekstur dengan kemampuan makan anak.", "Naikkan tekstur bertahap tanpa memberi bentuk yang meningkatkan risiko tersedak."),
    ],
    "toddler": [
        ("Ritme makan", "Bangun jadwal makan dan snack yang konsisten.", "Sediakan makan utama seimbang dan snack bergizi pada waktu yang relatif teratur."),
        ("Variasi pangan", "Perluas paparan sayur dan buah tanpa memaksa.", "Tawarkan porsi kecil bersama makanan yang sudah disukai."),
        ("Protein & energi", "Sertakan sumber protein di makan utama.", "Padukan karbohidrat, protein, sayur/buah, dan lemak sehat."),
        ("Minuman utama", "Prioritaskan air putih dan batasi minuman manis.", "Sediakan air di waktu makan dan di sela aktivitas."),
    ],
    "elderly": [
        ("Protein merata", "Sebarkan sumber protein pada beberapa waktu makan.", "Pilih tekstur yang mudah dikunyah bila diperlukan dan sesuaikan dengan toleransi."),
        ("Hidrasi", "Bangun rutinitas minum sepanjang hari.", "Sediakan air secara teratur kecuali ada pembatasan cairan dari tenaga kesehatan."),
        ("Padat gizi", "Utamakan makanan bernutrisi tinggi dalam porsi yang realistis.", "Gabungkan protein, sayur/buah, sumber energi, dan lemak sehat."),
        ("Keteraturan", "Jaga pola makan yang teratur sesuai nafsu makan.", "Gunakan porsi lebih kecil tetapi lebih sering bila asupan besar sulit dihabiskan."),
    ],
}

ELDERLY_SWALLOWING_SAFE_TEMPLATES = [
    (
        "Komposisi bergizi dengan pola yang sudah aman",
        "Susun satu waktu makan dari sumber energi, protein, dan sayur/buah menggunakan bentuk yang sudah diketahui aman.",
        "Contoh menu membantu memilih kandungan makanan; bentuk, tekstur, dan kekentalan tetap mengikuti pola yang sudah diketahui aman.",
    ),
    (
        "Protein dan energi yang realistis",
        "Pastikan salah satu waktu makan memiliki sumber protein dan sumber energi yang dapat dikonsumsi dengan pola yang sudah aman.",
        "Pilih bahan yang familiar dan sesuai alergi/pantangan; aplikasi tidak menentukan level tekstur atau kekentalan.",
    ),
    (
        "Variasi kelompok pangan",
        "Pertahankan kelompok pangan yang sudah dapat dikonsumsi dan tambahkan variasi bahan tanpa mengubah bentuk yang sudah aman.",
        "Fokus pada kandungan: sumber energi, protein, sayur/buah, serta cairan sesuai pola yang sudah aman.",
    ),
    (
        "Keteraturan makan dan minum",
        "Jaga waktu makan/minum tetap teratur sambil mencatat nafsu makan, cairan, dan kenyamanan hari ini.",
        "Jika ada perubahan kemampuan menelan, jangan mencoba level tekstur/kekentalan baru berdasarkan aplikasi.",
    ),
]


GOAL_COPY = {
    "mpasi": (
        "Bangun rutinitas MPASI yang konsisten",
        "Menjalankan panduan makan, variasi kelompok pangan, tekstur sesuai tahap, serta praktik responsive feeding secara konsisten.",
    ),
    "toddler": (
        "Bangun kebiasaan makan sehat yang konsisten",
        "Menjalankan struktur makan dan healthy eating checklist sesuai panduan tanpa memaksa anak menghabiskan makanan.",
    ),
    "elderly": (
        "Tingkatkan konsistensi panduan nutrisi harian",
        "Menjalankan pola makan, sumber protein/kelompok pangan, dan hidrasi yang relevan dengan assessment secara konsisten.",
    ),
}


def suggested_goal_payload(stage: str, duration_days: int = 14, *, profile_payload: dict | None = None, selected_goal_key: str | None = None) -> list[dict]:
    """Return one measurable primary goal for child programs.

    Lansia intentionally keeps the legacy guided-goal model because the adaptive
    MPASI/Toddler specification must not be copied onto it.
    """
    if stage == "elderly":
        profile = dict(profile_payload or {})
        # Keep one primary, user-readable goal. The actual program progress still
        # comes from daily task results; "completed days" is not presented as the goal itself.
        health_context = dict(profile.get("health_context") or {})
        lifestyle_context = dict(profile.get("elderly_context") or {})
        return [build_elderly_program_goal(
            profile,
            health_context=health_context,
            lifestyle_context=lifestyle_context,
            duration_days=duration_days,
            preferred_goal_key=selected_goal_key,
        )]

    profile = profile_payload or {}
    preferred = preferred_mpasi_metric(profile) if stage == "mpasi" else preferred_toddler_metric(profile)
    metric = selected_goal_key or preferred
    # Stage 3 can surface any evidence-backed metric supported by the existing
    # program engine. Keep the Stage 4 implementation unchanged; this only
    # allows its existing selected_goal_key contract to receive Stage 3 output.
    valid = ({
        "meal_frequency", "animal_source_food", "fruit_vegetable", "dietary_diversity",
        "responsive_feeding", "texture", "food_response",
    } if stage == "mpasi" else {
        "meal_routine", "sweet_beverage", "vegetable_fruit_exposure",
        "responsive_feeding", "self_feeding", "protein_presence", "food_response",
    })
    if metric not in valid:
        metric = preferred
    spec = target_for_metric(stage, metric, profile)
    titles = {
        "meal_frequency": "Konsistensi frekuensi makan",
        "animal_source_food": "Paparan protein hewani",
        "fruit_vegetable": "Paparan sayur dan buah",
        "dietary_diversity": "Keragaman pangan",
        "responsive_feeding": "Responsive feeding",
        "texture": "Penerimaan tekstur sesuai tahap",
        "food_response": "Penerimaan makanan fokus",
        "meal_routine": "Rutinitas makan",
        "sweet_beverage": "Kurangi minuman berpemanis",
        "vegetable_fruit_exposure": "Paparan sayur dan buah",
        "self_feeding": "Kemandirian makan",
        "protein_presence": "Protein pada makan utama",
    }
    return [{
        "goal_key": metric,
        "title": titles.get(metric, metric.replace("_", " ").title()),
        "description": spec.get("why") or "Goal perilaku dipilih dari assessment dan profile saat program dimulai.",
        "baseline": 0,
        "target": float(max(1, math.ceil(duration_days * 0.7))),
        "unit": "successful target days",
        "measurement_method": f"daily metric adherence for {metric}",
        "duration": duration_days,
        "priority": 1,
        "status": "NOT_STARTED",
    }]

def _program_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _safe_profile_payload(req: NutritionRequest) -> dict:
    return {
        "stage": req.stage,
        "age_months": req.age_months,
        "age_years": req.age_years,
        "sex": req.sex,
        "weight_kg": req.weight_kg,
        "height_cm": req.height_cm,
        "date_of_birth": req.date_of_birth.isoformat() if req.date_of_birth else None,
        "assessment_date": req.assessment_date.isoformat() if req.assessment_date else None,
        "feeding_mode": req.feeding_mode,
        "mpasi_history": req.mpasi_history,
        "texture_level": req.texture_level,
        "appetite": req.appetite,
        "meal_frequency": req.meal_frequency,
        "activity_level": req.activity_level,
        "chewing_difficulty": req.chewing_difficulty,
        "swallowing_difficulty": req.swallowing_difficulty,
        "hydration_pattern": req.hydration_pattern,
        "eating_independence": req.eating_independence,
        "caregiver_support": req.caregiver_support,
        "animal_source_food_days": req.animal_source_food_days,
        "fruit_vegetable_days": req.fruit_vegetable_days,
        "recent_food_group_count": req.recent_food_group_count,
        "recent_food_groups": req.recent_food_groups,
        "responsive_feeding": req.responsive_feeding,
        "meal_routine": req.meal_routine,
        "sweet_beverage_days": req.sweet_beverage_days,
        "sweetened_beverage_exposure": req.sweetened_beverage_exposure,
        "pressure_to_eat": req.pressure_to_eat,
        "screen_during_meals": req.screen_during_meals,
        "self_feeding_opportunity": req.self_feeding_opportunity,
        "mealtime_duration_minutes": req.mealtime_duration_minutes,
        "food_preferences": req.food_preferences,
        "primary_concern": req.primary_concern,
        "snack_frequency": req.snack_frequency,
        "feeding_method": req.feeding_method,
        "food_refusal": req.food_refusal,
        "food_rejection": req.food_rejection,
        "food_rejection_details": req.food_rejection_details,
        "feeding_difficulty": req.feeding_difficulty,
        "feeding_difficulty_details": req.feeding_difficulty_details,
        "texture_refusal": req.texture_refusal,
        "repeated_exposure_days": req.repeated_exposure_days,
        "water_primary_beverage": req.water_primary_beverage,
        "meal_environment": req.meal_environment,
        "safety_hygiene_ok": req.safety_hygiene_ok,
        "barriers": req.barriers,
        "allergies": req.allergies,
        "dietary_restrictions": req.dietary_restrictions,
        "medical_context": req.medical_context,
        "has_condition": req.has_condition,
        "conditions": list(req.conditions),
        "other_condition": req.other_condition,
        "notes": req.notes,
    }


def _assert_guided_safe(req: NutritionRequest, validation: dict, result_status: str) -> None:
    if validation["status"] == "INVALID":
        raise HTTPException(status_code=422, detail=validation["message"])
    if result_status != "limited_for_safety":
        return

    # Elderly swallowing difficulty may continue only in a general safety-limited
    # mode. The generated program must not personalize texture/thickness or
    # provide therapeutic swallowing advice. Other medical-context safety
    # limitations remain blocked.
    swallowing_general_mode = (
        req.stage == "elderly"
        and bool(req.swallowing_difficulty)
        and not has_medical_context(req)
    )
    if swallowing_general_mode:
        return

    raise HTTPException(
        status_code=409,
        detail="Guided Program tidak dibuat untuk assessment yang membutuhkan batasan keselamatan. Gunakan hasil edukatif dan pertimbangkan tenaga kesehatan.",
    )


def _restriction_note(profile_payload: dict) -> str | None:
    restricted = [str(x).strip() for x in (profile_payload.get("allergies") or []) + (profile_payload.get("dietary_restrictions") or []) if str(x).strip()]
    if not restricted:
        return None
    return "Hindari bahan yang sudah ditandai sebagai alergi/batasan: " + ", ".join(restricted) + "."


def _safe_menu_example(recommendation: dict, profile_payload: dict, day_number: int) -> str:
    menus = [str(x) for x in recommendation.get("sample_menu", [])]
    banned = [str(x).lower() for x in (profile_payload.get("allergies") or []) + (profile_payload.get("dietary_restrictions") or []) if str(x).strip()]
    safe = [m for m in menus if not any(term in m.lower() for term in banned)]
    if safe:
        return safe[(day_number - 1) % len(safe)]
    return "Gunakan kombinasi kelompok pangan yang direkomendasikan dan pilih bahan yang sesuai dengan alergi/batasan yang telah dimasukkan."


def _elderly_task(
    *,
    day_number: int,
    key: str,
    metric: str,
    action: str,
    target_label: str,
    result_prompt: str,
    input_type: str,
    target_value=None,
    unit: str | None = None,
    options: list[dict] | None = None,
    adherence_map: dict[str, float] | None = None,
    priority: int = 1,
    why: str = "Input harian membantu program menyesuaikan langkah berikutnya secara bertahap.",
) -> dict:
    return {
        "key": f"elderly-{day_number}-{key}",
        "id": f"elderly-{day_number}-{key}",
        "metric": metric,
        "metric_id": metric,
        "input_type": input_type,
        "target_value": target_value,
        "unit": unit,
        "target_label": target_label,
        "action": action,
        "action_text": action,
        "result_prompt": result_prompt,
        "options": list(options or []),
        "adherence_map": dict(adherence_map or {}),
        "priority": priority,
        "why": why,
        "result": None,
        "current_result": None,
        "status": "NOT_STARTED",
        "target_origin": "ELDERLY_BEHAVIORAL_GUIDANCE",
        "day_applicability": "DAILY",
    }


def _elderly_daily_tasks(
    profile_payload: dict,
    recommendation: dict,
    day_number: int,
    *,
    primary_action: str,
    strategy: str = "CONTINUE",
    goal_key: str | None = None,
) -> list[dict]:
    """Build Lansia-specific tasks from the primary behavioural goal.

    Unlike the child programs, the task set centres on adequacy/routine,
    hydration, functional eating, support and barriers. Disease context only
    modifies educational food focus; it never creates a therapeutic diet.
    """
    try:
        meal_target = int(profile_payload.get("meal_frequency") or 3)
    except (TypeError, ValueError):
        meal_target = 3
    meal_target = max(1, min(4, meal_target))

    health_context = dict(recommendation.get("health_context") or {})
    lifestyle_context = dict(recommendation.get("elderly_context") or {})
    contextual_actions = [str(item) for item in (health_context.get("daily_actions") or []) if str(item).strip()]
    lifestyle_actions = [str(item) for item in (lifestyle_context.get("daily_actions") or []) if str(item).strip()]
    all_context_actions = [*contextual_actions, *lifestyle_actions]
    context_action = all_context_actions[(day_number - 1) % len(all_context_actions)] if all_context_actions else primary_action

    swallowing_mode = bool(profile_payload.get("swallowing_difficulty"))
    goal_key = str(goal_key or build_elderly_program_goal(
        profile_payload,
        health_context=health_context,
        lifestyle_context=lifestyle_context,
    ).get("goal_key") or "elderly_balanced_meal_routine")

    if day_number <= 2:
        phase = "baseline"
    elif day_number <= 5:
        phase = "stabilize"
    elif day_number <= 9:
        phase = "consistency"
    elif day_number <= 12:
        phase = "variety"
    else:
        phase = "consolidate"

    routine_action = (
        "Jalankan waktu makan utama dengan bentuk/tekstur yang sudah diketahui aman dan catat berapa kali dapat dilakukan."
        if swallowing_mode else
        "Jalankan waktu makan utama sesuai pola yang paling realistis hari ini."
    )
    routine = _elderly_task(
        day_number=day_number, key="meal-routine", metric="elderly_meal_routine",
        action=routine_action,
        target_label=f"Sekitar {meal_target} kesempatan makan utama sesuai pola hari ini",
        result_prompt="Berapa kali kesempatan makan utama berhasil dijalankan hari ini?",
        input_type="count", target_value=meal_target, unit="waktu makan", priority=1,
        why="Kesempatan makan yang benar-benar dilakukan lebih informatif daripada sekadar menandai hari selesai.",
    )

    hydration_action = (
        "Pertahankan kesempatan minum dengan pola yang sudah diketahui aman dan catat keteraturannya hari ini."
        if swallowing_mode else
        "Buat kesempatan minum mudah dijangkau pada beberapa waktu sepanjang hari tanpa menetapkan target volume medis."
    )
    hydration = _elderly_task(
        day_number=day_number, key="hydration-routine", metric="elderly_hydration_routine",
        action=hydration_action,
        target_label="Kesempatan minum dapat dijalankan lebih teratur hari ini",
        result_prompt="Bagaimana keteraturan minum hari ini?", input_type="choice", target_value="regular",
        options=[{"value": "regular", "label": "Teratur"}, {"value": "partial", "label": "Sebagian"}, {"value": "not_yet", "label": "Belum"}],
        adherence_map={"regular": 100.0, "partial": 60.0, "not_yet": 0.0}, priority=1,
        why="Program memantau kebiasaan minum, bukan menentukan jumlah cairan individual untuk kondisi medis tertentu.",
    )

    composition_action = (
        "Pilih satu waktu makan dengan sumber energi + protein + sayur/buah menggunakan bentuk yang sudah diketahui aman."
        if swallowing_mode else
        "Lengkapi satu waktu makan dengan sumber energi, protein, dan sayur atau buah dari bahan yang tersedia."
    )
    composition = _elderly_task(
        day_number=day_number, key="meal-composition", metric="elderly_meal_quality",
        action=composition_action,
        target_label="Satu waktu makan memiliki komposisi yang lebih lengkap",
        result_prompt="Seberapa lengkap komposisi makan yang berhasil dijalankan hari ini?", input_type="choice", target_value="mostly",
        options=[{"value": "mostly", "label": "Lengkap"}, {"value": "some", "label": "Sebagian"}, {"value": "not_yet", "label": "Belum"}],
        adherence_map={"mostly": 100.0, "some": 60.0, "not_yet": 0.0}, priority=2,
        why="Fokus pada kecukupan kelompok pangan dan bahan yang realistis, bukan resep diet medis.",
    )

    context = _elderly_task(
        day_number=day_number, key="context-focus", metric="elderly_context_focus",
        action=context_action,
        target_label="Terapkan satu fokus nutrisi yang relevan dengan assessment",
        result_prompt="Seberapa jauh fokus nutrisi ini dapat diterapkan hari ini?", input_type="choice", target_value="done",
        options=[{"value": "done", "label": "Terlaksana"}, {"value": "partial", "label": "Sebagian"}, {"value": "not_done", "label": "Belum"}],
        adherence_map={"done": 100.0, "partial": 60.0, "not_done": 0.0}, priority=2,
        why="Kondisi kesehatan yang dilaporkan memodifikasi fokus edukasi makanan tanpa menjadi diagnosis atau larangan baru.",
    )

    support_mode = str(lifestyle_context.get("eating_independence") or "unknown")
    support_action = {
        "needs_reminder": "Gunakan satu pengingat pada waktu makan/minum yang paling mudah terlewat.",
        "needs_setup": "Siapkan satu makanan atau minuman lebih awal agar waktu makan lebih mudah dijalankan.",
        "needs_assistance": "Rencanakan bantuan pada satu waktu makan/minum yang paling membutuhkan dukungan.",
    }.get(support_mode, "Pertahankan cara makan/minum yang paling mandiri dan nyaman hari ini.")
    support = _elderly_task(
        day_number=day_number, key="eating-support", metric="elderly_eating_support",
        action=support_action,
        target_label="Dukungan makan/minum sesuai kebutuhan hari ini",
        result_prompt="Apakah dukungan makan/minum hari ini sesuai kebutuhan?", input_type="choice", target_value="adequate",
        options=[{"value": "adequate", "label": "Sesuai"}, {"value": "partial", "label": "Sebagian"}, {"value": "not_needed", "label": "Tidak perlu"}],
        adherence_map={"adequate": 100.0, "partial": 60.0, "not_needed": 100.0}, priority=2,
        why="Dukungan digunakan untuk membuat rencana lebih mudah dijalankan, bukan untuk menilai tingkat ketergantungan.",
    )

    experience = _elderly_task(
        day_number=day_number, key="daily-experience", metric="elderly_daily_experience",
        action="Catat apakah makan/minum dan panduan hari ini terasa mudah, cukup, atau sulit dijalankan.",
        target_label="Catat pengalaman makan/minum hari ini",
        result_prompt="Bagaimana pengalaman menjalankan panduan hari ini?", input_type="simple_experience",
        options=[{"value": "easy", "label": "Mudah"}, {"value": "manageable", "label": "Cukup"}, {"value": "difficult", "label": "Sulit"}],
        priority=4, why="Pengalaman harian membantu sistem memilih EASE, CONTINUE, atau ADVANCE tanpa membuat skor klinis.",
    )

    primary_by_goal = {
        "elderly_safe_nutrition_routine": composition,
        "elderly_hydration_routine": hydration,
        "elderly_supported_meal_routine": support,
        "elderly_meal_routine": routine,
        "elderly_balanced_meal_routine": composition,
    }
    primary = primary_by_goal.get(goal_key, composition)

    supporting_by_goal = {
        "elderly_safe_nutrition_routine": [routine, hydration, context],
        "elderly_hydration_routine": [routine, composition, context],
        "elderly_supported_meal_routine": [routine, composition, hydration],
        "elderly_meal_routine": [composition, hydration, context],
        "elderly_balanced_meal_routine": [routine, hydration, context],
    }
    supports = [task for task in supporting_by_goal.get(goal_key, [routine, hydration, context]) if task["key"] != primary["key"]]
    # A reported chronic-condition context remains an educational modifier from day 1.
    # It never becomes a clinical target, but the first supporting task should make
    # the connection visible instead of hiding it behind later phases.
    if health_context.get("has_condition") and context["key"] != primary["key"]:
        supports = [context, *[task for task in supports if task["key"] != context["key"]]]

    # Day phases make the journey feel progressive instead of repeating a fixed checklist.
    if phase == "baseline":
        tasks = [primary, supports[0], experience]
    elif phase in {"stabilize", "consistency"}:
        tasks = [primary, supports[0], supports[1], experience]
    elif phase == "variety":
        tasks = [primary, supports[0], composition if composition["key"] != primary["key"] else context, experience]
    else:
        tasks = [primary, supports[0], experience]

    if strategy == "EASE":
        primary["action"] = primary["action_text"] = "Fokuskan hari ini pada satu langkah utama yang paling mungkin dijalankan: " + str(primary.get("action") or primary.get("target_label") or "")
        primary["target_label"] = "Satu langkah utama yang paling realistis hari ini"
        return [primary, experience]

    if strategy == "ADVANCE":
        extra_action = (
            "Tambahkan satu variasi bahan dari kelompok pangan yang sama tanpa mengubah bentuk/tekstur yang sudah diketahui aman."
            if swallowing_mode else
            "Tambahkan satu variasi bahan lokal yang masih sesuai dengan goal dan pola makan yang sudah berjalan."
        )
        advance = _elderly_task(
            day_number=day_number, key="small-step", metric="elderly_small_step",
            action=extra_action,
            target_label="Tambahkan satu langkah kecil tanpa mengubah tujuan utama",
            result_prompt="Apakah langkah kecil tambahan ini dapat diterapkan hari ini?", input_type="boolean", target_value=True, priority=5,
            why="Langkah tambahan hanya muncul setelah beberapa hari menunjukkan pola yang cukup stabil.",
        )
        return [*tasks, advance]

    return tasks


def _day_payload(stage: str, day_number: int, recommendation: dict, profile_payload: dict, references: list[str], *, extension: bool = False, primary_metric: str | None = None, adaptive_strategy: str | None = None) -> dict:
    focus, action, meal = PROGRAM_TEMPLATES[stage][(day_number - 1) % len(PROGRAM_TEMPLATES[stage])]
    swallowing_general_mode = stage == "elderly" and bool(profile_payload.get("swallowing_difficulty"))
    if swallowing_general_mode:
        focus, action, meal = ELDERLY_SWALLOWING_SAFE_TEMPLATES[(day_number - 1) % len(ELDERLY_SWALLOWING_SAFE_TEMPLATES)]
    restriction = _restriction_note(profile_payload)
    menu_example = _safe_menu_example(recommendation, profile_payload, day_number)
    health_context = dict(recommendation.get("health_context") or {}) if stage == "elderly" else {}
    if stage == "elderly" and health_context.get("has_condition") and not swallowing_general_mode:
        program_focus = list(health_context.get("program_focus") or [])
        daily_actions = list(health_context.get("daily_actions") or [])
        if program_focus:
            focus = str(program_focus[(day_number - 1) % len(program_focus)])
        if daily_actions:
            action = str(daily_actions[(day_number - 1) % len(daily_actions)])
    when = {
        "mpasi": "Hari ini, sebelum menekan Simpan progress.",
        "toddler": "Hari ini, sebelum menekan Simpan progress.",
        "elderly": "Pada salah satu waktu makan utama hari ini.",
    }[stage]
    tasks = build_personalized_tasks(stage, profile_payload, day_number, primary_metric=primary_metric, personalization=recommendation)
    if stage == "elderly" and not tasks:
        tasks = _elderly_daily_tasks(
            profile_payload, recommendation, day_number, primary_action=action, strategy=adaptive_strategy or "CONTINUE", goal_key=primary_metric
        )
    if tasks:
        focus = {
            "meal_frequency": "Frekuensi makan",
            "animal_source_food": "Protein hewani",
            "fruit_vegetable": "Sayur dan buah",
            "dietary_diversity": "Keragaman pangan",
            "responsive_feeding": "Responsive feeding",
            "texture": "Tekstur sesuai tahap",
            "meal_routine": "Ritme makan",
            "sweet_beverage": "Minuman tanpa gula tambahan",
            "vegetable_fruit_exposure": "Paparan sayur dan buah",
            "self_feeding": "Kesempatan makan mandiri",
            "protein_presence": "Protein pada makan utama",
            "food_response": "Respons terhadap paparan makanan",
            "elderly_meal_routine": "Kesempatan makan utama",
            "elderly_hydration_routine": "Keteraturan minum",
            "elderly_eating_support": "Dukungan makan/minum",
            "elderly_meal_quality": "Komposisi makan",
            "elderly_context_focus": "Fokus nutrisi harian",
            "elderly_daily_experience": "Pengalaman makan/minum",
        }.get(tasks[0]["metric"], focus)
        action = tasks[0].get("action_text") or tasks[0].get("action") or tasks[0]["target_label"]
    if extension:
        action = "Ulangi target yang belum konsisten, lalu lanjutkan bertahap. " + action
    if tasks:
        checklist = [task.get("action_text") or task["target_label"] for task in tasks]
    elif stage == "elderly":
        contextual_actions = list(health_context.get("daily_actions") or [])
        checklist = [
            action if contextual_actions else "Ikuti tindakan utama hari ini",
            "Terapkan panduan makan pada waktu makan yang sesuai",
            "Catat apakah panduan dapat diterapkan hari ini",
        ]
    else:
        # Stage 5 must not fabricate a measurable target when Stage 4 has no
        # matching evidence rule. Keep the day available for review, but expose
        # no fake checklist/task.
        checklist = []
        action = "Target harian belum tersedia untuk kombinasi baseline dan evidence rule ini."
    return {
        "focus": focus,
        "recommended_action": action,
        "meal_guidance": f"{meal} Contoh: {menu_example}",
        "action_details": {
            "title": focus,
            "why": tasks[0]["why"] if tasks else (
                "Tindakan ini menyesuaikan konteks kesehatan yang dilaporkan tanpa mengubahnya menjadi diagnosis atau terapi diet."
                if stage == "elderly" and health_context.get("has_condition")
                else "Tindakan ini mendukung konsistensi program."
            ),
            "action": action,
            "when": when,
            "how": "Lakukan action, centang bahwa action sudah dikerjakan, lalu isi hasil aktual secara terpisah. Hasil boleh belum mencapai target dan tetap harus disimpan apa adanya.",
            "completion_criteria": "Hari selesai ketika seluruh action ditandai sudah dikerjakan dan refleksi hari tersimpan. Pencapaian target dihitung terpisah dari checkbox action.",
            "supports_goal": primary_metric or "daily_consistency",
            "tasks": tasks,
            "rule_version": RULE_VERSION,
            "stage5_engine_version": (tasks[0].get("stage5_engine_version") if tasks else None),
            "todo_generation_status": ("READY" if tasks and tasks[0].get("stage5_engine_version") else "LEGACY_COMPATIBILITY" if tasks else "NO_MATCHING_RULE"),
            "measurement_note": "Target perilaku diterjemahkan dari panduan evidence; ambang adaptasi program adalah heuristik produk SEHATIN, bukan cut-off klinis.",
            "health_context": (health_context if stage == "elderly" else {}),
        },
        "meal_guidance_details": {
            "occasion": "Waktu makan utama" if stage == "elderly" else "Main meal",
            "example": menu_example,
            "visual_key": _menu_visual_key(stage, menu_example),
            "food_groups": recommendation.get("food_groups", [])[:5],
            "preparation": meal,
            "substitutions": restriction or "Boleh mengganti bahan dengan pilihan dari kelompok pangan setara yang sesuai toleransi.",
            "restriction_note": restriction,
            "safety_notes": recommendation.get("safety_notes", [])[:3],
            "health_context": (health_context if stage == "elderly" else {}),
        },
        "checklist": checklist,
        "reference_notes": references[:3],
    }


def _menu_visual_key(stage: str, menu_example: str) -> str:
    """Return a stable educational visual key for the generated menu.

    The key is stored inside meal_guidance_details JSON, so existing databases
    do not need a schema migration. Older programs without this key continue
    to use the frontend title-based fallback.
    """
    value = (menu_example or "").lower()
    if stage == "mpasi":
        if "labu" in value:
            return "mpasi_pumpkin"
        if any(word in value for word in ("pisang", "pepaya", "mangga", "alpukat")):
            return "mpasi_banana"
        if any(word in value for word in ("brokoli", "wortel", "bayam", "sayur")):
            return "mpasi_vegetable"
        if any(word in value for word in ("ayam", "ikan", "telur", "tahu", "tempe", "daging")):
            return "mpasi_protein"
        return "mpasi_soft"

    if stage == "toddler":
        if any(word in value for word in ("ayam", "ikan", "telur", "daging", "tahu", "tempe")):
            return "toddler_protein"
        if any(word in value for word in ("buah", "pisang", "pepaya", "apel", "mangga")):
            return "toddler_fruit"
        if any(word in value for word in ("brokoli", "wortel", "bayam", "sayur")):
            return "toddler_vegetable"
        return "toddler_balanced"

    if "ikan" in value:
        return "elderly_fish"
    if any(word in value for word in ("bubur", "lunak", "lembut", "lumat")):
        return "elderly_soft"
    if any(word in value for word in ("ayam", "tahu", "tempe", "telur")):
        return "elderly_protein"
    if any(word in value for word in ("teh", "air", "cairan", "hidrasi")):
        return "elderly_hydration"
    return "elderly_balanced"


GENERIC_CHILD_CHECKLIST = {
    "Ikuti tindakan utama hari ini",
    "Terapkan meal guidance pada waktu makan yang sesuai",
    "Catat apakah panduan dapat diterapkan hari ini",
}

GENERIC_ELDERLY_CHECKLIST = {
    "Ikuti tindakan utama hari ini",
    "Terapkan panduan makan pada waktu makan yang sesuai",
    "Catat apakah panduan dapat diterapkan hari ini",
}


def _needs_personalized_upgrade(program: NutritionProgramModel, day: NutritionProgramDayModel) -> bool:
    if program.stage not in {"mpasi", "toddler", "elderly"} or day.completed:
        return False
    tasks = ((day.action_details or {}).get("tasks") or [])
    if tasks and all(str(task.get("metric") or "") not in {"", "legacy"} for task in tasks):
        return False
    checklist = {str(item) for item in (day.checklist or [])}
    generic = GENERIC_ELDERLY_CHECKLIST if program.stage == "elderly" else GENERIC_CHILD_CHECKLIST
    return not tasks or bool(checklist & generic)


def _ensure_personalized_day_payload(program: NutritionProgramModel, day: NutritionProgramDayModel) -> bool:
    """Upgrade an unfinished legacy child day in memory, without a DB migration.

    GET responses can immediately render the measurable To Do. The upgraded
    payload is persisted naturally on the next daily save. Completed history is
    never rewritten.
    """
    if not _needs_personalized_upgrade(program, day):
        return False
    profile_payload = program.assessment_snapshot or {}
    previous_details = dict(day.action_details or {})
    primary = _stage5_primary_metric(program.recommendation_snapshot or {}, program.stage, profile_payload)
    previous_strategy = str((previous_details.get("adaptation_context") or {}).get("strategy") or "CONTINUE") if program.stage == "elderly" else None
    payload = _day_payload(
        program.stage,
        day.day_number,
        program.recommendation_snapshot or {},
        profile_payload,
        (program.program_config or {}).get("source_snapshot", []),
        primary_metric=primary,
        adaptive_strategy=previous_strategy,
    )
    if previous_details.get("adaptive_mode"):
        payload["action_details"] = {
            **payload["action_details"],
            "planned": True,
            "adaptive_mode": True,
            "generated_from_day": previous_details.get("generated_from_day"),
            "adaptation_context": previous_details.get("adaptation_context") or {"strategy": previous_strategy or "CONTINUE", "new_challenge": False},
            "why_this_plan": previous_details.get("why_this_plan") or "Rencana hari ini diperbarui ke format task terukur tanpa mengubah progress hari yang sudah selesai.",
            "decision": previous_details.get("decision"),
        }
    elif previous_details.get("adaptive_mode") and not previous_details.get("planned", True):
        payload["action_details"] = {**payload["action_details"], "planned": True, "adaptive_mode": True, "generated_from_day": None, "adaptation_context": {"strategy": "MISSED_LOG_DEFAULT", "new_challenge": False}, "why_this_plan": "Log hari sebelumnya belum tersedia. Rencana dibuat lebih ringan dari profile tersimpan agar program mudah dilanjutkan."}
    previous_checks = list(day.checklist_state or [])
    day.focus = payload["focus"]
    day.recommended_action = payload["recommended_action"]
    day.meal_guidance = payload["meal_guidance"]
    day.action_details = payload["action_details"]
    day.meal_guidance_details = payload["meal_guidance_details"]
    day.reference_notes = payload["reference_notes"]
    day.checklist = payload["checklist"]
    day.checklist_state = previous_checks if len(previous_checks) == len(day.checklist) else [False] * len(day.checklist)
    return True


def _stage5_primary_metric(recommendation: dict, stage: str, profile_payload: dict) -> str | None:
    if stage == "elderly":
        health_context = dict(recommendation.get("health_context") or {})
        lifestyle_context = dict(recommendation.get("elderly_context") or {})
        return str(build_elderly_program_goal(
            profile_payload,
            health_context=health_context,
            lifestyle_context=lifestyle_context,
        ).get("goal_key") or "elderly_balanced_meal_routine")
    if stage not in {"mpasi", "toddler"}:
        return None
    stage4 = dict(recommendation.get("evidence_rule_evaluation") or {})
    stage4_primary = dict(stage4.get("primary_target") or {})
    metric = str(stage4_primary.get("metric") or "")
    if metric:
        return metric
    stage3_primary = dict(recommendation.get("primary_target") or {})
    metric = str(stage3_primary.get("metric") or "")
    if metric:
        return metric
    return preferred_mpasi_metric(profile_payload) if stage == "mpasi" else preferred_toddler_metric(profile_payload)


def _generate_days(program: NutritionProgramModel, *, count: int, references: list[str], recommendation: dict, profile_payload: dict, extension: bool = False) -> list[NutritionProgramDayModel]:
    """Create Day 1 detail + indicative future placeholders for child programs.

    Lansia keeps the legacy fixed guided-program behavior. Future MPASI/Toddler
    rows exist only to support timeline/scheduling; their detailed plan is empty
    until generated from the previous day's log/decision.
    """
    rows: list[NutritionProgramDayModel] = []
    primary = str((program.program_config or {}).get("selected_goal_key") or "").strip() or _stage5_primary_metric(recommendation, program.stage, profile_payload)
    themes = [item[0] for item in PROGRAM_TEMPLATES[program.stage]]
    for day_number in range(1, count + 1):
        detailed = program.stage == "elderly" or day_number == 1
        if detailed:
            payload = _day_payload(program.stage, day_number, recommendation, profile_payload, references, extension=extension, primary_metric=primary)
        else:
            payload = {
                "focus": themes[(day_number - 1) % len(themes)],
                "recommended_action": "",
                "meal_guidance": "",
                "action_details": {"planned": False, "indicative_theme": themes[(day_number - 1) % len(themes)], "generated_from_day": None, "adaptive_mode": True},
                "meal_guidance_details": {},
                "checklist": [],
                "reference_notes": [],
            }
        rows.append(NutritionProgramDayModel(program_id=program.id, day_number=day_number, focus=payload["focus"], recommended_action=payload["recommended_action"], meal_guidance=payload["meal_guidance"], action_details=payload["action_details"], meal_guidance_details=payload["meal_guidance_details"], checklist=payload["checklist"], checklist_state=[False] * len(payload["checklist"]), reference_notes=payload["reference_notes"]))
    return rows

def _create_goals(db: Session, program: NutritionProgramModel, *, duration_days: int, remaining_day_gap: int | None = None, profile_payload: dict | None = None, selected_goal_key: str | None = None) -> list[NutritionProgramGoalModel]:
    specs = suggested_goal_payload(program.stage, duration_days, profile_payload=profile_payload or program.assessment_snapshot or {}, selected_goal_key=selected_goal_key)
    rows = []
    for spec in specs:
        target = float(spec["target"])
        if remaining_day_gap is not None and (spec["goal_key"] == "daily_consistency" or program.stage == "elderly"):
            target = float(max(1, remaining_day_gap))
        rows.append(
            NutritionProgramGoalModel(
                program_id=program.id,
                goal_key=spec["goal_key"],
                title=spec["title"],
                description=spec["description"],
                baseline=float(spec["baseline"]),
                target=target,
                unit=spec["unit"],
                measurement_method=spec["measurement_method"],
                duration_days=duration_days,
                priority=int(spec["priority"]),
                status="NOT_STARTED",
                actual=0,
                progress_percentage=0,
            )
        )
    db.add_all(rows)
    return rows


def create_program(db: Session, user: UserModel, assessment: NutritionRequest, *, consent_to_save: bool, duration_days: int = 14, goal_key: str | None = None, display_name: str | None = None) -> NutritionProgramModel:
    if not consent_to_save:
        raise HTTPException(status_code=400, detail="Persetujuan penyimpanan diperlukan untuk memulai Guided Program.")
    validation = validate_anthropometrics(
        stage=assessment.stage,
        age_months=assessment.age_months,
        age_years=assessment.age_years,
        sex=assessment.sex,
        weight_kg=assessment.weight_kg,
        height_cm=assessment.height_cm,
    )
    result = generate_nutrition_recommendation(assessment, validation=validation)
    _assert_guided_safe(assessment, validation, result.personalization_status)

    profile_payload = _safe_profile_payload(assessment)
    profile = NutritionProfileModel(user_id=user.id, stage=assessment.stage, age_months=assessment.age_months, age_years=assessment.age_years, sex=assessment.sex, weight_kg=assessment.weight_kg, height_cm=assessment.height_cm, profile_payload=profile_payload)
    db.add(profile)
    db.flush()
    request_row = NutritionRequestModel(stage=assessment.stage, age_months=assessment.age_months, age_years=assessment.age_years, sex=assessment.sex, weight_kg=assessment.weight_kg, height_cm=assessment.height_cm, personalization_status=result.personalization_status, request_payload={"saved_by_user_choice": True})
    db.add(request_row)
    db.flush()
    result_payload = result.model_dump(mode="json")
    recommendation = NutritionRecommendationModel(request_id=request_row.id, user_id=user.id, profile_id=profile.id, category=result.category, age_band=result.age_band, personalization_status=result.personalization_status, summary=result.summary, result_payload=result_payload)
    db.add(recommendation)
    db.flush()

    now = utcnow()
    label = {"mpasi": "Program MPASI", "toddler": "Program Toddler", "elderly": "Guided Nutrition Program"}[assessment.stage]
    program_title = (display_name or "").strip() or label
    program = NutritionProgramModel(
        user_id=user.id,
        profile_id=profile.id,
        recommendation_id=recommendation.id,
        stage=assessment.stage,
        title=program_title,
        status="ACTIVE",
        duration_days=duration_days,
        cycle_number=1,
        assessment_snapshot=assessment.model_dump(mode="json"),
        recommendation_snapshot=result_payload,
        program_config={"goal_model": "goal_metric_v2" if assessment.stage in {"mpasi", "toddler"} else "behavioral_adherence_v1", "source_snapshot": result.references, "evidence_rule_version": RULE_VERSION, "evidence_framework": EVIDENCE, "stage5_rule_version": STAGE5_RULE_VERSION, "stage6_rule_version": STAGE6_RULE_VERSION, "adaptive_mode": assessment.stage in {"mpasi", "toddler", "elderly"}, "adaptive_rule_version": ADAPTIVE_RULE_VERSION, "selected_goal_key": goal_key, "guided_safety_mode": ("swallowing_general_only" if assessment.stage == "elderly" and assessment.swallowing_difficulty and result.personalization_status == "limited_for_safety" else None)},
        started_at=now,
        ends_at=now + (_day_interval() * (duration_days - 1)),
        last_activity_at=now,
    )
    db.add(program)
    db.flush()
    _create_goals(db, program, duration_days=duration_days, profile_payload=profile_payload, selected_goal_key=goal_key)
    db.add_all(_generate_days(program, count=duration_days, references=result.references, recommendation=result_payload, profile_payload=profile_payload))
    db.commit()
    db.refresh(program)
    return program


def owned_program(db: Session, user: UserModel, program_id: str) -> NutritionProgramModel:
    program = db.get(NutritionProgramModel, program_id)
    if not program or program.user_id != user.id:
        raise HTTPException(status_code=404, detail="Program tidak ditemukan.")
    return program


def _days(db: Session, program_id: str) -> list[NutritionProgramDayModel]:
    return list(db.scalars(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program_id).order_by(NutritionProgramDayModel.day_number)))


def _goals(db: Session, program_id: str) -> list[NutritionProgramGoalModel]:
    return list(db.scalars(select(NutritionProgramGoalModel).where(NutritionProgramGoalModel.program_id == program_id).order_by(NutritionProgramGoalModel.priority, NutritionProgramGoalModel.created_at)))


def _meal_logs_by_day(db: Session, program_id: str) -> dict[str, NutritionMealLogModel]:
    rows = list(db.scalars(select(NutritionMealLogModel).where(NutritionMealLogModel.program_id == program_id).order_by(NutritionMealLogModel.logged_at, NutritionMealLogModel.created_at)))
    return {row.program_day_id: row for row in rows if row.program_day_id}


def _normalized_status(program: NutritionProgramModel) -> str:
    return (program.status or "ACTIVE").upper()


def _goal_status(actual: float, target: float, *, complete: bool) -> tuple[str, float, float]:
    pct = min(100.0, round((actual / target) * 100, 1)) if target else 0.0
    gap = max(0.0, target - actual)
    if not complete:
        status = "NOT_STARTED" if actual <= 0 else "IN_PROGRESS"
    elif actual >= target:
        status = "MET"
    elif actual >= target * 0.6:
        status = "PARTIALLY_MET"
    else:
        status = "NOT_MET"
    return status, pct, gap


def _sync_goals(db: Session, program: NutritionProgramModel, *, persist: bool = False) -> list[dict]:
    days = _days(db, program.id)
    completed_days = sum(1 for day in days if day.completed)
    completed_tasks = sum(sum(1 for value in (day.checklist_state or []) if bool(value)) for day in days)
    complete = bool(program.completed_at or program.cancelled_at) or (all(day.completed for day in days) if days else False)
    output = []
    elderly_day_scores: list[float] = []
    if program.stage == "elderly":
        for day in days:
            metric_rows = [
                row for row in ((day.action_details or {}).get("metric_results") or [])
                if isinstance(row.get("adherence"), (int, float))
            ]
            if metric_rows:
                elderly_day_scores.append(sum(float(row["adherence"]) for row in metric_rows) / len(metric_rows))
    for goal in _goals(db, program.id):
        if program.stage == "elderly":
            # Elderly goals describe successful behavioural days, not raw checkbox totals.
            # Existing legacy programs without metric results keep completed-day semantics.
            observed_days = len(elderly_day_scores) if elderly_day_scores else completed_days
            actual = float(sum(1 for score in elderly_day_scores if score >= 70.0)) if elderly_day_scores else float(completed_days)
        elif program.stage in {"mpasi", "toddler"} and goal.goal_key not in {"daily_consistency", "guidance_tasks"}:
            successful_days = 0
            observed_days = 0
            for day in days:
                for row in ((day.action_details or {}).get("metric_results") or []):
                    if str(row.get("metric_id") or "") != goal.goal_key:
                        continue
                    observed_days += 1
                    measured = row.get("adherence")
                    if goal.goal_key == "responsive_feeding":
                        actual = row.get("actual_result", row.get("actual"))
                        corrected = responsive_feeding_adherence(actual)
                        if corrected is not None:
                            measured = corrected
                    if float(measured or 0) >= 100:
                        successful_days += 1
                    break
            actual = float(successful_days)
        else:
            observed_days = completed_days
            actual = float(completed_days if goal.goal_key == "daily_consistency" else completed_tasks)
        status, pct, gap = _goal_status(actual, goal.target, complete=complete)
        if persist:
            goal.actual = actual
            goal.status = status
            goal.progress_percentage = pct
        output.append({"id": goal.id, "goal_key": goal.goal_key, "title": goal.title, "description": goal.description, "baseline": goal.baseline, "target": goal.target, "actual": actual, "unit": goal.unit, "measurement_method": goal.measurement_method, "duration_days": goal.duration_days, "priority": goal.priority, "status": status, "progress_percentage": pct, "remaining_gap": gap})
    return output

def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _day_interval() -> timedelta:
    return timedelta(seconds=get_settings().effective_nutrition_day_interval_seconds)


def _nutrition_zone() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().nutrition_timezone)
    except Exception:
        return ZoneInfo("Asia/Jakarta")


def _uses_midnight_schedule() -> bool:
    # Production/default programs follow the user's calendar: each daily window
    # closes at 00:00 WIB and the next day opens immediately. Keep the existing
    # accelerated interval behavior for local development/tests when a shorter
    # interval is explicitly configured.
    return get_settings().effective_nutrition_day_interval_seconds >= 86400


def _local_midnight_utc(local_date: date) -> datetime:
    local_midnight = datetime.combine(local_date, time.min, tzinfo=_nutrition_zone())
    return local_midnight.astimezone(timezone.utc)


def _program_start_local_date(program: NutritionProgramModel) -> date:
    return _as_utc(program.started_at).astimezone(_nutrition_zone()).date()


def _program_end_at(program: NutritionProgramModel) -> datetime:
    if _uses_midnight_schedule():
        # `ends_at` points at the start of the final scheduled day. Normalize
        # its local calendar date to the next midnight so legacy rows and new
        # rows share the same end-of-day rule.
        final_day_local = _as_utc(program.ends_at).astimezone(_nutrition_zone()).date()
        return _local_midnight_utc(final_day_local + timedelta(days=1))
    # Accelerated development/test schedule retains the previous behavior.
    return _as_utc(program.ends_at) + _day_interval()


def _day_unlock_at(program: NutritionProgramModel, day_number: int) -> datetime:
    if _uses_midnight_schedule():
        start_date = _program_start_local_date(program) + timedelta(days=day_number - 1)
        return _local_midnight_utc(start_date) if day_number > 1 else _as_utc(program.started_at)
    return _as_utc(program.started_at) + (_day_interval() * (day_number - 1))


def _effective_now(program: NutritionProgramModel, current: datetime) -> datetime:
    # Cancellation and safety/recovery pause freeze the journey timeline.
    if program.cancelled_at:
        return min(current, _as_utc(program.cancelled_at))
    paused_at = (program.program_config or {}).get("paused_at")
    if paused_at and _normalized_status(program) in {"PAUSED", "SAFETY_HOLD"}:
        try:
            parsed = datetime.fromisoformat(str(paused_at))
            return min(current, _as_utc(parsed))
        except ValueError:
            pass
    return current


def _calendar_state(program: NutritionProgramModel, *, now: datetime | None = None) -> dict:
    current = _as_utc(now or utcnow())
    effective = _effective_now(program, current)
    started = _as_utc(program.started_at)
    elapsed_seconds = max(0.0, (effective - started).total_seconds())
    interval = _day_interval()
    if _uses_midnight_schedule():
        local_effective = effective.astimezone(_nutrition_zone()).date()
        local_started = started.astimezone(_nutrition_zone()).date()
        raw_day = (local_effective - local_started).days + 1
    else:
        raw_day = int(elapsed_seconds // interval.total_seconds()) + 1
    current_day = min(program.duration_days, max(1, raw_day))
    end_at = _program_end_at(program)
    ended = bool(program.completed_at or program.cancelled_at) or current >= end_at
    last_activity = _as_utc(program.last_activity_at or program.started_at)
    inactive_days = max(0, int(max(0.0, (current - last_activity).total_seconds()) // interval.total_seconds()) - 1)
    return {
        "current_day": current_day,
        "time_elapsed_days": min(program.duration_days, max(1, raw_day)),
        "ended": ended,
        "inactive_days": inactive_days,
        "last_activity_at": last_activity,
        "program_end_at": end_at,
    }


def get_day_availability(program: NutritionProgramModel, day: NutritionProgramDayModel, *, now: datetime | None = None) -> dict:
    current = _as_utc(now or utcnow())
    effective = _effective_now(program, current)
    unlock_at = _day_unlock_at(program, day.day_number)
    if _uses_midnight_schedule():
        # Calendar-midnight schedule: every day closes at the next local
        # midnight. Day 1 may start at an arbitrary time, so its close must
        # be the midnight immediately following the program start date rather
        # than 24 hours after the exact start timestamp.
        start_date = _program_start_local_date(program)
        closes_at = _local_midnight_utc(start_date + timedelta(days=day.day_number))
    else:
        closes_at = unlock_at + _day_interval()
    status = _normalized_status(program)
    paused_current_day = _calendar_state(program, now=current)["current_day"] if status in {"PAUSED", "SAFETY_HOLD"} else None

    if day.completed:
        day_status = "COMPLETED"
    elif (day.action_details or {}).get("manual_skip"):
        day_status = "MISSED"
    elif effective < unlock_at:
        # Future days stay LOCKED. A pause freezes effective time, so they do
        # not silently unlock while the user is recovering.
        day_status = "LOCKED"
    elif status == "CANCELLED":
        day_status = "MISSED"
    elif status in {"PAUSED", "SAFETY_HOLD"} and day.day_number == paused_current_day:
        # PAUSED/SAFETY_HOLD is a program state, not a replacement for the
        # current day's availability state. Keep the last day visible so saved
        # progress can be reviewed and resumed without being labelled LOCKED.
        details = day.action_details or {}
        has_progress = (
            any(bool(value) for value in (day.checklist_state or []))
            or bool(details.get("task_results"))
            or bool(details.get("daily_log"))
            or day.has_complaint is not None
        )
        day_status = "IN_PROGRESS" if has_progress else "AVAILABLE"
    elif status in {"PAUSED", "SAFETY_HOLD"}:
        # Any scheduled day after the frozen current day remains unavailable;
        # older unfinished windows retain their normal missed semantics.
        day_status = "LOCKED" if paused_current_day and day.day_number > paused_current_day else "MISSED"
    elif effective >= closes_at:
        day_status = "MISSED"
    elif status == "ACTIVE":
        has_progress = any(bool(value) for value in (day.checklist_state or []))
        day_status = "IN_PROGRESS" if has_progress else "AVAILABLE"
    else:
        day_status = "MISSED"

    remaining = max(0, math.ceil((unlock_at - current).total_seconds())) if day_status == "LOCKED" and status == "ACTIVE" else 0
    close_remaining = max(0, math.ceil((closes_at - current).total_seconds())) if day_status in {"AVAILABLE", "IN_PROGRESS"} and status == "ACTIVE" else 0
    return {
        "day": day.day_number,
        "status": day_status,
        "unlock_at": unlock_at,
        "close_at": closes_at,
        "remaining_seconds": remaining,
        "close_remaining_seconds": close_remaining,
        "completed_at": day.completed_at,
    }

def _finalize_if_due(db: Session, program: NutritionProgramModel, *, now: datetime | None = None) -> bool:
    """Persist schedule-ended programs without treating missed days as completed."""
    if program.completed_at is not None or program.cancelled_at is not None or _normalized_status(program) != "ACTIVE":
        return False
    current = _as_utc(now or utcnow())
    if current < _program_end_at(program):
        return False
    program.status = "COMPLETED"
    program.completed_at = current
    _sync_goals(db, program, persist=True)
    db.commit()
    db.refresh(program)
    return True


def _program_chain(db: Session, program: NutritionProgramModel, *, through_cycle: int | None = None) -> list[NutritionProgramModel]:
    root_id = program.parent_program_id or program.id
    rows = list(db.scalars(
        select(NutritionProgramModel)
        .where((NutritionProgramModel.id == root_id) | (NutritionProgramModel.parent_program_id == root_id))
        .order_by(NutritionProgramModel.cycle_number)
    ))
    if through_cycle is not None:
        rows = [row for row in rows if row.cycle_number <= through_cycle]
    return rows


def cumulative_goal_for(db: Session, program: NutritionProgramModel) -> dict | None:
    """Return original target + actual earned across cycles up to this program."""
    chain = _program_chain(db, program, through_cycle=program.cycle_number)
    if not chain:
        return None
    root = chain[0]
    root_goals = _sync_goals(db, root)
    root_primary = _primary_goal(root_goals)
    if not root_primary:
        return None
    total_actual = 0.0
    for row in chain:
        goals = _sync_goals(db, row)
        primary = _primary_goal(goals)
        if primary:
            total_actual += float(primary["actual"])
    target = float(root_primary["target"])
    capped_actual = min(target, total_actual)
    progress = min(100.0, round((capped_actual / target) * 100, 1)) if target else 0.0
    remaining = max(0.0, target - capped_actual)
    if capped_actual >= target:
        status = "MET"
    elif program.completed_at or program.cancelled_at:
        status = "PARTIALLY_MET" if capped_actual >= target * 0.6 else "NOT_MET"
    elif capped_actual > 0:
        status = "IN_PROGRESS"
    else:
        status = "NOT_STARTED"
    return {
        "title": root_primary["title"],
        "target": target,
        "actual": capped_actual,
        "unit": root_primary["unit"],
        "progress_percentage": progress,
        "remaining_gap": remaining,
        "status": status,
        "cycles_included": len(chain),
    }


def progress_for(db: Session, program: NutritionProgramModel) -> dict:
    _finalize_if_due(db, program)
    days = _days(db, program.id)
    calendar = _calendar_state(program)
    completed_days = sum(1 for day in days if day.completed)
    total_tasks = sum(len(day.checklist or []) for day in days)
    completed_tasks = sum(sum(1 for item in (day.checklist_state or []) if bool(item)) for day in days)
    # Program progress is intentionally separate from goal achievement.
    pct = min(100.0, round((completed_days / program.duration_days) * 100, 2)) if program.duration_days else 0.0
    day_states = [get_day_availability(program, day) for day in days]
    missed_days = sum(1 for state in day_states if state["status"] == "MISSED")
    return {
        "program_id": program.id,
        "days_completed": completed_days,
        "total_days": program.duration_days,
        "completed_tasks": completed_tasks,
        "total_tasks": total_tasks,
        "progress_percent": pct,
        "current_day": calendar["current_day"],
        "time_elapsed_days": calendar["time_elapsed_days"],
        "missed_days": missed_days,
        "inactive_days": calendar["inactive_days"],
        "last_activity_at": calendar["last_activity_at"],
        "program_status": _normalized_status(program),
        "completed_at": program.completed_at,
        "goals": _sync_goals(db, program),
        "cumulative_goal": cumulative_goal_for(db, program),
        "goal_progress_percent": (_sync_goals(db, program)[0]["progress_percentage"] if _sync_goals(db, program) else 0.0),
    }


def _primary_goal(goals: list[dict]) -> dict | None:
    return goals[0] if goals else None


def serialize_summary(db: Session, program: NutritionProgramModel) -> dict:
    _finalize_if_due(db, program)
    progress = progress_for(db, program)
    primary = _primary_goal(progress["goals"])
    return {
        "id": program.id,
        "stage": program.stage,
        "title": program.title,
        "status": progress["program_status"],
        "duration_days": program.duration_days,
        "cycle_number": program.cycle_number,
        "parent_program_id": program.parent_program_id,
        "created_at": program.created_at,
        "started_at": program.started_at,
        "ends_at": program.ends_at,
        "completed_at": program.completed_at,
        "cancelled_at": program.cancelled_at,
        "current_day": progress["current_day"],
        "days_completed": progress["days_completed"],
        "completed_tasks": progress["completed_tasks"],
        "total_tasks": progress["total_tasks"],
        "progress_percent": progress["progress_percent"],
        "time_elapsed_days": progress["time_elapsed_days"],
        "missed_days": progress["missed_days"],
        "inactive_days": progress["inactive_days"],
        "last_activity_at": progress["last_activity_at"],
        "goal": primary,
        "cumulative_goal": progress["cumulative_goal"],
        "adaptive_mode": bool((program.program_config or {}).get("adaptive_mode")),
        "latest_decision": (program.program_config or {}).get("last_adaptation"),
        "post_block_choice": (program.program_config or {}).get("post_block_choice"),
    }


def _extension_chain(db: Session, program: NutritionProgramModel) -> list[dict]:
    return [serialize_summary(db, row) for row in _program_chain(db, program)]


def _serialize_day(program: NutritionProgramModel, day: NutritionProgramDayModel, logs: dict[str, NutritionMealLogModel], *, now: datetime | None = None) -> dict:
    availability = get_day_availability(program, day, now=now)
    if availability["status"] in {"AVAILABLE", "IN_PROGRESS"}:
        _ensure_personalized_day_payload(program, day)
    reveal_guidance = availability["status"] not in {"LOCKED", "MISSED"}
    log = logs.get(day.id)
    return {
        "id": day.id,
        "day_number": day.day_number,
        "focus": day.focus,
        "status": availability["status"],
        "unlock_at": availability["unlock_at"],
        "close_at": availability["close_at"],
        "remaining_seconds": availability["remaining_seconds"],
        "close_remaining_seconds": availability["close_remaining_seconds"],
        # Locked days expose only title/schedule metadata. The actual guidance is
        # returned only once the backend says the day is reviewable/available.
        "recommended_action": day.recommended_action if reveal_guidance else "",
        "meal_guidance": day.meal_guidance if reveal_guidance else "",
        "action_details": (day.action_details or {}) if reveal_guidance else {},
        "meal_guidance_details": (day.meal_guidance_details or {}) if reveal_guidance else {},
        "reference_notes": (day.reference_notes or []) if reveal_guidance else [],
        "checklist": (day.checklist or []) if reveal_guidance else [],
        "checklist_state": (day.checklist_state or [False] * len(day.checklist or [])) if reveal_guidance else [],
        "food_group_state": (day.food_group_state or []) if reveal_guidance else [],
        "has_complaint": day.has_complaint if reveal_guidance else None,
        "complaint_note": day.complaint_note if reveal_guidance else None,
        "completed": day.completed,
        "completed_at": day.completed_at,
        "locked": availability["status"] == "LOCKED",
        "missed": availability["status"] == "MISSED",
        "meal_label": log.meal_label if log and reveal_guidance else None,
        "meal_notes": log.notes if log and reveal_guidance else None,
        "task_results": ((day.action_details or {}).get("task_results") or {}) if reveal_guidance else {},
        "metric_results": ((day.action_details or {}).get("metric_results") or []) if reveal_guidance else [],
    }


def serialize_detail(db: Session, program: NutritionProgramModel) -> dict:
    base = serialize_summary(db, program)
    profile = db.get(NutritionProfileModel, program.profile_id)
    recommendation = db.get(NutritionRecommendationModel, program.recommendation_id)
    days = _days(db, program.id)
    logs = _meal_logs_by_day(db, program.id)
    rec_snapshot = program.recommendation_snapshot or recommendation.result_payload
    assessment_snapshot = program.assessment_snapshot or {
        "stage": profile.stage, "age_months": profile.age_months, "age_years": profile.age_years, "sex": profile.sex,
        "weight_kg": profile.weight_kg, "height_cm": profile.height_cm, **(profile.profile_payload or {}),
    }
    base.update({
        "profile": {"stage": profile.stage, "age_months": profile.age_months, "age_years": profile.age_years, "sex": profile.sex, "weight_kg": profile.weight_kg, "height_cm": profile.height_cm, **(profile.profile_payload or {})},
        "assessment_snapshot": assessment_snapshot,
        "recommendation": rec_snapshot,
        "goals": _sync_goals(db, program),
        "days": [_serialize_day(program, day, logs) for day in days],
        "extension_history": _extension_chain(db, program),
        "rule_version": (program.program_config or {}).get("adaptive_rule_version") if program.stage in {"mpasi", "toddler"} else None,
    })
    return base


def serialize_day_detail(db: Session, program: NutritionProgramModel, day_number: int) -> dict:
    _finalize_if_due(db, program)
    day = db.scalar(select(NutritionProgramDayModel).where(
        NutritionProgramDayModel.program_id == program.id,
        NutritionProgramDayModel.day_number == day_number,
    ))
    if not day:
        raise HTTPException(status_code=404, detail="Hari program tidak ditemukan.")
    progress = progress_for(db, program)
    logs = _meal_logs_by_day(db, program.id)
    goals = progress["goals"]
    return {
        "program_id": program.id,
        "program_title": program.title,
        "program_status": progress["program_status"],
        "duration_days": program.duration_days,
        "current_day": progress["current_day"],
        "progress_percent": progress["progress_percent"],
        "missed_days": progress["missed_days"],
        "inactive_days": progress["inactive_days"],
        "last_activity_at": progress["last_activity_at"],
        "goal": _primary_goal(goals),
        "cumulative_goal": progress["cumulative_goal"],
        "day": _serialize_day(program, day, logs),
    }


def _upsert_meal_log(db: Session, program: NutritionProgramModel, day: NutritionProgramDayModel, payload: DailyLogRequest) -> None:
    meal_label = (payload.meal_label or "").strip()
    meal_notes = (payload.meal_notes or "").strip()
    if not meal_label and not meal_notes:
        return
    existing = db.scalar(select(NutritionMealLogModel).where(NutritionMealLogModel.program_id == program.id, NutritionMealLogModel.program_day_id == day.id).order_by(NutritionMealLogModel.created_at.desc()))
    if existing:
        existing.meal_label = meal_label or existing.meal_label or "Catatan makan"
        existing.notes = meal_notes or None
        existing.logged_at = utcnow()
        existing.completed = True
    else:
        db.add(NutritionMealLogModel(program_id=program.id, program_day_id=day.id, meal_label=meal_label or "Catatan makan", notes=meal_notes or None, completed=True))


def _daily_log_payload(payload: DailyLogRequest) -> dict:
    return {
        "portion": payload.portion,
        "acceptance": payload.acceptance,
        "texture": payload.texture,
        "new_food": payload.new_food,
        "reaction": payload.reaction,
        "reaction_notes": (payload.reaction_notes or "").strip() or None,
        "child_condition": payload.child_condition,
        "health_condition": payload.health_condition,
        "appetite_status": payload.appetite_status,
        "eating_difficulty": payload.eating_difficulty,
        "routine_adherence": payload.routine_adherence,
        "caregiver_adherence": payload.caregiver_adherence,
        "hydration_status": payload.hydration_status,
        "eating_support": payload.eating_support,
        "eating_barrier": payload.eating_barrier,
        "parent_difficulty": payload.parent_difficulty,
        "available_ingredients": list(payload.available_ingredients or []),
        "budget_context": (payload.budget_context or "").strip() or None,
        "notes": (payload.notes or payload.meal_notes or "").strip() or None,
    }


def _recent_daily_logs(db: Session, program: NutritionProgramModel, *, before_day: int | None = None, limit: int = 7) -> list[dict]:
    rows = _days(db, program.id)
    output: list[dict] = []
    for row in rows:
        if before_day is not None and row.day_number >= before_day:
            continue
        log = (row.action_details or {}).get("daily_log")
        if isinstance(log, dict) and log:
            output.append(log)
    return output[-limit:]


def _recent_primary_adherence(
    db: Session,
    program: NutritionProgramModel,
    *,
    primary_metric: str,
    before_day: int | None = None,
    limit: int = 7,
) -> list[float]:
    """Read Stage 6 authoritative metric results without fabricating missing days."""
    values: list[float] = []
    for row in _days(db, program.id):
        if before_day is not None and row.day_number >= before_day:
            continue
        results = (row.action_details or {}).get("metric_results") or []
        metric_values = [
            float(item["adherence"])
            for item in results
            if str(item.get("metric_id") or "") == primary_metric and isinstance(item.get("adherence"), (int, float))
        ]
        if metric_values:
            values.append(sum(metric_values) / len(metric_values))
    return values[-limit:]


def _next_primary_metric(stage: str, current: str, decision: str) -> str:
    """Stage 7 never silently changes the primary goal/metric.

    ADVANCE means one small challenge inside the same goal. Goal changes belong
    to the explicit Block Review / Stage 8 flow.
    """
    return current


def _record_adaptation_history(
    program: NutritionProgramModel,
    current_day: NutritionProgramDayModel,
    *,
    decision: dict,
    indicators: dict,
    safety: dict,
    next_plan: dict | None,
    next_day: NutritionProgramDayModel | None = None,
) -> None:
    """Append one immutable, versioned Stage 7 decision to JSON audit history."""
    config = dict(program.program_config or {})
    history = list(config.get("decision_history") or [])
    # A completed day normally cannot be saved twice, but this guard protects
    # idempotency if the service is retried around a commit boundary.
    already_recorded = any(
        str(item.get("day_id") or "") == str(current_day.id)
        and str((item.get("decision") or {}).get("decision") or item.get("decision_type") or "") == str(decision.get("decision") or "")
        for item in history
    )
    if not already_recorded:
        history.append({
            "program_id": program.id,
            "day_id": current_day.id,
            "day": current_day.day_number,
            "decision_type": decision.get("decision"),
            "decision": decision,
            "reason": decision.get("reason_text") or decision.get("reason"),
            "reason_code": decision.get("reason_code"),
            "indicators": indicators,  # backward compatibility
            "indicator_snapshot": indicators,
            "safety": safety,  # backward compatibility
            "safety_state": safety,
            "rule_version": decision.get("rule_version") or {"id": decision.get("rule_version_id")},
            "previous_plan_id": current_day.id,
            "next_plan_id": next_day.id if next_day is not None else None,
            "next_plan": next_plan,
            "created_at": utcnow().isoformat(),
        })
    config["decision_history"] = history[-60:]
    config["last_adaptation"] = {"source_day": current_day.day_number, **decision}
    config["adaptive_rule_version"] = ADAPTIVE_RULE_VERSION
    program.program_config = config


def _apply_plan_to_day(program: NutritionProgramModel, next_day: NutritionProgramDayModel, *, primary_metric: str, decision: dict, log: dict, current_day_number: int) -> dict:
    profile_payload = program.assessment_snapshot or {}
    adjustment = plan_adjustments(str(decision.get("decision") or "CONTINUE"), log)
    strategy = str(adjustment.get("strategy") or "CONTINUE")
    payload = _day_payload(
        program.stage, next_day.day_number, program.recommendation_snapshot or {}, profile_payload,
        (program.program_config or {}).get("source_snapshot", []), primary_metric=primary_metric, adaptive_strategy=strategy
    )
    # Strategy changes the next plan itself, not only its explanation. These are
    # UX/product adjustments around an existing evidence-backed target; they do
    # not invent new clinical thresholds or nutrition targets.
    elderly = program.stage == "elderly"
    if strategy == "REPEAT":
        payload["focus"] = f"Ulangi fokus · {payload['focus']}"
        payload["recommended_action"] = f"Ulangi target yang sama tanpa menambah tantangan baru. {payload['recommended_action']}"
        payload["meal_guidance"] = (
            f"Pertahankan pilihan yang familiar dan realistis sesuai kemampuan makan hari ini. {payload['meal_guidance']}"
            if elderly else
            f"Gunakan pendekatan yang familiar dan ubah bentuk penyajian bila perlu sesuai kemampuan anak. {payload['meal_guidance']}"
        )
    elif strategy == "EASE":
        payload["focus"] = f"Fokus lebih ringan · {payload['focus']}"
        payload["recommended_action"] = f"Prioritaskan satu langkah inti dan hindari menambah kompleksitas hari ini. {payload['recommended_action']}"
        payload["meal_guidance"] = (
            f"Sederhanakan pilihan makan dan pertahankan pola yang paling mudah dijalankan hari ini. {payload['meal_guidance']}"
            if elderly else
            f"Utamakan makanan/bentuk yang lebih familiar dan tetap responsif tanpa memaksa. {payload['meal_guidance']}"
        )
    elif strategy == "ADVANCE":
        payload["recommended_action"] = (
            f"Tambahkan satu kebiasaan kecil yang masih realistis hari ini. {payload['recommended_action']}"
            if elderly else
            f"Tambahkan hanya satu tantangan kecil hari ini. {payload['recommended_action']}"
        )
    elif strategy == "BLOCK_REVIEW":
        payload["recommended_action"] = f"Pertahankan langkah yang aman sambil meninjau kembali target/strategi. {payload['recommended_action']}"
    payload["action_details"] = {
        **payload["action_details"],
        "planned": True,
        "adaptive_mode": True,
        "generated_from_day": current_day_number,
        "adaptation_context": adjustment,
        "why_this_plan": decision.get("user_facing_reason"),
        "decision": decision,
    }
    next_day.focus = payload["focus"]
    next_day.recommended_action = payload["recommended_action"]
    next_day.meal_guidance = payload["meal_guidance"]
    next_day.action_details = payload["action_details"]
    next_day.meal_guidance_details = payload["meal_guidance_details"]
    next_day.checklist = payload["checklist"]
    next_day.checklist_state = [False] * len(next_day.checklist)
    next_day.reference_notes = payload["reference_notes"]
    generated_tasks = list((next_day.action_details or {}).get("tasks") or [])
    primary_task = generated_tasks[0] if generated_tasks else {}
    support_tasks = generated_tasks[1:] if len(generated_tasks) > 1 else []
    return {
        "plan_id": next_day.id,
        "day_number": next_day.day_number,
        "focus": next_day.focus,
        "recommended_action": next_day.recommended_action,
        "strategy": adjustment.get("strategy"),
        "difficulty": adjustment.get("difficulty"),
        "primary_target_id": primary_task.get("metric_id") or primary_task.get("metric") or primary_metric,
        "actions": [task.get("action_text") or task.get("action") or task.get("target_label") for task in generated_tasks],
        "support_actions": [task.get("action_text") or task.get("action") or task.get("target_label") for task in support_tasks],
        "new_challenges": list(adjustment.get("new_challenges") or []),
        "why": decision.get("user_facing_reason"),
        "explanation": decision.get("explanation") or {},
    }


def _run_adaptive_loop(db: Session, program: NutritionProgramModel, current_day: NutritionProgramDayModel, *, log: dict, task_adherence: dict[str, float]) -> dict:
    if program.stage not in {"mpasi", "toddler", "elderly"}:
        return {"indicators": {}, "safety": {}, "adaptation": {}, "daily_summary": {}, "next_day_plan": None}

    tasks = (current_day.action_details or {}).get("tasks") or []
    primary_metric = str(tasks[0].get("metric_id") or tasks[0].get("metric") if tasks else (_goals(db, program.id)[0].goal_key if _goals(db, program.id) else ""))
    previous_logs = _recent_daily_logs(db, program, before_day=current_day.day_number, limit=7)
    previous_adherence = _recent_primary_adherence(
        db, program, primary_metric=primary_metric, before_day=current_day.day_number, limit=7
    )

    # Safety is always evaluated before any optimization/progression decision.
    pre_safety = safety_guard(log, program.assessment_snapshot or {}, stage=program.stage)
    primary_adherence = {
        str(task.get("key") or task.get("id")): task_adherence.get(str(task.get("key") or task.get("id")), 0.0)
        for task in tasks
        if str(task.get("metric_id") or task.get("metric") or "") == primary_metric
        and str(task.get("key") or task.get("id")) in task_adherence
    }
    indicator_fn = calculate_elderly_indicators if program.stage == "elderly" else calculate_indicators
    indicators = indicator_fn(
        log,
        previous_logs,
        goal_metric=primary_metric,
        task_adherence=primary_adherence,
        recent_adherence_history=previous_adherence,
        rule_version=ADAPTIVE_RULE_VERSION,
    )
    prior_history = list((program.program_config or {}).get("decision_history") or [])
    previous_decision = ((prior_history[-1].get("decision") or {}).get("decision") if prior_history else None)
    decision_fn = decide_elderly_adaptation if program.stage == "elderly" else decide_adaptation
    decision = decision_fn(
        safety=pre_safety,
        indicators=indicators,
        current_log=log,
        recent_logs=previous_logs,
        day_number=current_day.day_number,
        previous_decision=previous_decision,
        block_days=program.duration_days,
        rule_version=ADAPTIVE_RULE_VERSION,
    )

    next_day = db.scalar(select(NutritionProgramDayModel).where(
        NutritionProgramDayModel.program_id == program.id,
        NutritionProgramDayModel.day_number == current_day.day_number + 1,
    ))
    next_preview = "Block selesai; lanjut ke review program." if next_day is None else "Rencana berikutnya belum dibuat karena safety hold."
    next_day_plan = None
    post_safety = pre_safety

    if next_day is not None and decision.get("decision") not in {"PAUSE", "REFER", "BLOCK_REVIEW"}:
        # Primary goal/metric remains stable. ADVANCE only changes one small
        # challenge/difficulty inside the same goal.
        next_metric = _next_primary_metric(program.stage, primary_metric, str(decision.get("decision")))
        next_day_plan = _apply_plan_to_day(
            program, next_day, primary_metric=next_metric, decision=decision, log=log, current_day_number=current_day.day_number
        )
        post_safety = safety_guard(log, program.assessment_snapshot or {}, generated_plan=next_day_plan, stage=program.stage)
        if post_safety.get("blocked"):
            decision = decide_adaptation(
                safety=post_safety,
                indicators=indicators,
                current_log=log,
                recent_logs=previous_logs,
                day_number=current_day.day_number,
                previous_decision=previous_decision,
                block_days=program.duration_days,
                rule_version=ADAPTIVE_RULE_VERSION,
            )
            next_day.recommended_action = ""
            next_day.meal_guidance = ""
            next_day.action_details = {
                "planned": False,
                "adaptive_mode": True,
                "generated_from_day": current_day.day_number,
                "safety_hold": post_safety,
            }
            next_day.meal_guidance_details = {}
            next_day.checklist = []
            next_day.checklist_state = []
            next_day_plan = None
        else:
            next_preview = f"{next_day.focus}: {next_day.recommended_action}"
    elif decision.get("decision") == "BLOCK_REVIEW":
        next_preview = "Cycle selesai. Tinjau hasil block sebelum menentukan langkah berikutnya."

    if decision.get("decision") == "PAUSE":
        program.status = "PAUSED"
        cfg = dict(program.program_config or {})
        cfg["paused_at"] = utcnow().isoformat()
        cfg["pause_reason"] = "safety_recovery"
        program.program_config = cfg
    elif decision.get("decision") == "REFER":
        program.status = "SAFETY_HOLD"
        cfg = dict(program.program_config or {})
        cfg["paused_at"] = utcnow().isoformat()
        cfg["safety_hold_source_day"] = current_day.day_number
        cfg["safety_hold_red_flags"] = list(pre_safety.get("red_flags") or [])
        program.program_config = cfg

    safety = {"before_adaptation": pre_safety, "after_plan_generation": post_safety}
    summary = daily_summary(log, indicators, decision, next_preview)
    _record_adaptation_history(
        program,
        current_day,
        decision=decision,
        indicators=indicators,
        safety=safety,
        next_plan=next_day_plan,
        next_day=next_day,
    )
    return {
        "indicators": indicators,
        "safety": safety,
        "adaptation": decision,
        "daily_summary": summary,
        "next_day_plan": next_day_plan,
    }

def apply_daily_log(db: Session, program: NutritionProgramModel, payload: DailyLogRequest) -> dict:
    _finalize_if_due(db, program)
    status = _normalized_status(program)
    if status == "CANCELLED":
        raise _program_error(409, "PROGRAM_CANCELLED", "Program sudah dibatalkan dan hanya tersedia sebagai history.")
    if program.completed_at is not None or status != "ACTIVE":
        raise _program_error(409, "PROGRAM_COMPLETED", "Program sudah selesai dan progress lama tidak dapat diubah.")

    day = db.scalar(select(NutritionProgramDayModel).where(
        NutritionProgramDayModel.program_id == program.id,
        NutritionProgramDayModel.day_number == payload.day_number,
    ))
    if not day:
        raise HTTPException(status_code=404, detail="Hari program tidak ditemukan.")

    availability = get_day_availability(program, day)
    if availability["status"] == "LOCKED":
        raise _program_error(409, "PROGRAM_DAY_LOCKED", "Hari program ini belum tersedia sesuai jadwal unlock.")
    if availability["status"] == "MISSED":
        raise _program_error(409, "PROGRAM_DAY_CLOSED", "Hari yang sudah lewat tercatat sebagai missed dan tidak dapat diubah kembali.")
    if availability["status"] == "COMPLETED":
        raise _program_error(409, "PROGRAM_DAY_FINALIZED", "Hari ini sudah selesai dan tersedia sebagai review saja.")

    _ensure_personalized_day_payload(program, day)
    expected = len(day.checklist or [])
    if len(payload.checklist_state) != expected:
        raise HTTPException(status_code=422, detail=f"Checklist harus memiliki {expected} item.")

    complaint_note = (payload.complaint_note or "").strip()
    reaction_notes = (payload.reaction_notes or "").strip()
    if program.stage in {"mpasi", "toddler"} and payload.reaction == "detected" and not reaction_notes:
        raise HTTPException(status_code=422, detail="Jelaskan reaksi tidak biasa yang terlihat agar safety check dapat dilakukan.")
    task_specs = ((day.action_details or {}).get("tasks") or [])
    incoming_results = dict(payload.task_results or {})

    # The checkbox records whether the caregiver completed/attempted the action.
    # It is deliberately independent from the measurable result: a target may be
    # attempted and saved even when the actual result is below target.
    action_checks = [bool(value) for value in payload.checklist_state]
    reflection_complete = payload.has_complaint is not None and (payload.has_complaint is False or bool(complaint_note))
    daily_log = _daily_log_payload(payload)
    safety_enabled = program.stage in {"mpasi", "toddler", "elderly"}
    pre_save_safety = (
        safety_guard(daily_log, program.assessment_snapshot or {}, stage=program.stage)
        if safety_enabled
        else {}
    )
    safety_blocked = bool(pre_save_safety.get("blocked"))
    # A safety pause/hold preserves every saved answer but never finalizes the
    # day. The user must resume the same day and finish it under ACTIVE state.
    requested_completed = bool(expected and all(action_checks) and reflection_complete and not safety_blocked)

    save_time = utcnow()
    task_adherence: dict[str, float] = {}
    details = dict(day.action_details or {})
    metric_results: list[dict] = list(details.get("metric_results") or [])
    if task_specs and incoming_results:
        try:
            if safety_blocked:
                normalized_results, new_metric_results, task_adherence = evaluate_partial_daily_results(
                    list(task_specs),
                    incoming_results,
                    action_checks,
                    saved_at=save_time,
                    previous_task_results=dict(details.get("task_results") or {}),
                    previous_metric_results=metric_results,
                )
            else:
                normalized_results, new_metric_results, task_adherence = evaluate_daily_results(
                    list(task_specs),
                    incoming_results,
                    action_checks,
                    saved_at=save_time,
                    previous_metric_results=metric_results,
                )
        except DailyResultValidationError as exc:
            raise HTTPException(status_code=422, detail=f"Hasil aktual tidak valid untuk {exc.task_id}: {exc.message}") from exc
        # Only backend-normalized values are persisted. Unknown client task IDs
        # are ignored because the server-side task definition is authoritative.
        details["task_results"] = normalized_results
        details["last_saved_task_adherence"] = task_adherence
        details["metric_results"] = new_metric_results
        details["last_saved_at"] = save_time.isoformat()
        metric_results = new_metric_results
    elif task_specs:
        # Backward compatibility for pre-Stage-6 clients that still save only
        # checklist/reflection data. No result/adherence is fabricated.
        task_adherence = {
            str(row.get("task_id")): float(row["adherence"])
            for row in metric_results
            if row.get("task_id") and row.get("adherence") is not None
        }
    day.checklist_state = action_checks
    details["daily_log"] = daily_log
    day.action_details = details
    day.food_group_state = [bool(value) for value in payload.food_group_state]
    day.has_complaint = payload.has_complaint
    day.complaint_note = complaint_note if payload.has_complaint else None
    day.completed = requested_completed
    day.completed_at = (day.completed_at or save_time) if requested_completed else None
    program.last_activity_at = save_time
    _upsert_meal_log(db, program, day, payload)
    db.flush()

    # Day completion never advances the calendar clock. Day N+1 remains locked
    # until its own unlock timestamp. Completing the final scheduled day closes
    # the program; earlier missed days remain missed.
    if day.day_number == program.duration_days and requested_completed:
        program.status = "COMPLETED"
        program.completed_at = program.completed_at or save_time
    _sync_goals(db, program, persist=True)
    child_adaptive = program.stage in {"mpasi", "toddler"}
    daily_adaptive = program.stage in {"mpasi", "toddler", "elderly"}
    if requested_completed:
        adaptive = _run_adaptive_loop(db, program, day, log=daily_log, task_adherence=task_adherence)
    else:
        adaptation: dict = {}
        partial_indicators: dict = {}
        if safety_enabled and pre_save_safety.get("blocked"):
            # Safety override is event-driven and does not wait for checklist
            # completion. Normal adaptive decisions remain child-only; Lansia
            # reuses the same program state machine without copying pediatric
            # progression rules.
            if child_adaptive:
                tasks = (day.action_details or {}).get("tasks") or []
                primary_metric = str(
                    (tasks[0].get("metric_id") or tasks[0].get("metric"))
                    if tasks
                    else (_goals(db, program.id)[0].goal_key if _goals(db, program.id) else "")
                )
                previous_logs = _recent_daily_logs(db, program, before_day=day.day_number, limit=7)
                previous_adherence = _recent_primary_adherence(
                    db, program, primary_metric=primary_metric, before_day=day.day_number, limit=7
                )
                primary_adherence = {
                    str(task.get("key") or task.get("id")): task_adherence[str(task.get("key") or task.get("id"))]
                    for task in tasks
                    if str(task.get("metric_id") or task.get("metric") or "") == primary_metric
                    and str(task.get("key") or task.get("id")) in task_adherence
                }
                partial_indicators = calculate_indicators(
                    daily_log,
                    previous_logs,
                    goal_metric=primary_metric,
                    task_adherence=primary_adherence,
                    recent_adherence_history=previous_adherence,
                    rule_version=ADAPTIVE_RULE_VERSION,
                )
                prior_history = list((program.program_config or {}).get("decision_history") or [])
                previous_decision = ((prior_history[-1].get("decision") or {}).get("decision") if prior_history else None)
                adaptation = decide_adaptation(
                    safety=pre_save_safety,
                    indicators=partial_indicators,
                    current_log=daily_log,
                    recent_logs=previous_logs,
                    day_number=day.day_number,
                    previous_decision=previous_decision,
                    block_days=program.duration_days,
                    rule_version=ADAPTIVE_RULE_VERSION,
                )
            else:
                adaptation = {
                    "decision": str(pre_save_safety.get("decision") or "PAUSE"),
                    "reason_code": "SAFETY_RECOVERY",
                    "reason": str(pre_save_safety.get("reason") or "Kondisi harian membutuhkan jeda program."),
                    "reason_text": str(pre_save_safety.get("reason") or "Kondisi harian membutuhkan jeda program."),
                    "user_facing_reason": str(pre_save_safety.get("user_facing_reason") or "Program dijeda sementara."),
                    "rule_version": {"id": "shared_program_safety_state_v1", "version": "1.0.0"},
                    "explanation": {
                        "what_changed": "Program dijeda sementara.",
                        "why": str(pre_save_safety.get("user_facing_reason") or "Kondisi harian membutuhkan jeda."),
                        "what_next": "Lanjutkan dari hari yang sama setelah kondisi membaik.",
                    },
                }

            if adaptation.get("decision") == "REFER":
                program.status = "SAFETY_HOLD"
                cfg = dict(program.program_config or {})
                cfg["paused_at"] = save_time.isoformat()
                cfg["safety_hold_source_day"] = day.day_number
                cfg["safety_hold_red_flags"] = list(pre_save_safety.get("red_flags") or [])
                cfg["safety_state_stage"] = program.stage
                program.program_config = cfg
            elif adaptation.get("decision") == "PAUSE":
                program.status = "PAUSED"
                cfg = dict(program.program_config or {})
                cfg["paused_at"] = save_time.isoformat()
                cfg["pause_reason"] = "safety_recovery"
                cfg["pause_source_day"] = day.day_number
                cfg["safety_state_stage"] = program.stage
                program.program_config = cfg
            safety_payload = {"before_adaptation": pre_save_safety, "after_plan_generation": pre_save_safety}
            if child_adaptive:
                _record_adaptation_history(
                    program, day, decision=adaptation, indicators=partial_indicators, safety=safety_payload, next_plan=None
                )
        adaptive = {
            "indicators": partial_indicators,
            "safety": ({"before_adaptation": pre_save_safety, "after_plan_generation": pre_save_safety} if safety_enabled else {}),
            "adaptation": adaptation,
            "daily_summary": {},
            "next_day_plan": None,
        }
    if safety_enabled:
        details = dict(day.action_details or {})
        if daily_adaptive:
            details["indicators"] = adaptive["indicators"]
            details["daily_summary"] = adaptive["daily_summary"]
        details["safety"] = adaptive["safety"]
        details["adaptation"] = adaptive["adaptation"]
        day.action_details = details
    db.commit()
    db.refresh(day)
    db.refresh(program)
    progress = progress_for(db, program)
    return {
        **progress,
        "saved": True,
        "saved_at": save_time,
        "day_number": day.day_number,
        "day_completed": day.completed,
        "day_completed_at": day.completed_at,
        "checklist_state": day.checklist_state or [],
        "food_group_state": day.food_group_state or [],
        "has_complaint": day.has_complaint,
        "complaint_note": day.complaint_note,
        "task_results": ((day.action_details or {}).get("task_results") or {}),
        "metric_results": ((day.action_details or {}).get("metric_results") or []),
        "indicators": adaptive.get("indicators") or {},
        "safety": adaptive.get("safety") or {},
        "adaptation": adaptive.get("adaptation") or {},
        "daily_summary": adaptive.get("daily_summary") or {},
        "next_day_plan": adaptive.get("next_day_plan"),
    }


def active_rule_version() -> dict:
    return ADAPTIVE_RULE_VERSION


def pause_program(db: Session, program: NutritionProgramModel, *, confirm: bool) -> NutritionProgramModel:
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan untuk menjeda program.")
    if _normalized_status(program) != "ACTIVE":
        raise _program_error(409, "PROGRAM_NOT_ACTIVE", "Hanya program aktif yang dapat dijeda.")
    now = utcnow()
    config = dict(program.program_config or {})
    config["paused_at"] = now.isoformat()
    config["pause_reason"] = "manual"
    program.program_config = config
    program.status = "PAUSED"
    db.commit(); db.refresh(program)
    return program


def resume_program(
    db: Session,
    program: NutritionProgramModel,
    *,
    confirm: bool,
    recovery_status: str | None = None,
) -> NutritionProgramModel:
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan untuk melanjutkan program.")
    if _normalized_status(program) == "SAFETY_HOLD":
        raise _program_error(409, "SAFETY_REVIEW_REQUIRED", "Program dalam safety hold dan tidak dapat dilanjutkan melalui resume biasa.")
    if _normalized_status(program) != "PAUSED":
        raise _program_error(409, "PROGRAM_NOT_PAUSED", "Program tidak sedang dijeda.")

    now = utcnow()
    config = dict(program.program_config or {})
    pause_reason = str(config.get("pause_reason") or "manual")

    # Safety-triggered pauses require an explicit recovery check. A manual
    # pause keeps backward compatibility: confirm=true without this field may
    # resume as before.
    if pause_reason == "safety_recovery" and recovery_status not in {"improved", "still_unwell"}:
        raise _program_error(422, "RECOVERY_CHECK_REQUIRED", "Pilih kondisi sekarang sebelum melanjutkan program.")

    if recovery_status == "still_unwell":
        config["last_resume_check"] = {
            "checked_at": now.isoformat(),
            "status": "still_unwell",
            "result": "remain_paused",
        }
        program.program_config = config
        db.commit(); db.refresh(program)
        return program

    if recovery_status == "improved":
        config["last_resume_check"] = {
            "checked_at": now.isoformat(),
            "status": "improved",
            "result": "resume_allowed",
            "stage": program.stage,
        }

    paused_at_raw = config.get("paused_at")
    if paused_at_raw:
        try:
            paused_at = _as_utc(datetime.fromisoformat(str(paused_at_raw)))
            delta = max(timedelta(0), _as_utc(now) - paused_at)
            # Shift the schedule by exactly the paused duration. This keeps the
            # same current day and prevents an automatic jump to Day N+1.
            program.started_at = _as_utc(program.started_at) + delta
            program.ends_at = _as_utc(program.ends_at) + delta
        except ValueError:
            pass
    config.pop("paused_at", None)
    config.pop("pause_reason", None)
    config["resumed_at"] = now.isoformat()
    program.program_config = config
    program.status = "ACTIVE"
    program.last_activity_at = now
    db.commit(); db.refresh(program)
    return program

def review_safety_hold(
    db: Session,
    program: NutritionProgramModel,
    *,
    confirm: bool,
    action: str,
    goal_key: str | None = None,
) -> NutritionProgramModel:
    """Archive a SAFETY_HOLD program before a fresh assessment.

    A safety hold caused by a red flag cannot be resolved by lowering or
    changing the goal. The held cycle stays frozen until the caregiver
    explicitly archives it and starts a new assessment after the child has
    received appropriate medical evaluation.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan sebelum memulai asesmen ulang.")
    if _normalized_status(program) != "SAFETY_HOLD":
        raise _program_error(409, "PROGRAM_NOT_IN_SAFETY_HOLD", "Program tidak sedang berada dalam safety hold.")
    if action != "restart_assessment":
        raise HTTPException(status_code=422, detail="Safety hold karena red flag hanya dapat dilanjutkan melalui asesmen ulang.")

    now = utcnow()
    config = dict(program.program_config or {})
    goals = _goals(db, program.id)
    primary = goals[0] if goals else None
    review_entry = {
        "action": "restart_assessment",
        "reviewed_at": now.isoformat(),
        "previous_goal_key": primary.goal_key if primary else None,
        "result": "program_archived_for_new_assessment",
        "reason": "red_flag_requires_new_assessment",
    }
    history = list(config.get("safety_review_history") or [])
    history.append(review_entry)
    config["safety_review_history"] = history[-20:]
    config["last_safety_review"] = review_entry
    program.program_config = config
    program.status = "CANCELLED"
    program.cancelled_at = now
    program.last_activity_at = now
    db.commit()
    db.refresh(program)
    return program

def skip_current_day(db: Session, program: NutritionProgramModel, *, confirm: bool) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan untuk melewati hari ini.")
    if _normalized_status(program) != "ACTIVE":
        raise _program_error(409, "PROGRAM_NOT_ACTIVE", "Hari hanya dapat dilewati saat program aktif.")
    current_day_number = _calendar_state(program)["current_day"]
    day = db.scalar(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program.id, NutritionProgramDayModel.day_number == current_day_number))
    if not day or day.completed:
        raise _program_error(409, "PROGRAM_DAY_NOT_SKIPPABLE", "Hari ini tidak dapat dilewati.")
    details = dict(day.action_details or {})
    details["manual_skip"] = True
    details["missed_reason"] = "user_skipped"
    day.action_details = details
    program.last_activity_at = utcnow()
    next_day = db.scalar(select(NutritionProgramDayModel).where(NutritionProgramDayModel.program_id == program.id, NutritionProgramDayModel.day_number == current_day_number + 1))
    if program.stage in {"mpasi", "toddler"}:
        primary = _goals(db, program.id)[0].goal_key if _goals(db, program.id) else (preferred_mpasi_metric(program.assessment_snapshot or {}) if program.stage == "mpasi" else preferred_toddler_metric(program.assessment_snapshot or {}))
        previous_logs = _recent_daily_logs(db, program, before_day=current_day_number, limit=7)
        previous_adherence = _recent_primary_adherence(db, program, primary_metric=primary, before_day=current_day_number, limit=7)
        indicators = calculate_indicators(
            {}, previous_logs, goal_metric=primary, task_adherence={}, recent_adherence_history=previous_adherence, rule_version=ADAPTIVE_RULE_VERSION
        )
        fallback_decision = missing_day_decision(indicators, rule_version=ADAPTIVE_RULE_VERSION)
        next_plan = None
        if next_day is not None:
            next_plan = _apply_plan_to_day(program, next_day, primary_metric=primary, decision=fallback_decision, log={}, current_day_number=current_day_number)
        safety = {
            "before_adaptation": {"level": "CLEAR", "blocked": False, "decision": None, "reason": "Tidak ada daily result untuk dievaluasi.", "user_facing_reason": "Hari dilewati tanpa data hasil aktual."},
            "after_plan_generation": {"level": "CLEAR", "blocked": False, "decision": None},
        }
        _record_adaptation_history(
            program, day, decision=fallback_decision, indicators=indicators, safety=safety, next_plan=next_plan, next_day=next_day
        )
    db.commit()
    return progress_for(db, program)


def block_review(db: Session, program: NutritionProgramModel) -> dict:
    evaluation = evaluate_program(db, program)
    review = dict((evaluation.get("details") or {}).get("block_review") or {})
    if not review:
        progress = progress_for(db, program)
        review = _build_stage8_review(program, evaluation.get("details") or {}, progress)
        review = _persist_stage8_review(program, review)
        db.commit()
    # Backward-compatible aliases retained for the existing frontend while the
    # richer Stage 8 contract is exposed in the same response.
    return {
        **review,
        "what_improved": " ".join(review.get("what_improved") or []),
        "what_remains": " ".join(review.get("what_remains") or []),
        "safety": dict(review.get("safety_summary") or {}),
    }

def cancel_program(db: Session, program: NutritionProgramModel, *, confirm: bool) -> NutritionProgramModel:
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan sebelum membatalkan program.")
    _finalize_if_due(db, program)
    status = _normalized_status(program)
    if status not in {"ACTIVE", "SAFETY_HOLD"} or program.completed_at is not None:
        raise _program_error(409, "PROGRAM_NOT_CANCELLABLE", "Hanya program aktif atau program dalam safety hold yang dapat diarsipkan.")
    now = utcnow()
    if status == "SAFETY_HOLD":
        cfg = dict(program.program_config or {})
        cfg["last_safety_review"] = {
            "action": "restart_assessment",
            "reviewed_at": now.isoformat(),
            "result": "program_archived_for_new_assessment",
            "reason": "red_flag_requires_new_assessment",
        }
        program.program_config = cfg
    program.status = "CANCELLED"
    program.cancelled_at = now
    _sync_goals(db, program, persist=True)
    db.commit()
    db.refresh(program)
    return program


def delete_cancelled_program(db: Session, program: NutritionProgramModel) -> None:
    """Permanently remove a user-owned program only after explicit cancellation.

    The API performs ownership verification before calling this function. Database
    foreign keys cascade program-owned days/goals/logs/evaluations/extensions while
    shared profile/recommendation records remain intact.
    """
    if _normalized_status(program) != "CANCELLED" or program.cancelled_at is None:
        raise _program_error(409, "PROGRAM_NOT_CANCELLED", "Program harus dibatalkan terlebih dahulu sebelum dapat dihapus.")
    db.delete(program)
    db.commit()


def _metric_label(metric: str) -> str:
    return {
        "meal_frequency": "Frekuensi makan",
        "animal_source_food": "Paparan protein hewani",
        "fruit_vegetable": "Paparan sayur/buah",
        "dietary_diversity": "Keragaman pangan",
        "responsive_feeding": "Responsive feeding",
        "texture": "Tekstur sesuai tahap",
        "food_response": "Respons terhadap paparan makanan",
        "meal_routine": "Rutinitas makan",
        "sweet_beverage": "Paparan minuman berpemanis",
        "vegetable_fruit_exposure": "Paparan sayur/buah",
        "self_feeding": "Kesempatan makan mandiri",
        "protein_presence": "Protein pada makan utama",
        "elderly_meal_routine": "Keteraturan waktu makan",
        "elderly_context_focus": "Fokus pola makan",
        "elderly_daily_experience": "Kemudahan menjalankan rencana",
        "elderly_meal_quality": "Kesesuaian pilihan makan",
        "elderly_small_step": "Langkah kecil tambahan",
        "elderly_hydration_routine": "Keteraturan minum",
        "elderly_eating_support": "Dukungan makan/minum",
    }.get(metric, metric.replace("_", " ").title())


def _stage8_block_complete(program: NutritionProgramModel) -> bool:
    return bool(
        int(program.duration_days) == 14
        and program.completed_at is not None
        and _normalized_status(program) in {"COMPLETED", "EXTENDED"}
    )


def _stage8_metric_trend(rows: list[dict], metric: str) -> dict:
    values = [
        float(row["adherence"])
        for row in rows
        if str(row.get("metric_id") or row.get("metric") or "") == metric and row.get("adherence") is not None
    ]
    if len(values) < 2:
        return {
            "status": "INSUFFICIENT_DATA",
            "direction": "INSUFFICIENT_DATA",
            "early": None,
            "recent": None,
            "observations": len(values),
            "message": "Belum ada data yang cukup untuk melihat tren.",
        }
    split = max(1, len(values) // 2)
    early_values = values[:split]
    recent_values = values[split:]
    if not recent_values:
        recent_values = values[-1:]
    early = round(sum(early_values) / len(early_values), 1)
    recent = round(sum(recent_values) / len(recent_values), 1)
    delta = recent - early
    direction = "IMPROVING" if delta >= 5 else "DECLINING" if delta <= -5 else "STABLE"
    message = {
        "IMPROVING": "Adherence meningkat pada bagian akhir block.",
        "DECLINING": "Adherence menurun pada bagian akhir block dan masih perlu ditinjau.",
        "STABLE": "Adherence relatif stabil sepanjang data yang tersedia.",
    }[direction]
    return {
        "status": "AVAILABLE",
        "direction": direction,
        "early": early,
        "recent": recent,
        "delta": round(delta, 1),
        "observations": len(values),
        "message": message,
    }


def _stage8_safety_summary(program: NutritionProgramModel, decision_history: list[dict]) -> dict:
    events: list[dict] = []
    for row in decision_history:
        safety = dict(row.get("safety_state") or row.get("safety") or {})
        for phase in ("before_adaptation", "after_plan_generation"):
            item = dict(safety.get(phase) or {})
            if item.get("blocked"):
                events.append({
                    "day": row.get("day"),
                    "level": item.get("level"),
                    "decision": item.get("decision"),
                    "reason": item.get("user_facing_reason") or item.get("reason"),
                })
    status = _normalized_status(program)
    active = status in {"SAFETY_HOLD", "PAUSED"}
    current_decision = "REFER" if status == "SAFETY_HOLD" else "PAUSE" if status == "PAUSED" else None
    return {
        "active": active,
        "decision": current_decision,
        "event_count": len(events),
        "events": events,
        "summary": (
            "Safety condition masih aktif sehingga optimasi goal dihentikan."
            if active
            else ("Safety event pernah tercatat dan tetap tersedia dalam riwayat." if events else "Tidak ada safety event yang memblokir evaluasi normal.")
        ),
    }


def _stage8_review_key(program: NutritionProgramModel) -> str:
    completed = program.completed_at.isoformat() if program.completed_at else "in-progress"
    return f"cycle:{program.cycle_number}:days:{program.duration_days}:completed:{completed}:rule:{STAGE8_RULE_VERSION}"


def _find_stage8_final_evaluation(db: Session, program: NutritionProgramModel) -> NutritionEvaluationModel | None:
    if not _stage8_block_complete(program):
        return None
    rows = list(db.scalars(
        select(NutritionEvaluationModel)
        .where(NutritionEvaluationModel.program_id == program.id)
        .order_by(NutritionEvaluationModel.created_at.desc())
    ))
    key = _stage8_review_key(program)
    for row in rows:
        details = row.details or {}
        if details.get("stage8_rule_version") == STAGE8_RULE_VERSION and details.get("block_review_key") == key:
            return row
    return None


def _stage8_decision(*, block_complete: bool, goal_status: str, behavioral_adherence: float, trend_direction: str, safety: dict) -> str:
    if safety.get("active"):
        return str(safety.get("decision") or "REFER")
    if not block_complete:
        return "CONTINUE"
    if goal_status == "MET":
        return "COMPLETE"
    if goal_status == "PARTIALLY_MET":
        return "EXTEND"
    if behavioral_adherence >= 50 and trend_direction == "IMPROVING":
        return "CONTINUE"
    return "REFRAME"


def _build_stage8_review(program: NutritionProgramModel, details: dict, progress: dict) -> dict:
    goals = list(details.get("goals") or [])
    primary = _primary_goal(goals)
    daily_history = list(details.get("daily_metric_history") or [])
    behavior_metrics = dict(details.get("behavior_metrics") or {})
    decision_history = list(details.get("decision_history") or [])
    primary_metric = str((primary or {}).get("goal_key") or "")
    primary_trend = _stage8_metric_trend(daily_history, primary_metric) if primary_metric else {
        "status": "INSUFFICIENT_DATA", "direction": "INSUFFICIENT_DATA", "early": None, "recent": None,
        "observations": 0, "message": "Belum ada data yang cukup untuk melihat tren."
    }
    trends = {metric: _stage8_metric_trend(daily_history, metric) for metric in behavior_metrics}
    safety = _stage8_safety_summary(program, decision_history)
    block_complete = _stage8_block_complete(program)
    goal_status = str((primary or {}).get("status") or "NOT_MET")
    overall = float(details.get("overall_behavioral_adherence") or 0.0)
    has_actual_daily_results = any(
        row.get("actual_result", row.get("actual")) is not None
        for row in daily_history
    )
    decision = _stage8_decision(
        block_complete=block_complete,
        goal_status=goal_status,
        behavioral_adherence=overall,
        trend_direction=str(primary_trend.get("direction") or "INSUFFICIENT_DATA"),
        safety=safety,
    )
    # Elderly programs use both cycle completion and measured daily adherence.
    # Completing all scheduled days does not automatically mean the behavioral
    # pattern is already consistent enough to end guidance.
    elderly_behavioral_gap = bool(
        program.stage == "elderly"
        and block_complete
        and has_actual_daily_results
        and overall < 80
        and not safety.get("active")
    )
    if elderly_behavioral_gap:
        decision = "EXTEND" if overall >= 50 else "REFRAME"

    metric_summary: list[dict] = []
    for metric, bucket in behavior_metrics.items():
        rows = [row for row in daily_history if str(row.get("metric_id") or row.get("metric") or "") == metric]
        target = next((row.get("target") for row in rows if row.get("target") is not None), None)
        unit = next((row.get("unit") for row in rows if row.get("unit")), None)
        metric_summary.append({
            "metric": metric,
            "label": bucket.get("label") or _metric_label(metric),
            "target": target,
            "unit": unit,
            "actual": int(bucket.get("met_days", 0)),
            "observed_days": int(bucket.get("scored_days", 0)),
            "assigned_days": int(bucket.get("assigned_days", 0)),
            "adherence": float(bucket.get("adherence_percentage", 0.0)),
            "status": str(bucket.get("status") or behavioral_status(float(bucket.get("adherence_percentage", 0.0)))),
            "trend": trends.get(metric),
        })

    improved = [
        f"{item['label']} lebih konsisten ({item['adherence']:.0f}% adherence)."
        for item in metric_summary if item["adherence"] >= 80
    ]
    remains = [
        f"{item['label']} masih perlu dilanjutkan ({item['adherence']:.0f}% adherence)."
        for item in metric_summary if item["adherence"] < 80
    ]
    if not improved:
        improved = ["Tidak ada perubahan yang cukup konsisten untuk diringkas."]
    if not remains:
        remains = ["Tidak ada area goal-related yang masih berada di bawah threshold produk pada data yang tersedia."]

    next_focus = str(details.get("next_focus") or ((primary or {}).get("title") if primary else "Tinjau target berikutnya"))
    if safety.get("active"):
        next_focus = "Selesaikan langkah safety yang diperlukan dan lakukan asesmen ulang sebelum program berikutnya."
    elif decision == "COMPLETE":
        next_focus = f"Pertahankan {str((primary or {}).get('title') or 'kebiasaan utama').lower()} dan pilih goal berikutnya hanya jika diperlukan."
    elif decision == "EXTEND":
        next_focus = f"Lanjutkan {next_focus.lower()} pada cycle berikutnya bila caregiver memilih extension."
    elif decision == "REFRAME":
        next_focus = f"Sesuaikan strategi pada {next_focus.lower()} sebelum memulai cycle berikutnya."
    elif decision == "CONTINUE" and block_complete:
        next_focus = f"Pertahankan strategi pada {next_focus.lower()} dan tinjau kembali setelah data tambahan tersedia."

    options = {
        "COMPLETE": ["next_goal"],
        "EXTEND": ["same_goal", "smaller_goal", "different_goal"],
        "REFRAME": ["smaller_goal", "different_goal", "same_goal"],
        "CONTINUE": ["same_goal", "smaller_goal", "different_goal"] if block_complete else [],
        "REFER": [],
        "PAUSE": [],
    }.get(decision, [])
    return {
        "program_id": program.id,
        "block_number": int(program.cycle_number),
        "duration_days": int(program.duration_days),
        "block_completed": block_complete,
        "review_status": "BLOCK_COMPLETED" if block_complete else "BLOCK_IN_PROGRESS",
        "program_progress": {
            "completed_days": int(progress.get("days_completed", 0)),
            "planned_days": int(progress.get("total_days", program.duration_days)),
            "percent": float(progress.get("progress_percent", 0.0)),
        },
        "goal_progress": {
            "metric": primary_metric or None,
            "target": (primary or {}).get("target"),
            "actual": (primary or {}).get("actual"),
            "unit": (primary or {}).get("unit"),
            "percent": float((primary or {}).get("progress_percentage", 0.0)),
        },
        "goal": primary,
        "baseline": (primary or {}).get("baseline"),
        "current": (primary or {}).get("actual"),
        "metrics": metric_summary,
        "adherence_summary": {
            "overall": overall,
            "status": str(details.get("overall_behavioral_status") or behavioral_status(overall)),
            "heuristic": ">=80 TERCAPAI_KONSISTEN; 50–79 SEBAGIAN_TERCAPAI; <50 PERLU_DILANJUTKAN (PRODUCT_HEURISTIC).",
        },
        "trend": primary_trend,
        "trends": trends,
        "what_improved": improved,
        "what_remains": remains,
        "safety_summary": safety,
        "goal_status": goal_status,
        "decision": decision,
        "next_focus": next_focus,
        "options": options,
        "can_extend": bool(
            block_complete
            and not safety.get("active")
            and (goal_status in {"PARTIALLY_MET", "NOT_MET"} or elderly_behavioral_gap)
        ),
        "can_reframe": bool(block_complete and decision == "REFRAME" and not safety.get("active")),
        "rule_version": STAGE8_RULE_VERSION,
        "generated_at": utcnow().isoformat(),
        "evaluation_framework": "Behavioral block review; bukan diagnosis, status gizi, atau cutoff klinis.",
    }


def _persist_stage8_review(program: NutritionProgramModel, review: dict) -> dict:
    if not review.get("block_completed"):
        return review
    key = _stage8_review_key(program)
    cfg = dict(program.program_config or {})
    history = list(cfg.get("block_review_history") or [])
    existing = next((item for item in history if item.get("block_review_key") == key), None)
    if existing:
        return dict(existing.get("review") or review)
    history.append({
        "block_review_key": key,
        "block": int(program.cycle_number),
        "date": review.get("generated_at"),
        "goal": review.get("goal"),
        "metrics": review.get("metrics"),
        "adherence": review.get("adherence_summary"),
        "decision": review.get("decision"),
        "next_focus": review.get("next_focus"),
        "rule_version": STAGE8_RULE_VERSION,
        "review": review,
    })
    cfg["block_review_history"] = history
    cfg["last_block_review"] = review
    program.program_config = cfg
    return review



def _elderly_daily_context_summary(logs: list[dict]) -> dict:
    def counts(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for row in logs:
            value = str(row.get(key) or "").strip()
            if value:
                out[value] = out.get(value, 0) + 1
        return out

    latest = logs[-1] if logs else {}
    return {
        "logged_days": len(logs),
        "appetite": counts("appetite_status"),
        "hydration": counts("hydration_status"),
        "routine": counts("routine_adherence"),
        "difficulty": counts("eating_difficulty"),
        "eating_support": counts("eating_support"),
        "barriers": counts("eating_barrier"),
        "latest": {
            "appetite_status": latest.get("appetite_status"),
            "hydration_status": latest.get("hydration_status"),
            "routine_adherence": latest.get("routine_adherence"),
            "eating_difficulty": latest.get("eating_difficulty"),
            "eating_support": latest.get("eating_support"),
            "eating_barrier": latest.get("eating_barrier"),
            "health_condition": latest.get("health_condition"),
        },
    }

def evaluate_program(db: Session, program: NutritionProgramModel) -> dict:
    # Calendar end finalizes the program, not the goal. Goal status still depends
    # only on measured actual vs target.
    _finalize_if_due(db, program)
    persisted_final = _find_stage8_final_evaluation(db, program)
    if persisted_final is not None:
        return {
            "program_id": program.id,
            "completion_rate": persisted_final.completion_rate,
            "guidance_completion": persisted_final.guidance_completion,
            "meal_log_count": persisted_final.meal_log_count,
            "summary": persisted_final.summary,
            "details": dict(persisted_final.details or {}),
        }
    progress = progress_for(db, program)
    meal_count = db.scalar(select(func.count(NutritionMealLogModel.id)).where(NutritionMealLogModel.program_id == program.id)) or 0
    completion = round((progress["days_completed"] / progress["total_days"]) * 100, 1) if progress["total_days"] else 0.0
    guidance = round((progress["completed_tasks"] / progress["total_tasks"]) * 100, 1) if progress["total_tasks"] else 0.0
    goals = _sync_goals(db, program, persist=True)
    primary = _primary_goal(goals)
    goal_status = primary["status"] if primary else "NEEDS_REVIEW"
    summary = f"Program mencatat {progress['days_completed']} dari {progress['total_days']} hari selesai dan {progress['missed_days']} hari terlewat. Evaluasi mengukur adherence target perilaku yang tersimpan, bukan kondisi kesehatan atau diagnosis; hasil ini juga bukan penilaian status gizi."
    if program.cancelled_at:
        next_step = "Program dibatalkan. Progress yang sudah tercatat tetap tersedia di Nutrition History."
    elif program.completed_at:
        if goal_status == "MET":
            next_step = "Pertahankan kebiasaan yang sudah berjalan. Mulai assessment baru bila kebutuhan berubah."
        else:
            next_step = "Goal belum sepenuhnya tercapai. Extension dapat dipertimbangkan untuk menutup remaining gap dengan panduan yang disesuaikan."
    else:
        next_step = "Lanjutkan current day dan simpan checklist untuk memperbarui progress."
    behavior_metrics: dict[str, dict[str, float | int | str]] = {}
    daily_metric_history: list[dict] = []
    total_adherence = 0.0
    total_observations = 0
    elderly_daily_logs: list[dict] = []

    for row in _days(db, program.id):
        details_payload = row.action_details or {}
        if program.stage == "elderly" and isinstance(details_payload.get("daily_log"), dict) and details_payload.get("daily_log"):
            elderly_daily_logs.append(dict(details_payload.get("daily_log") or {}))
        tasks = details_payload.get("tasks") or []
        results = details_payload.get("task_results") or {}
        stored_adherence = details_payload.get("last_saved_task_adherence") or {}
        stored_metric_rows = {
            str(item.get("task_id")): item
            for item in (details_payload.get("metric_results") or [])
            if item.get("task_id")
        }
        availability = get_day_availability(program, row)
        explicitly_saved = bool(
            details_payload.get("last_saved_at")
            or results
            or any(row.checklist_state or [])
            or row.completed_at
        )
        is_missed = availability["status"] == "MISSED"

        # Future/unsaved rows are not treated as failures. A calendar-missed day
        # is recorded as zero adherence while remaining distinct from a saved
        # failed target.
        if not explicitly_saved and not is_missed:
            continue

        for index, task in enumerate(tasks):
            metric = str(task.get("metric_id") or task.get("metric") or "unknown")
            key = str(task.get("key") or task.get("id") or f"{metric}_{row.day_number}_{index}")
            checked = (row.checklist_state or [False] * len(tasks))[index] if index < len(row.checklist_state or []) else False
            stored = stored_metric_rows.get(key) or {}
            if is_missed and not explicitly_saved:
                measured: float | None = 0.0
                result_status = "MISSED"
                actual = None
                completed_at = None
            else:
                actual = stored.get("actual_result", stored.get("actual", results.get(key)))
                if stored:
                    raw_measured = stored.get("adherence")
                    measured = float(raw_measured) if raw_measured is not None else None
                    result_status = str(stored.get("status") or stored.get("result_status") or "COMPLETED")
                    completed_at = stored.get("completed_at")
                else:
                    # Historical rows created before Stage 6 keep the previous
                    # calculation semantics instead of being reinterpreted.
                    raw_measured = stored_adherence.get(key, adherence_for_task(task, actual, checked))
                    measured = float(raw_measured)
                    result_status = task_result_status(task, actual, checked)
                    completed_at = None

            # Stage 8 bug fix is intentionally metric-specific. Historical
            # responsive_feeding actual values are re-evaluated for the review
            # without mutating the stored daily result: Ya/true = 100,
            # Tidak/false = 0. Other metric formulas remain untouched.
            stored_measured = measured
            if metric == "responsive_feeding" and actual is not None:
                corrected = responsive_feeding_adherence(actual)
                if corrected is not None:
                    measured = corrected
                    result_status = "COMPLETED" if corrected >= 100 else "PARTIAL"

            bucket = behavior_metrics.setdefault(
                metric,
                {
                    "label": _metric_label(metric),
                    "assigned_days": 0,
                    "scored_days": 0,
                    "met_days": 0,
                    "partial_days": 0,
                    "missed_days": 0,
                    "adherence_total": 0.0,
                },
            )
            bucket["assigned_days"] += 1
            if measured is not None:
                bucket["scored_days"] += 1
                bucket["adherence_total"] += measured
                if measured >= 100:
                    bucket["met_days"] += 1
                elif measured > 0:
                    bucket["partial_days"] += 1
                total_adherence += measured
                total_observations += 1
            if is_missed and not explicitly_saved:
                bucket["missed_days"] += 1

            daily_metric_history.append({
                "program_id": program.id,
                "day_id": row.id,
                "day": row.day_number,
                "task_id": key,
                "metric": metric,
                "metric_id": metric,
                "metric_label": _metric_label(metric),
                "target": stored.get("target", stored.get("target_value", task.get("target_value"))),
                "unit": stored.get("unit", stored.get("target_unit", task.get("unit"))),
                "input_type": stored.get("input_type", task.get("input_type")),
                "actual": actual,
                "actual_result": actual,
                "adherence": measured,
                "stored_adherence": stored_measured if metric == "responsive_feeding" else measured,
                "evaluation_rule_fix": "responsive_feeding_yes_100_no_0" if metric == "responsive_feeding" and stored_measured != measured else None,
                "status": result_status,
                "completed_at": completed_at,
                "action_completed": checked,
                "evidence_rule_id": stored.get("evidence_rule_id", stored.get("rule_id", task.get("evidence_rule_id"))),
            })

    for metric, bucket in behavior_metrics.items():
        assigned = int(bucket["assigned_days"])
        scored = int(bucket.get("scored_days", 0))
        avg = round(float(bucket["adherence_total"]) / scored, 1) if scored else 0.0
        bucket["adherence_percentage"] = avg
        bucket["status"] = behavioral_status(avg)
        bucket.pop("adherence_total", None)

    overall_behavioral_adherence = round(total_adherence / total_observations, 1) if total_observations else 0.0
    overall_behavioral_status = behavioral_status(overall_behavioral_adherence) if total_observations else "PERLU_DILANJUTKAN"
    has_actual_daily_results = any(row.get("actual_result", row.get("actual")) is not None for row in daily_metric_history)

    ranked_metrics = sorted(
        behavior_metrics.items(),
        key=lambda item: float(item[1].get("adherence_percentage", 0.0)),
        reverse=True,
    )
    most_stable_metric = ranked_metrics[0][0] if ranked_metrics else None
    least_consistent_metric = ranked_metrics[-1][0] if ranked_metrics else None
    next_focus = _metric_label(least_consistent_metric) if least_consistent_metric else None

    if ranked_metrics:
        best = ranked_metrics[0][1]
        worst = ranked_metrics[-1][1]
        if int(best.get("met_days", 0)) > 0 or float(best.get("adherence_percentage", 0.0)) > 0:
            what_went_well = (
                f"{best['label']}: {best['met_days']} dari {best['assigned_days']} hari mencapai target; "
                f"adherence rata-rata {best['adherence_percentage']}%."
            )
        else:
            what_went_well = "Tidak ada perubahan yang cukup konsisten untuk diringkas."
        what_remains = (
            f"{worst['label']} masih paling tidak konsisten dengan adherence rata-rata "
            f"{worst['adherence_percentage']}%."
        )
    else:
        what_went_well = "Belum ada hasil metric tersimpan yang cukup untuk diringkas."
        what_remains = "Simpan hasil harian agar evaluasi metric dapat dibentuk."

    if program.completed_at and next_focus:
        next_step = (
            f"Program 14 hari selesai dengan status perilaku {overall_behavioral_status}. "
            f"Fokus berikutnya: {next_focus}. Status ini bukan diagnosis atau penilaian status gizi."
        )

    details = {
        **{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in progress.items() if k != "goals"},
        "goals": goals,
        "goal_status": goal_status,
        "what_went_well": what_went_well,
        "what_remains": what_remains,
        "recommended_next_step": next_step,
        "can_extend": bool(
            program.completed_at
            and not program.cancelled_at
            and primary
            and (
                primary["status"] in {"PARTIALLY_MET", "NOT_MET"}
                or (program.stage == "elderly" and has_actual_daily_results and overall_behavioral_adherence < 80)
            )
        ),
        "cumulative_goal": progress.get("cumulative_goal"),
        "behavior_metrics": behavior_metrics,
        "daily_metric_history": daily_metric_history,
        "overall_behavioral_adherence": overall_behavioral_adherence,
        "overall_behavioral_status": overall_behavioral_status,
        "most_stable_metric": most_stable_metric,
        "least_consistent_metric": least_consistent_metric,
        "next_focus": next_focus,
        "evaluation_framework": "Mengukur keterlaksanaan target perilaku yang disimpan pengguna; bukan penilaian status gizi atau diagnosis.",
        "behavioral_status_heuristic": ">=80 TERCAPAI_KONSISTEN; 50–79 SEBAGIAN_TERCAPAI; <50 PERLU_DILANJUTKAN. Ini heuristik produk SEHATIN, bukan cut-off WHO/Kemenkes.",
        "adaptation_rule_version": ADAPTIVE_RULE_VERSION,
        "decision_history": list((program.program_config or {}).get("decision_history") or []),
        "elderly_daily_context": _elderly_daily_context_summary(elderly_daily_logs) if program.stage == "elderly" else {},
        "stage8_rule_version": STAGE8_RULE_VERSION,
        "block_completed": _stage8_block_complete(program),
        "block_review_key": _stage8_review_key(program) if _stage8_block_complete(program) else None,
    }
    review = _build_stage8_review(program, details, progress)
    review = _persist_stage8_review(program, review)
    details["block_review"] = review
    details["program_progress"] = review.get("program_progress")
    details["goal_progress"] = review.get("goal_progress")
    details["metric_summary"] = review.get("metrics")
    details["trends"] = review.get("trends")
    details["safety_summary"] = review.get("safety_summary")
    details["next_focus"] = review.get("next_focus")
    details["recommended_next_step"] = review.get("next_focus") if review.get("block_completed") else next_step

    if review.get("block_completed"):
        # Final Day-14 evaluation is immutable/versioned. Refreshing the page
        # returns this same record instead of updating it or creating duplicates.
        latest = NutritionEvaluationModel(
            program_id=program.id,
            completion_rate=completion,
            guidance_completion=guidance,
            meal_log_count=meal_count,
            summary=summary,
            details=details,
        )
        db.add(latest)
    else:
        latest = db.scalar(select(NutritionEvaluationModel).where(NutritionEvaluationModel.program_id == program.id).order_by(NutritionEvaluationModel.created_at.desc()))
        if latest and not (latest.details or {}).get("block_completed"):
            latest.completion_rate, latest.guidance_completion, latest.meal_log_count, latest.summary, latest.details = completion, guidance, meal_count, summary, details
        else:
            latest = NutritionEvaluationModel(program_id=program.id, completion_rate=completion, guidance_completion=guidance, meal_log_count=meal_count, summary=summary, details=details)
            db.add(latest)
    db.commit()
    return {"program_id": program.id, "completion_rate": completion, "guidance_completion": guidance, "meal_log_count": meal_count, "summary": summary, "details": details}



def _final_daily_progress_series(db: Session, program: NutritionProgramModel, details: dict, history: list[dict]) -> tuple[list[dict], dict]:
    """Build a day-by-day behavioural series for Final Result visualisation.

    Values represent adherence to saved daily behavioural targets. They are not
    clinical outcomes and must not be presented as a health-status score.
    """
    rows = list(details.get("daily_metric_history") or [])
    scores_by_day: dict[int, list[float]] = {}
    met_by_day: dict[int, int] = {}
    task_count_by_day: dict[int, int] = {}
    for row in rows:
        try:
            day_number = int(row.get("day"))
        except (TypeError, ValueError):
            continue
        adherence = row.get("adherence")
        if adherence is None:
            continue
        try:
            value = max(0.0, min(100.0, float(adherence)))
        except (TypeError, ValueError):
            continue
        scores_by_day.setdefault(day_number, []).append(value)
        task_count_by_day[day_number] = task_count_by_day.get(day_number, 0) + 1
        if value >= 100:
            met_by_day[day_number] = met_by_day.get(day_number, 0) + 1

    decisions: dict[int, str] = {}
    for row in history:
        try:
            day_number = int(row.get("day"))
        except (TypeError, ValueError):
            continue
        decision = dict(row.get("decision") or {})
        decisions[day_number] = str(decision.get("decision") or "CONTINUE")

    day_models = {row.day_number: row for row in _days(db, program.id)}
    series: list[dict] = []
    for day_number in range(1, int(program.duration_days) + 1):
        scores = scores_by_day.get(day_number, [])
        average = round(sum(scores) / len(scores), 1) if scores else None
        model = day_models.get(day_number)
        if model and model.completed:
            status = "COMPLETED"
        elif program.completed_at:
            status = "MISSED"
        else:
            status = "NO_DATA"
        series.append({
            "day": day_number,
            "adherence_percent": average,
            "task_count": task_count_by_day.get(day_number, 0),
            "met_tasks": met_by_day.get(day_number, 0),
            "status": status,
            "decision": decisions.get(day_number),
        })

    scored_values = [float(item["adherence_percent"]) for item in series if item.get("adherence_percent") is not None]
    first_values = scored_values[: min(3, len(scored_values))]
    last_values = scored_values[-min(3, len(scored_values)) :] if scored_values else []
    early_average = round(sum(first_values) / len(first_values), 1) if first_values else None
    recent_average = round(sum(last_values) / len(last_values), 1) if last_values else None
    delta = round(recent_average - early_average, 1) if early_average is not None and recent_average is not None else None
    if delta is None:
        direction = "INSUFFICIENT_DATA"
    elif delta >= 10:
        direction = "IMPROVING"
    elif delta <= -10:
        direction = "DECLINING"
    else:
        direction = "STABLE"
    change = {
        "early_average": early_average,
        "recent_average": recent_average,
        "delta_points": delta,
        "direction": direction,
        "scored_days": len(scored_values),
        "strong_days": sum(1 for value in scored_values if value >= 80),
    }
    return series, change



def final_program_result(db: Session, program: NutritionProgramModel) -> dict:
    """Aggregate the completed block into one auditable, non-diagnostic result.

    Every statement is derived from persisted program data: goal state, daily metric
    history, stored adaptive decisions, meal logs, missed days, and safety events.
    """
    evaluation = evaluate_program(db, program)
    normalized = _normalized_status(program)
    if not program.completed_at and normalized not in {"COMPLETED", "EXTENDED"}:
        raise _program_error(409, "PROGRAM_BLOCK_NOT_COMPLETE", "Final Program Result tersedia setelah block program selesai.")

    progress = progress_for(db, program)
    goals = evaluation.get("details", {}).get("goals", [])
    primary = _primary_goal(goals)
    review = block_review(db, program)
    details = evaluation.get("details", {})
    history = list(details.get("decision_history") or [])
    behavior_metrics = details.get("behavior_metrics") or {}

    meal_logs = list(db.scalars(select(NutritionMealLogModel).where(NutritionMealLogModel.program_id == program.id)))
    logged_day_ids = {row.program_day_id for row in meal_logs if row.program_day_id}
    program_numbers = {
        "duration_days": int(program.duration_days),
        "completed_days": int(progress.get("days_completed", 0)),
        "missed_days": int(progress.get("missed_days", 0)),
        "logged_days": len(logged_day_ids),
        "adaptation_decisions": len(history),
    }

    accomplished: list[str] = []
    worked_well: list[str] = []
    challenges: list[str] = []
    ranked = sorted(
        behavior_metrics.values(),
        key=lambda item: float(item.get("adherence_percentage", 0.0)),
        reverse=True,
    )
    for item in ranked[:3]:
        met = int(item.get("met_days", 0))
        assigned = int(item.get("assigned_days", 0))
        if met > 0 and assigned > 0:
            accomplished.append(f"{item.get('label', 'Target perilaku')}: target tercapai pada {met} dari {assigned} hari yang diukur.")
    if ranked:
        best = ranked[0]
        worked_well.append(
            f"{best.get('label', 'Target utama')} paling konsisten dengan adherence rata-rata {float(best.get('adherence_percentage', 0.0)):.0f}%."
        )
        worst = ranked[-1]
        if float(worst.get("adherence_percentage", 0.0)) < 100:
            challenges.append(
                f"{worst.get('label', 'Target berikutnya')} masih perlu waktu; adherence rata-rata {float(worst.get('adherence_percentage', 0.0)):.0f}%."
            )
    if int(progress.get("missed_days", 0)) > 0:
        challenges.append(f"Ada {int(progress['missed_days'])} hari yang terlewat dan tidak dihitung sebagai hari selesai.")
    if not accomplished:
        accomplished.append("Program menyimpan riwayat harian yang dapat ditinjau kembali; belum ada metric dengan pencapaian konsisten yang cukup untuk diringkas.")
    if not worked_well:
        worked_well.append(str(details.get("what_went_well") or "Data program tersimpan dan dapat ditinjau."))
    if not challenges:
        challenges.append(str(details.get("what_remains") or "Tidak ada tantangan spesifik yang cukup sering tercatat untuk diringkas."))

    adaptation_history: list[dict] = []
    decision_counts: dict[str, int] = {}
    safety_notes: list[str] = []
    acceptance_series: list[dict] = []
    for row in history:
        decision = dict(row.get("decision") or {})
        label = str(decision.get("decision") or "CONTINUE")
        decision_counts[label] = decision_counts.get(label, 0) + 1
        indicators = dict(row.get("indicators") or {})
        trend_value = indicators.get("acceptance_trend")
        if trend_value is not None:
            acceptance_series.append({"day": row.get("day"), "value": trend_value, "direction": indicators.get("trend_direction")})
        safety = dict(row.get("safety") or {})
        before = dict(safety.get("before_adaptation") or {})
        after = dict(safety.get("after_plan_generation") or {})
        for safety_row in (before, after):
            if safety_row.get("blocked"):
                note = str(safety_row.get("user_facing_reason") or safety_row.get("reason") or "Safety guard membatasi adaptasi otomatis.")
                if note not in safety_notes:
                    safety_notes.append(note)
        adaptation_history.append({
            "day": row.get("day"),
            "decision": label,
            "reason": decision.get("reason"),
            "user_facing_reason": decision.get("user_facing_reason"),
            "rule_version_id": decision.get("rule_version_id"),
            "trend_direction": indicators.get("trend_direction"),
            "acceptance_trend": trend_value,
            "next_plan": row.get("next_plan"),
        })

    if decision_counts:
        ordered = sorted(decision_counts.items(), key=lambda item: (-item[1], item[0]))
        decision_text = ", ".join(f"{name} {count}×" for name, count in ordered)
        what_changed = f"Selama cycle ini, sistem mencatat keputusan adaptasi: {decision_text}. Setiap perubahan mengikuti daily log, indikator, rule version, dan safety guard yang tersimpan."
    else:
        what_changed = "Tidak ada keputusan adaptasi tersimpan pada cycle ini."

    daily_progress, daily_progress_change = _final_daily_progress_series(db, program, details, history)
    goal_pct = float(primary.get("progress_percentage", 0.0)) if primary else 0.0
    next_decision = str(review.get("decision") or "REVIEW")
    next_step = {
        "decision": next_decision,
        "can_extend": bool(review.get("can_extend")),
        "can_reframe": bool(review.get("can_reframe")),
        "options": list(review.get("options") or []),
        "message": str(details.get("recommended_next_step") or review.get("what_remains") or "Tinjau goal berikutnya."),
    }
    if program.stage == "elderly":
        elderly_focus = _elderly_extension_focus(details, str((primary or {}).get("goal_key") or ""))
        next_step["suggested_focus"] = elderly_focus["focus"]
        next_step["suggested_goal_key"] = elderly_focus["goal_key"]
        next_step["focus_reason"] = elderly_focus["reason"]

    return {
        "program": serialize_summary(db, program),
        "cycle": int(program.cycle_number),
        "duration_days": int(program.duration_days),
        "goal": primary,
        "baseline": primary.get("baseline") if primary else None,
        "target": primary.get("target") if primary else None,
        "actual": primary.get("actual") if primary else None,
        "goal_status": str(primary.get("status") if primary else "NEEDS_REVIEW"),
        "goal_achievement_percent": goal_pct,
        "program_completion_percent": float(progress.get("progress_percent", 0.0)),
        "program_numbers": program_numbers,
        "what_accomplished": accomplished,
        "what_changed": what_changed,
        "what_worked_well": worked_well,
        "challenges": challenges,
        "adaptation_history": adaptation_history,
        "trends": {
            "acceptance": acceptance_series,
            "goal_progress_percent": goal_pct,
            "behavioral_adherence_percent": float(details.get("overall_behavioral_adherence") or 0.0),
            "goal_metric": primary.get("goal_key") if primary else None,
            "daily_progress": daily_progress,
            "daily_progress_change": daily_progress_change,
            "elderly_daily_context": dict(details.get("elderly_daily_context") or {}) if program.stage == "elderly" else {},
        },
        "safety_notes": safety_notes,
        "next_step": next_step,
        "extension_history": _extension_chain(db, program),
        "generated_at": utcnow(),
    }


def _elderly_extension_focus(details: dict, current_goal_key: str | None) -> dict:
    """Choose the next behavioural focus from observed daily patterns.

    This is a product heuristic for program continuation, not a clinical
    diagnosis or medical nutrition prescription.
    """
    daily = dict(details.get("elderly_daily_context") or {})
    hydration = dict(daily.get("hydration") or {})
    appetite = dict(daily.get("appetite") or {})
    difficulty = dict(daily.get("difficulty") or {})
    support = dict(daily.get("eating_support") or {})
    barriers = dict(daily.get("barriers") or {})

    hydration_gap = int(hydration.get("reduced", 0) or 0) + int(hydration.get("poor", 0) or 0)
    appetite_gap = int(appetite.get("reduced", 0) or 0) + int(appetite.get("poor", 0) or 0)
    difficulty_gap = int(difficulty.get("some", 0) or 0) + int(difficulty.get("difficult", 0) or 0)
    support_gap = int(support.get("reminder", 0) or 0) + int(support.get("assisted", 0) or 0)
    swallowing_barrier = int(barriers.get("swallowing", 0) or 0)
    chewing_barrier = int(barriers.get("chewing", 0) or 0)

    candidates = [
        (swallowing_barrier + difficulty_gap, "elderly_safe_nutrition_routine", "Menjaga kecukupan makan/minum dengan pola yang sudah aman"),
        (hydration_gap, "elderly_hydration_routine", "Membuat kesempatan minum lebih teratur"),
        (support_gap, "elderly_supported_meal_routine", "Membuat makan/minum lebih mudah dengan dukungan yang sesuai"),
        (appetite_gap + chewing_barrier, "elderly_meal_routine", "Menjaga kesempatan makan agar tidak mudah terlewat"),
    ]
    candidates.sort(key=lambda row: row[0], reverse=True)
    score, goal_key, focus = candidates[0]
    if score <= 0:
        goal_key = "elderly_balanced_meal_routine"
        focus = "Mempertahankan pola makan seimbang dan menambah variasi secara bertahap"

    if goal_key == current_goal_key and score <= 1:
        goal_key = "elderly_balanced_meal_routine"
        focus = "Mempertahankan pola yang sudah stabil sambil menambah variasi kecil"

    return {
        "goal_key": goal_key,
        "focus": focus,
        "reason": (
            "Fokus berikutnya dipilih dari pola cairan, nafsu makan, kenyamanan, hambatan, dan dukungan yang tercatat selama cycle. "
            "Ini adalah heuristik produk untuk kelanjutan program, bukan penilaian klinis."
        ),
    }

def extension_recommendation(db: Session, program: NutritionProgramModel) -> dict:
    evaluation = evaluate_program(db, program)
    details = evaluation.get("details") or {}
    goals = details.get("goals", [])
    primary = goals[0] if goals else None
    if not program.completed_at:
        raise _program_error(409, "PROGRAM_NOT_COMPLETE", "Extension hanya tersedia setelah program selesai.")

    elderly_daily_history = list(details.get("daily_metric_history") or [])
    elderly_has_actual_results = any(
        row.get("actual_result", row.get("actual")) is not None
        for row in elderly_daily_history
    )
    if program.stage == "elderly" and elderly_has_actual_results:
        overall = float(details.get("overall_behavioral_adherence") or 0.0)
        if overall >= 80:
            raise _program_error(409, "EXTENSION_NOT_NEEDED", "Pola harian sudah cukup konsisten untuk cycle ini; extension tidak direkomendasikan.")
        remaining_gap = round(max(0.0, 80.0 - overall), 1)
        recommended_days = 7 if overall >= 60 else 14
        next_focus = _elderly_extension_focus(details, str((primary or {}).get("goal_key") or ""))
        return {
            "program_id": program.id,
            "goal_status": str((primary or {}).get("status") or "NEEDS_REVIEW"),
            "previous_actual": overall,
            "previous_target": 80.0,
            "remaining_gap": remaining_gap,
            "unit": "behavioral adherence percentage points",
            "recommended_days": recommended_days,
            "cumulative_actual": overall,
            "cumulative_target": 80.0,
            "cumulative_progress": min(100.0, round((overall / 80.0) * 100, 1)) if overall else 0.0,
            "why": "Extension Lansia mempertimbangkan keterlaksanaan target harian dan pola hambatan selama cycle, bukan hanya jumlah hari yang selesai. Ambang 80% adalah heuristik produk SEHATIN, bukan cut-off klinis.",
            "guidance_adjustments": {
                "focus": next_focus["focus"],
                "recommended_goal_key": next_focus["goal_key"],
                "reason": next_focus["reason"],
                "meal_guidance": "Pertahankan konteks assessment, gunakan menu berbasis kelompok pangan yang familiar, dan sesuaikan beban langkah dengan pola harian terakhir.",
            },
        }

    if not primary or primary["status"] not in {"PARTIALLY_MET", "NOT_MET"}:
        raise _program_error(409, "EXTENSION_NOT_NEEDED", "Goal utama sudah tercapai atau memerlukan review lain; extension tidak direkomendasikan.")
    cumulative = cumulative_goal_for(db, program)
    remaining_gap = float(cumulative["remaining_gap"] if cumulative else primary["remaining_gap"])
    remaining = max(1, math.ceil(remaining_gap))
    recommended_days = 7
    return {
        "program_id": program.id,
        "goal_status": primary["status"],
        "previous_actual": primary["actual"],
        "previous_target": primary["target"],
        "remaining_gap": remaining_gap,
        "unit": primary["unit"],
        "recommended_days": recommended_days,
        "cumulative_actual": cumulative["actual"] if cumulative else primary["actual"],
        "cumulative_target": cumulative["target"] if cumulative else primary["target"],
        "cumulative_progress": cumulative["progress_percentage"] if cumulative else primary["progress_percentage"],
        "why": "Durasi extension didasarkan pada remaining gap behavioral goal dan memberi ruang beberapa hari untuk membangun konsistensi. Ini bukan target medis.",
        "guidance_adjustments": {"focus": "Ulangi area yang belum konsisten", "meal_guidance": "Pertahankan contoh menu yang kompatibel dengan assessment dan batasan pangan tersimpan."},
    }


def create_extension(db: Session, user: UserModel, program: NutritionProgramModel, *, confirm: bool, preference: str = "same_goal", difficulty: str | None = None, goal_key: str | None = None) -> NutritionProgramModel:
    if not confirm:
        raise HTTPException(status_code=400, detail="Konfirmasi diperlukan sebelum membuat extension.")
    info = extension_recommendation(db, program)
    existing = db.scalar(select(NutritionProgramExtensionModel).where(NutritionProgramExtensionModel.original_program_id == program.id))
    if existing:
        existing_program = db.get(NutritionProgramModel, existing.extension_program_id)
        if existing_program:
            return existing_program
    root_id = program.parent_program_id or program.id
    siblings = list(db.scalars(select(NutritionProgramModel).where((NutritionProgramModel.id == root_id) | (NutritionProgramModel.parent_program_id == root_id))))
    if len(siblings) >= 3:
        raise _program_error(409, "EXTENSION_LIMIT", "Maksimal tiga cycle disediakan agar program tidak berulang tanpa review baru.")

    now = utcnow()
    duration = int(info["recommended_days"])
    new_program = NutritionProgramModel(
        user_id=user.id,
        profile_id=program.profile_id,
        recommendation_id=program.recommendation_id,
        parent_program_id=root_id,
        stage=program.stage,
        title=f"{program.title} · Extension {max(p.cycle_number for p in siblings) + 1}",
        status="ACTIVE",
        duration_days=duration,
        cycle_number=max(p.cycle_number for p in siblings) + 1,
        assessment_snapshot=program.assessment_snapshot,
        recommendation_snapshot=program.recommendation_snapshot,
        program_config={**(program.program_config or {}), "extension_of": program.id, "remaining_gap_at_start": info["remaining_gap"], "post_block_choice": {"preference": preference, "difficulty": difficulty, "goal_key": goal_key}, "adaptive_rule_version": ADAPTIVE_RULE_VERSION},
        started_at=now,
        ends_at=now + (_day_interval() * (duration - 1)),
        last_activity_at=now,
    )
    db.add(new_program)
    db.flush()
    profile = db.get(NutritionProfileModel, program.profile_id)
    current_goal_key = _goals(db, program.id)[0].goal_key if _goals(db, program.id) else None
    behavioral_elderly_extension = bool(
        program.stage == "elderly"
        and str(info.get("unit") or "") == "behavioral adherence percentage points"
    )
    recommended_goal_key = str((info.get("guidance_adjustments") or {}).get("recommended_goal_key") or "") or None
    selected_goal = (
        goal_key if preference == "different_goal" and goal_key
        else recommended_goal_key if behavioral_elderly_extension and preference != "smaller_goal"
        else current_goal_key
    )
    if selected_goal:
        cfg = dict(new_program.program_config or {})
        cfg["selected_goal_key"] = selected_goal
        cfg["extension_focus"] = str((info.get("guidance_adjustments") or {}).get("focus") or "")
        new_program.program_config = cfg
    new_goals = _create_goals(
        db, new_program, duration_days=duration,
        remaining_day_gap=(None if behavioral_elderly_extension else math.ceil(float(info["remaining_gap"]))),
        profile_payload=profile.profile_payload or {}, selected_goal_key=selected_goal
    )
    if preference == "smaller_goal" and new_goals:
        new_goals[0].target = float(max(1, min(duration, math.ceil(float(info["remaining_gap"]) / 2))))
        new_goals[0].description += " Target extension diperkecil atas pilihan caregiver."
    profile = db.get(NutritionProfileModel, program.profile_id)
    recommendation = program.recommendation_snapshot or db.get(NutritionRecommendationModel, program.recommendation_id).result_payload
    db.add_all(_generate_days(new_program, count=duration, references=recommendation.get("references", []), recommendation=recommendation, profile_payload=profile.profile_payload or {}, extension=True))
    db.add(NutritionProgramExtensionModel(original_program_id=program.id, extension_program_id=new_program.id, previous_actual=float(info["previous_actual"]), previous_target=float(info["previous_target"]), remaining_gap=float(info["remaining_gap"]), recommended_days=duration, rationale=info["why"], guidance_adjustments=info["guidance_adjustments"]))
    program.status = "EXTENDED"
    db.commit()
    db.refresh(new_program)
    return new_program
