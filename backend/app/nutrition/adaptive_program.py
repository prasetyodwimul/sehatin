"""Deterministic adaptive loop for MPASI/Toddler guided nutrition.

Stage 7 reads saved Stage 6 daily results plus caregiver logs. Core decisions are
rule-based and auditable; no LLM/randomness is used for safety, adherence,
progression, or goal changes.

Thresholds below are product rules and remain marked NEEDS_CLINICAL_VALIDATION.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.nutrition.safety_red_flags import detect_red_flags, emergency_message

RULE_VERSION = {
    "id": "nutrition_adaptive_rules_v2",
    "version": "2.0.0",
    "active": True,
    "effective_date": "2026-09-25",
    "review_status": "NEEDS_CLINICAL_VALIDATION",
    "reviewer": None,
    "thresholds": {
        "trend_window_days": 3,
        "history_window_days": 7,
        "ease_refusal_count": 2,
        "ease_adherence_average_max": 0.50,
        "advance_acceptance_average": 0.80,
        "advance_adherence_average_min": 0.75,
        "advance_burden_max": 0.35,
        "minimum_trend_points": 2,
        "block_days": 14,
    },
    "notes": (
        "Product decision thresholds are deterministic product heuristics and "
        "require pediatric/nutrition review before production use."
    ),
}

PORTION_SCORE = {"finished": 1.0, "partial": 0.67, "little": 0.33, "none": 0.0}
ACCEPTANCE_SCORE = {"liked": 1.0, "neutral": 0.5, "refused": 0.0}
BURDEN_SCORE = {"easy": 0.0, "somewhat_difficult": 0.5, "difficult": 1.0}
SICK_CONDITIONS = {"sick", "fever", "diarrhea", "severe_teething"}
ELDERLY_PAUSE_CONDITIONS = {"unwell", "nausea", "vomiting", "fever", "diarrhea", "dizziness", "pain_discomfort", "difficulty_eating_drinking", "other_concern"}
ELDERLY_APPETITE_SCORE = {"good": 1.0, "reduced": 0.5, "poor": 0.0}
ELDERLY_DIFFICULTY_SCORE = {"none": 0.0, "some": 0.5, "difficult": 1.0}
ELDERLY_ROUTINE_SCORE = {"yes": 1.0, "partial": 0.5, "no": 0.0}
ELDERLY_HYDRATION_SCORE = {"good": 1.0, "reduced": 0.5, "poor": 0.0}
ELDERLY_SUPPORT_NEED_SCORE = {"independent": 0.0, "reminder": 0.5, "assisted": 1.0}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _rule_snapshot(rule_version: dict[str, Any] | None) -> dict[str, Any]:
    rule = deepcopy(rule_version or RULE_VERSION)
    return {
        "id": str(rule.get("id") or RULE_VERSION["id"]),
        "version": str(rule.get("version") or "unknown"),
        "effective_date": rule.get("effective_date"),
        "review_status": rule.get("review_status"),
    }


def _trend(values: list[float], *, delta_threshold: float = 0.15) -> tuple[float | None, str]:
    if not values:
        return None, "INSUFFICIENT_DATA"
    average = round(sum(values) / len(values), 3)
    if len(values) < 2:
        return average, "INSUFFICIENT_DATA"
    delta = values[-1] - values[0]
    direction = "IMPROVING" if delta > delta_threshold else "DECLINING" if delta < -delta_threshold else "STABLE"
    return average, direction


def safety_guard(
    log: dict[str, Any],
    profile: dict[str, Any],
    *,
    generated_plan: dict[str, Any] | None = None,
    stage: str | None = None,
) -> dict[str, Any]:
    """Return the existing deterministic safety state for one daily log.

    MPASI/Toddler keep the established pediatric red-flag detector. Elderly
    reuses the same ACTIVE/PAUSED state machine but does not reuse pediatric
    danger-sign evidence; its daily health selector only pauses the program.
    """
    category = str(stage or profile.get("stage") or "").lower()
    child_condition = str(log.get("child_condition") or "").lower()
    health_condition = str(log.get("health_condition") or "").lower()
    condition = health_condition if category == "elderly" else (child_condition or health_condition)
    reaction = str(log.get("reaction") or "").lower()
    reaction_notes = str(log.get("reaction_notes") or "")
    notes = str(log.get("notes") or "")
    red_flags = detect_red_flags(reaction_notes, notes) if category in {"mpasi", "toddler", ""} else []
    severe = bool(red_flags)
    paused_conditions = ELDERLY_PAUSE_CONDITIONS if category == "elderly" else SICK_CONDITIONS
    paused = condition in paused_conditions
    unsafe_plan = bool(generated_plan and generated_plan.get("strategy") == "ADVANCE" and (severe or paused))
    if severe or unsafe_plan:
        return {
            "level": "SEVERE",
            "blocked": True,
            "decision": "REFER",
            "emergency": True,
            "red_flags": red_flags,
            "reason": "Terdeteksi red flag eksplisit dari detail reaksi/catatan caregiver.",
            "user_facing_reason": "Tanda bahaya terdeteksi dari informasi yang Anda masukkan. Adaptasi otomatis dihentikan.",
            "recommended_action": emergency_message(red_flags),
        }
    if paused:
        return {
            "level": "PAUSE",
            "blocked": True,
            "decision": "PAUSE",
            "emergency": False,
            "red_flags": [],
            "reason": f"Kondisi saat log: {condition}.",
            "user_facing_reason": "Program dijeda sementara agar fokus tetap pada pemulihan, bukan mengejar target program.",
            "recommended_action": "Progress yang sudah dilakukan tetap tersimpan. Lanjutkan program setelah kondisi membaik dan proses resume selesai.",
        }
    if reaction == "detected":
        return {
            "level": "OBSERVE",
            "blocked": False,
            "decision": None,
            "emergency": False,
            "red_flags": [],
            "reason": "Reaksi dilaporkan, tetapi tidak ada red flag eksplisit pada teks yang tersimpan.",
            "user_facing_reason": "Reaksi hari ini dicatat sebagai observasi dan tidak otomatis menghentikan program.",
        }
    return {
        "level": "CLEAR",
        "blocked": False,
        "decision": None,
        "emergency": False,
        "red_flags": [],
        "reason": "Tidak ada red flag dari daily log.",
        "user_facing_reason": "Tidak ada tanda keamanan yang menghentikan adaptasi otomatis.",
    }


def calculate_indicators(
    current_log: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    *,
    goal_metric: str | None,
    task_adherence: dict[str, float] | None = None,
    recent_adherence_history: list[float] | None = None,
    rule_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate deterministic Stage 7 indicators without inventing missing data."""
    rule = rule_version or RULE_VERSION
    thresholds = rule.get("thresholds") or RULE_VERSION["thresholds"]
    acceptance = ACCEPTANCE_SCORE.get(str(current_log.get("acceptance") or ""), None)
    portion = PORTION_SCORE.get(str(current_log.get("portion") or ""), None)
    burden = BURDEN_SCORE.get(str(current_log.get("parent_difficulty") or ""), None)

    task_values = [float(v) / 100 for v in (task_adherence or {}).values() if isinstance(v, (int, float))]
    current_adherence = (sum(task_values) / len(task_values)) if task_values else None

    history_window = int(thresholds.get("history_window_days", 7))
    trend_window = int(thresholds.get("trend_window_days", 3))
    logs = list(recent_logs or [])[-history_window:]

    acceptance_values = [ACCEPTANCE_SCORE.get(str(row.get("acceptance") or "")) for row in logs]
    acceptance_values = [float(v) for v in acceptance_values if v is not None]
    if acceptance is not None:
        acceptance_values.append(float(acceptance))
    acceptance_window = acceptance_values[-trend_window:]
    acceptance_average, acceptance_direction = _trend(acceptance_window)

    portion_values = [PORTION_SCORE.get(str(row.get("portion") or "")) for row in logs]
    portion_values = [float(v) for v in portion_values if v is not None]
    if portion is not None:
        portion_values.append(float(portion))
    portion_window = portion_values[-trend_window:]
    portion_average, portion_direction = _trend(portion_window)

    burden_values = [BURDEN_SCORE.get(str(row.get("parent_difficulty") or "")) for row in logs]
    burden_values = [float(v) for v in burden_values if v is not None]
    if burden is not None:
        burden_values.append(float(burden))
    burden_window = burden_values[-trend_window:]
    burden_average = round(sum(burden_window) / len(burden_window), 3) if burden_window else None

    adherence_values = [
        _bounded(float(v) / 100 if float(v) > 1 else float(v))
        for v in (recent_adherence_history or [])
        if isinstance(v, (int, float))
    ]
    if current_adherence is not None:
        adherence_values.append(_bounded(current_adherence))
    adherence_values = adherence_values[-history_window:]
    adherence_average, adherence_direction = _trend(adherence_values[-trend_window:])

    safety_index = 1.0 if (
        detect_red_flags(str(current_log.get("reaction_notes") or ""), str(current_log.get("notes") or ""))
        or str(current_log.get("child_condition") or "") in SICK_CONDITIONS
    ) else 0.0

    return {
        # Backward-compatible fields used by current UI/reports.
        "acceptance_score": None if acceptance is None else round(acceptance * 5, 2),
        "portion_score": None if portion is None else round(portion * 100, 1),
        "trend_window_days": trend_window,
        "acceptance_trend": acceptance_average,
        "trend_direction": acceptance_direction,
        "goal_progress_score": None if current_adherence is None else round(current_adherence * 100, 1),
        "goal_metric": goal_metric,
        "burden_index": None if burden is None else round(_bounded(burden), 2),
        "safety_index": safety_index,
        "technical_labels": {"acceptance_score": "SPH", "portion_score": "SPoH", "goal_progress_score": "SKG"},
        # Stage 7 explicit indicator contract.
        "history_days_available": len(logs),
        "history_window_days": history_window,
        "current_adherence": None if current_adherence is None else round(current_adherence * 100, 2),
        "recent_adherence_average": None if adherence_average is None else round(adherence_average * 100, 2),
        "adherence_trend_direction": adherence_direction,
        "goal_metric_trend": adherence_direction,
        "portion_trend": None if portion_average is None else round(portion_average * 100, 2),
        "portion_trend_direction": portion_direction,
        "burden_average": burden_average,
        "data_sufficiency": "SUFFICIENT" if len(logs) >= 2 else "LIMITED" if len(logs) == 1 else "CURRENT_DAY_ONLY",
    }



def calculate_elderly_indicators(
    current_log: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    *,
    goal_metric: str | None,
    task_adherence: dict[str, float] | None = None,
    recent_adherence_history: list[float] | None = None,
    rule_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Daily indicators for elderly programs using only user-entered daily data.

    These are product heuristics, not medical scoring. They drive plan complexity
    and continuity only; safety state still has precedence.
    """
    rule = rule_version or RULE_VERSION
    thresholds = rule.get("thresholds") or RULE_VERSION["thresholds"]
    history_window = int(thresholds.get("history_window_days", 7))
    trend_window = int(thresholds.get("trend_window_days", 3))
    logs = list(recent_logs or [])[-history_window:]

    task_values = [float(v) / 100 for v in (task_adherence or {}).values() if isinstance(v, (int, float))]
    current_adherence = (sum(task_values) / len(task_values)) if task_values else None
    adherence_values = [
        _bounded(float(v) / 100 if float(v) > 1 else float(v))
        for v in (recent_adherence_history or []) if isinstance(v, (int, float))
    ]
    if current_adherence is not None:
        adherence_values.append(_bounded(current_adherence))
    adherence_average, adherence_direction = _trend(adherence_values[-trend_window:])

    appetite_values = [ELDERLY_APPETITE_SCORE.get(str(row.get("appetite_status") or "")) for row in logs]
    appetite_values = [float(v) for v in appetite_values if v is not None]
    current_appetite = ELDERLY_APPETITE_SCORE.get(str(current_log.get("appetite_status") or ""))
    if current_appetite is not None:
        appetite_values.append(float(current_appetite))
    appetite_average, appetite_direction = _trend(appetite_values[-trend_window:])

    routine_values = [ELDERLY_ROUTINE_SCORE.get(str(row.get("routine_adherence") or "")) for row in logs]
    routine_values = [float(v) for v in routine_values if v is not None]
    current_routine = ELDERLY_ROUTINE_SCORE.get(str(current_log.get("routine_adherence") or ""))
    if current_routine is not None:
        routine_values.append(float(current_routine))
    routine_average, routine_direction = _trend(routine_values[-trend_window:])

    difficulty_values = [ELDERLY_DIFFICULTY_SCORE.get(str(row.get("eating_difficulty") or "")) for row in logs]
    difficulty_values = [float(v) for v in difficulty_values if v is not None]
    current_difficulty = ELDERLY_DIFFICULTY_SCORE.get(str(current_log.get("eating_difficulty") or ""))
    if current_difficulty is not None:
        difficulty_values.append(float(current_difficulty))
    difficulty_window = difficulty_values[-trend_window:]
    difficulty_average = round(sum(difficulty_window) / len(difficulty_window), 3) if difficulty_window else None

    hydration_values = [ELDERLY_HYDRATION_SCORE.get(str(row.get("hydration_status") or "")) for row in logs]
    hydration_values = [float(v) for v in hydration_values if v is not None]
    current_hydration = ELDERLY_HYDRATION_SCORE.get(str(current_log.get("hydration_status") or ""))
    if current_hydration is not None:
        hydration_values.append(float(current_hydration))
    hydration_average, hydration_direction = _trend(hydration_values[-trend_window:])

    support_values = [ELDERLY_SUPPORT_NEED_SCORE.get(str(row.get("eating_support") or "")) for row in logs]
    support_values = [float(v) for v in support_values if v is not None]
    current_support = ELDERLY_SUPPORT_NEED_SCORE.get(str(current_log.get("eating_support") or ""))
    if current_support is not None:
        support_values.append(float(current_support))
    support_window = support_values[-trend_window:]
    support_need_average = round(sum(support_window) / len(support_window), 3) if support_window else None

    barrier_rows = [str(row.get("eating_barrier") or "") for row in logs]
    current_barrier = str(current_log.get("eating_barrier") or "")
    if current_barrier:
        barrier_rows.append(current_barrier)
    meaningful_barriers = [item for item in barrier_rows[-trend_window:] if item and item != "none"]

    condition = str(current_log.get("health_condition") or "")
    safety_index = 1.0 if condition in ELDERLY_PAUSE_CONDITIONS else 0.0
    return {
        "goal_metric": goal_metric,
        "history_days_available": len(logs),
        "history_window_days": history_window,
        "trend_window_days": trend_window,
        "current_adherence": None if current_adherence is None else round(current_adherence * 100, 2),
        "recent_adherence_average": None if adherence_average is None else round(adherence_average * 100, 2),
        "adherence_trend_direction": adherence_direction,
        "goal_progress_score": None if current_adherence is None else round(current_adherence * 100, 1),
        "appetite_average": appetite_average,
        "appetite_trend_direction": appetite_direction,
        "routine_average": routine_average,
        "routine_trend_direction": routine_direction,
        "difficulty_average": difficulty_average,
        "hydration_average": hydration_average,
        "hydration_trend_direction": hydration_direction,
        "support_need_average": support_need_average,
        "barrier_count": len(meaningful_barriers),
        "latest_barrier": current_barrier or None,
        "safety_index": safety_index,
        "data_sufficiency": "SUFFICIENT" if len(logs) >= 2 else "LIMITED" if len(logs) == 1 else "CURRENT_DAY_ONLY",
    }


def decide_elderly_adaptation(
    *,
    safety: dict[str, Any],
    indicators: dict[str, Any],
    current_log: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    day_number: int,
    previous_decision: str | None = None,
    block_days: int | None = None,
    rule_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Adapt elderly day plans from daily adherence/experience without medical inference."""
    rule = rule_version or RULE_VERSION
    final_day = int(block_days or (rule.get("thresholds") or RULE_VERSION["thresholds"]).get("block_days", 14))
    if safety.get("blocked"):
        decision = str(safety.get("decision") or "PAUSE")
        return _decision_payload(
            decision, reason_code="SAFETY_RECOVERY",
            reason_text=str(safety.get("reason") or "Kondisi harian membutuhkan jeda."),
            user_facing_reason=str(safety.get("user_facing_reason") or "Program dijeda sementara."),
            indicators=indicators, rule_version=rule, evidence_refs=["SAFETY_GUARD"],
            what_changed="Adaptasi rencana dihentikan sementara.",
            what_next="Lanjutkan dari hari yang sama setelah kondisi membaik.",
        )
    if day_number >= final_day:
        return _decision_payload(
            "BLOCK_REVIEW", reason_code="BLOCK_END_REACHED",
            reason_text="Hari terakhir guidance cycle telah selesai.",
            user_facing_reason="Cycle panduan selesai dan hasil hariannya siap ditinjau.",
            indicators=indicators, rule_version=rule, evidence_refs=["PROGRAM_BLOCK_SEMANTICS"],
            what_changed="Adaptasi harian berhenti pada akhir block.",
            what_next="Tinjau pola beberapa hari sebelum melanjutkan cycle berikutnya.",
        )

    history = int(indicators.get("history_days_available") or 0)
    adherence_raw = indicators.get("recent_adherence_average")
    adherence = None if adherence_raw is None else float(adherence_raw) / 100
    appetite = indicators.get("appetite_average")
    routine = indicators.get("routine_average")
    difficulty = indicators.get("difficulty_average")
    hydration = indicators.get("hydration_average")
    current_appetite = str(current_log.get("appetite_status") or "")
    current_difficulty = str(current_log.get("eating_difficulty") or "")
    current_routine = str(current_log.get("routine_adherence") or "")
    current_hydration = str(current_log.get("hydration_status") or "")
    current_barrier = str(current_log.get("eating_barrier") or "")

    recent = list(recent_logs or [])[-3:]
    poor_appetite_count = sum(1 for row in recent if row.get("appetite_status") == "poor") + (1 if current_appetite == "poor" else 0)
    difficult_count = sum(1 for row in recent if row.get("eating_difficulty") == "difficult") + (1 if current_difficulty == "difficult" else 0)
    poor_hydration_count = sum(1 for row in recent if row.get("hydration_status") == "poor") + (1 if current_hydration == "poor" else 0)
    barrier_count = sum(1 for row in recent if str(row.get("eating_barrier") or "") not in {"", "none"}) + (1 if current_barrier not in {"", "none"} else 0)
    low_routine = current_routine == "no" or (routine is not None and float(routine) <= 0.5)
    low_adherence = adherence is not None and adherence <= 0.55
    low_hydration = hydration is not None and float(hydration) <= 0.4
    if poor_appetite_count >= 2 or difficult_count >= 2 or poor_hydration_count >= 2 or barrier_count >= 2 or low_routine or low_adherence or low_hydration:
        return _decision_payload(
            "EASE", reason_code="ELDERLY_DAILY_BURDEN",
            reason_text="Input beberapa hari menunjukkan nafsu makan, cairan, hambatan makan, atau keterlaksanaan rencana perlu diringankan.",
            user_facing_reason="Ada pola yang membuat makan/minum lebih sulit dijalankan. Rencana berikutnya dipersempit ke langkah paling penting dan realistis.",
            indicators=indicators, rule_version=rule, evidence_refs=["ELDERLY_DAILY_LOG", "STAGE6_DAILY_HISTORY"],
            what_changed="Kompleksitas rencana berikutnya diturunkan.",
            what_next="Fokus pada satu langkah inti yang paling mudah dijalankan sambil mempertahankan tujuan utama.",
        )

    enough_history = history >= 2
    stable_good = (
        enough_history
        and (adherence is None or adherence >= 0.80)
        and (appetite is None or float(appetite) >= 0.75)
        and (routine is None or float(routine) >= 0.75)
        and (difficulty is None or float(difficulty) <= 0.35)
        and (hydration is None or float(hydration) >= 0.75)
        and current_barrier in {"", "none"}
    )
    if stable_good and previous_decision not in {"ADVANCE", "EASE"}:
        return _decision_payload(
            "ADVANCE", reason_code="ELDERLY_STABLE_PROGRESS",
            reason_text="Beberapa hari terakhir menunjukkan keterlaksanaan dan toleransi yang stabil.",
            user_facing_reason="Pola beberapa hari terakhir cukup stabil. Rencana berikutnya dapat menambah satu langkah kecil tanpa mengubah tujuan utama.",
            indicators=indicators, rule_version=rule, evidence_refs=["ELDERLY_DAILY_LOG", "STAGE6_DAILY_HISTORY"],
            what_changed="Rencana berikutnya dinaikkan satu langkah kecil.",
            what_next="Tambahkan satu kebiasaan kecil yang masih realistis dan catat respons hari berikutnya.",
        )

    return _decision_payload(
        "CONTINUE", reason_code="ELDERLY_STABLE_CONTINUATION" if history else "INSUFFICIENT_HISTORY",
        reason_text="Belum ada pola yang cukup kuat untuk mengubah tingkat rencana." if not history else "Pola harian masih sesuai untuk dilanjutkan.",
        user_facing_reason="Rencana utama tetap dilanjutkan sambil membaca pola dari input hari berikutnya.",
        indicators=indicators, rule_version=rule, evidence_refs=["ELDERLY_DAILY_LOG"],
        what_changed="Rencana utama tidak berubah.",
        what_next="Lanjutkan tindakan utama dan isi catatan hari berikutnya agar program dapat terus menyesuaikan.",
    )

def _decision_payload(
    decision: str,
    *,
    reason_code: str,
    reason_text: str,
    user_facing_reason: str,
    indicators: dict[str, Any],
    rule_version: dict[str, Any],
    evidence_refs: list[str] | None = None,
    what_changed: str,
    what_next: str,
) -> dict[str, Any]:
    rule = _rule_snapshot(rule_version)
    refs = list(evidence_refs or [])
    if f"ADAPTIVE_RULE:{rule['id']}" not in refs:
        refs.append(f"ADAPTIVE_RULE:{rule['id']}")
    return {
        "decision": decision,
        "reason_code": reason_code,
        "reason": reason_text,  # backward compatibility
        "reason_text": reason_text,
        "user_facing_reason": user_facing_reason,
        "evidence_refs": refs,
        "indicator_snapshot": deepcopy(indicators),
        "indicators_snapshot": deepcopy(indicators),  # backward compatibility
        "rule_version": rule,
        "rule_version_id": rule["id"],
        "next_plan_strategy": decision,
        "explanation": {
            "what_changed": what_changed,
            "why": user_facing_reason,
            "what_next": what_next,
        },
    }


def decide_adaptation(
    *,
    safety: dict[str, Any],
    indicators: dict[str, Any],
    current_log: dict[str, Any],
    recent_logs: list[dict[str, Any]],
    day_number: int,
    previous_decision: str | None = None,
    block_days: int | None = None,
    rule_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one deterministic Stage 7 decision with safety precedence."""
    rule = rule_version or RULE_VERSION
    thresholds = rule.get("thresholds") or RULE_VERSION["thresholds"]
    final_day = int(block_days or thresholds.get("block_days", 14))

    if safety.get("blocked"):
        decision = str(safety.get("decision") or "PAUSE")
        code = "SAFETY_RED_FLAG" if decision == "REFER" else "SAFETY_RECOVERY"
        return _decision_payload(
            decision,
            reason_code=code,
            reason_text=str(safety.get("reason") or "Safety condition menghentikan adaptasi normal."),
            user_facing_reason=str(safety.get("user_facing_reason") or "Untuk sementara target tidak dinaikkan."),
            indicators=indicators,
            rule_version=rule,
            evidence_refs=["SAFETY_GUARD", *[f"RED_FLAG:{row.get('code')}" for row in (safety.get("red_flags") or []) if row.get("code")]],
            what_changed="Adaptasi normal dihentikan untuk sementara.",
            what_next=(
                "Segera ikuti arahan keselamatan yang ditampilkan dan ulangi asesmen sebelum memulai cycle baru."
                if decision == "REFER"
                else "Fokus pada pemulihan; program tidak menaikkan target saat kondisi ini aktif."
            ),
        )

    # Stage 8 owns the review itself; Stage 7 only hands off at block end.
    if day_number >= final_day:
        return _decision_payload(
            "BLOCK_REVIEW",
            reason_code="BLOCK_END_REACHED",
            reason_text="Hari terakhir guidance cycle telah selesai; keputusan lanjutan harus melalui Block Review.",
            user_facing_reason="Cycle panduan sudah mencapai akhir block. Hasilnya perlu ditinjau sebelum menentukan langkah berikutnya.",
            indicators=indicators,
            rule_version=rule,
            evidence_refs=["PROGRAM_BLOCK_SEMANTICS"],
            what_changed="Cycle 14 hari selesai dan adaptasi harian berhenti pada tahap review.",
            what_next="Tinjau hasil block sebelum memutuskan melanjutkan, memperpanjang, atau menyusun ulang target.",
        )

    acceptance = str(current_log.get("acceptance") or "")
    new_food = bool(current_log.get("new_food"))
    window = int(thresholds.get("trend_window_days", 3))
    recent = list(recent_logs or [])[-window:]
    refusal_count = sum(1 for row in recent if row.get("acceptance") == "refused") + (1 if acceptance == "refused" else 0)
    difficult_count = sum(1 for row in recent if row.get("parent_difficulty") == "difficult") + (1 if current_log.get("parent_difficulty") == "difficult" else 0)
    adherence_average_raw = indicators.get("recent_adherence_average")
    adherence_average = None if adherence_average_raw is None else float(adherence_average_raw) / 100
    burden = indicators.get("burden_index")
    burden = 0.0 if burden is None else float(burden)
    acceptance_average = indicators.get("acceptance_trend")
    acceptance_average = 0.0 if acceptance_average is None else float(acceptance_average)
    history_marker = indicators.get("history_days_available")
    if history_marker is None:
        # Backward compatibility for callers/tests created before Stage 7 made
        # data sufficiency explicit in the indicator contract.
        history_points = len(recent_logs or [])
        if indicators.get("trend_direction") in {"IMPROVING", "DECLINING", "STABLE"}:
            history_points = max(history_points, int(thresholds.get("minimum_trend_points", 2)))
    else:
        history_points = int(history_marker)

    if new_food and acceptance == "refused":
        return _decision_payload(
            "REPEAT",
            reason_code="NEW_FOOD_REJECTED",
            reason_text="New food/target exposure ditolak pada daily log.",
            user_facing_reason="Makanan target belum diterima. Besok kita coba lagi dengan cara yang berbeda tanpa menambah tantangan baru.",
            indicators=indicators,
            rule_version=rule,
            evidence_refs=["DAILY_LOG:NEW_FOOD", "DAILY_LOG:ACCEPTANCE"],
            what_changed="Target utama dipertahankan dan tidak dinaikkan.",
            what_next="Ulangi target yang sama dengan penyajian yang sesuai tanpa menambah tantangan baru.",
        )

    low_adherence = adherence_average is not None and adherence_average <= float(thresholds.get("ease_adherence_average_max", 0.50))
    repeated_difficulty = difficult_count >= 2
    declining = indicators.get("trend_direction") == "DECLINING" and history_points >= 1
    repeated_refusal = refusal_count >= int(thresholds.get("ease_refusal_count", 2))
    high_burden_with_support = burden >= 0.75 and (low_adherence or repeated_difficulty or history_points >= 1)
    if repeated_refusal or declining or high_burden_with_support:
        return _decision_payload(
            "EASE",
            reason_code=("REPEATED_REFUSAL" if repeated_refusal else "DECLINING_TREND" if declining else "HIGH_BURDEN_LOW_ADHERENCE"),
            reason_text="History menunjukkan penolakan berulang, tren menurun, atau beban yang tinggi bersama kesulitan menjalankan target.",
            user_facing_reason="Beberapa sesi terakhir terasa lebih sulit. Rencana berikutnya dibuat lebih ringan tanpa mengganti goal utama.",
            indicators=indicators,
            rule_version=rule,
            evidence_refs=["STAGE6_DAILY_HISTORY", "CAREGIVER_BURDEN"],
            what_changed="Kompleksitas rencana berikutnya diturunkan.",
            what_next="Fokus pada langkah inti yang lebih ringan sambil mempertahankan goal utama.",
        )

    minimum_points = int(thresholds.get("minimum_trend_points", 2))
    enough_history_for_advance = history_points >= minimum_points
    adherence_good = adherence_average is None or adherence_average >= float(thresholds.get("advance_adherence_average_min", 0.75))
    advance_candidate = (
        enough_history_for_advance
        and indicators.get("trend_direction") == "IMPROVING"
        and acceptance_average >= float(thresholds.get("advance_acceptance_average", 0.80))
        and burden <= float(thresholds.get("advance_burden_max", 0.35))
        and adherence_good
        and acceptance != "refused"
    )
    if advance_candidate:
        if previous_decision in {"EASE", "ADVANCE"}:
            return _decision_payload(
                "CONTINUE",
                reason_code="ADVANCE_GUARDRAIL",
                reason_text=f"Guardrail mencegah ADVANCE setelah {previous_decision} pada keputusan sebelumnya.",
                user_facing_reason="Penerimaan membaik, tetapi program mempertahankan tingkat hari ini agar perubahan tidak terlalu cepat.",
                indicators=indicators,
                rule_version=rule,
                evidence_refs=["ADVANCE_GUARDRAIL"],
                what_changed="Tidak ada kenaikan tantangan hari berikutnya.",
                what_next="Pertahankan tingkat saat ini satu hari lagi sebelum mempertimbangkan peningkatan berikutnya.",
            )
        return _decision_payload(
            "ADVANCE",
            reason_code="STABLE_IMPROVEMENT",
            reason_text="History menunjukkan penerimaan membaik, burden rendah, dan performa cukup stabil untuk satu peningkatan kecil.",
            user_facing_reason="Penerimaan beberapa hari terakhir membaik. Rencana berikutnya dapat menambah satu tantangan kecil.",
            indicators=indicators,
            rule_version=rule,
            evidence_refs=["STAGE6_DAILY_HISTORY", "ADVANCE_GUARDRAIL"],
            what_changed="Rencana berikutnya dinaikkan satu langkah kecil.",
            what_next="Tambahkan maksimal satu tantangan baru sambil mempertahankan goal utama.",
        )

    no_history = history_points == 0
    return _decision_payload(
        "CONTINUE",
        reason_code="INSUFFICIENT_HISTORY" if no_history else "STABLE_CONTINUATION",
        reason_text=(
            "Belum cukup history untuk mengubah tingkat tantangan secara yakin."
            if no_history
            else "Tidak ada safety flag atau pola history yang cukup kuat untuk mengubah tingkat tantangan."
        ),
        user_facing_reason=(
            "Belum cukup data untuk mengubah target hari ini. Rencana utama tetap dilanjutkan."
            if no_history
            else "Rencana tetap dilanjutkan karena pola saat ini belum membutuhkan perubahan besar."
        ),
        indicators=indicators,
        rule_version=rule,
        evidence_refs=["STAGE6_DAILY_HISTORY"],
        what_changed="Rencana utama tidak berubah.",
        what_next="Lanjutkan tindakan utama dan simpan hasil aktual agar pola beberapa hari dapat dinilai.",
    )


def plan_adjustments(decision: str, current_log: dict[str, Any]) -> dict[str, Any]:
    strategy = decision
    if decision == "REPEAT":
        return {"strategy": strategy, "difficulty": "SAME_OR_SIMPLER", "complexity": "same_or_simpler", "new_challenge": False, "new_challenges": [], "note": "Ulangi target yang sama; boleh ubah bentuk penyajian yang aman."}
    if decision == "EASE":
        return {"strategy": strategy, "difficulty": "LOWER", "complexity": "lighter", "new_challenge": False, "new_challenges": [], "note": "Kurangi kompleksitas dukungan tanpa mengganti goal utama."}
    if decision == "ADVANCE":
        return {"strategy": strategy, "difficulty": "ONE_SMALL_STEP", "complexity": "one_small_step", "new_challenge": True, "new_challenges": ["one_small_challenge"], "max_new_challenges": 1, "note": "Maksimum satu tantangan baru; jangan menaikkan porsi bila penolakan terjadi."}
    if decision in {"PAUSE", "REFER"}:
        return {"strategy": strategy, "difficulty": "RECOVERY", "complexity": "recovery", "new_challenge": False, "new_challenges": [], "note": "Tidak mengoptimalkan goal saat safety condition aktif."}
    if decision == "BLOCK_REVIEW":
        return {"strategy": strategy, "difficulty": "REVIEW", "complexity": "review", "new_challenge": False, "new_challenges": [], "note": "Tidak membuat daily challenge baru sampai Block Review dilakukan."}
    return {"strategy": "CONTINUE", "difficulty": "STEADY", "complexity": "steady", "new_challenge": False, "new_challenges": [], "note": "Pertahankan fokus saat ini."}


def daily_summary(log: dict[str, Any], indicators: dict[str, Any], decision: dict[str, Any], next_preview: str) -> dict[str, Any]:
    if any(key in log for key in ("appetite_status", "eating_difficulty", "routine_adherence")):
        appetite = str(log.get("appetite_status") or "")
        difficulty = str(log.get("eating_difficulty") or "")
        routine = str(log.get("routine_adherence") or "")
        went_well = "Catatan harian tersimpan untuk membantu penyesuaian rencana berikutnya."
        if appetite == "good" and routine == "yes":
            went_well = "Nafsu makan dan keterlaksanaan rencana hari ini tercatat baik."
        difficult = "Tidak ada kesulitan utama yang dicatat."
        if difficulty == "difficult":
            difficult = "Menjalankan atau menerima pola makan hari ini terasa sulit."
        elif appetite == "poor":
            difficult = "Nafsu makan hari ini tercatat rendah."
        explanation = decision.get("explanation") or {}
        return {
            "what_went_well": went_well,
            "what_was_difficult": difficult,
            "today_progress": indicators.get("goal_progress_score"),
            "adaptation_decision": decision.get("decision"),
            "why_plan_changes": decision.get("user_facing_reason"),
            "what_changed": explanation.get("what_changed"),
            "what_next": explanation.get("what_next"),
            "tomorrow_preview": next_preview,
        }
    acceptance = str(log.get("acceptance") or "")
    portion = str(log.get("portion") or "")
    went_well = "Daily log tersimpan."
    if acceptance == "liked":
        went_well = "Makanan diterima dengan baik hari ini."
    elif acceptance == "neutral":
        went_well = "Anak masih dapat mencoba makanan hari ini."
    difficult = "Tidak ada kesulitan utama yang dicatat."
    if acceptance == "refused":
        difficult = "Makanan ditolak pada sesi yang dicatat."
    elif portion in {"little", "none"}:
        difficult = "Porsi yang termakan masih sedikit."
    explanation = decision.get("explanation") or {}
    return {
        "what_went_well": went_well,
        "what_was_difficult": difficult,
        "today_progress": indicators.get("goal_progress_score"),
        "adaptation_decision": decision.get("decision"),
        "why_plan_changes": decision.get("user_facing_reason"),
        "what_changed": explanation.get("what_changed"),
        "what_next": explanation.get("what_next"),
        "tomorrow_preview": next_preview,
    }


def missing_day_decision(
    indicators: dict[str, Any] | None = None,
    *,
    rule_version: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Safe deterministic decision when a scheduled day has no actual result."""
    return _decision_payload(
        "CONTINUE",
        reason_code="MISSING_DAY_NO_RESULT",
        reason_text="Hari dilewati tanpa daily result; tidak dianggap berhasil maupun gagal.",
        user_facing_reason="Hari ini belum memiliki hasil aktual. Rencana berikutnya dilanjutkan dengan langkah yang ringan tanpa menilai hari ini sebagai gagal.",
        indicators=dict(indicators or {}),
        rule_version=rule_version or RULE_VERSION,
        evidence_refs=["MISSING_DAY_POLICY"],
        what_changed="Tidak ada peningkatan tantangan berdasarkan hari yang tidak memiliki data.",
        what_next="Lanjutkan rencana berikutnya dan simpan hasil aktual saat tersedia.",
    )
