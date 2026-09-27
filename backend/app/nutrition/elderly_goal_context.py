from __future__ import annotations

from typing import Any


ELDERLY_GOAL_KEYS = {
    "elderly_safe_nutrition_routine",
    "elderly_hydration_routine",
    "elderly_supported_meal_routine",
    "elderly_meal_routine",
    "elderly_balanced_meal_routine",
}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_elderly_program_goal(
    profile: dict[str, Any] | None,
    *,
    health_context: dict[str, Any] | None = None,
    lifestyle_context: dict[str, Any] | None = None,
    duration_days: int = 14,
    preferred_goal_key: str | None = None,
) -> dict[str, Any]:
    """Return one clear behavioural goal for the elderly program.

    Goal selection is driven by eating/hydration/function context rather than by
    completed days. ``preferred_goal_key`` is used by an extension cycle when the
    previous cycle shows a clearer next focus. It never creates a diagnosis or a
    clinical diet prescription.
    """
    profile = dict(profile or {})
    health_context = dict(health_context or {})
    lifestyle_context = dict(lifestyle_context or {})
    target_days = max(1, round(duration_days * 0.7))

    hydration = str(profile.get("hydration_pattern") or lifestyle_context.get("hydration_pattern") or "unknown")
    independence = str(profile.get("eating_independence") or lifestyle_context.get("eating_independence") or "unknown")
    caregiver = str(profile.get("caregiver_support") or lifestyle_context.get("caregiver_support") or "unknown")
    appetite = str(profile.get("appetite") or "typical")
    meals = max(1, min(10, _int(profile.get("meal_frequency"), 3)))
    swallowing = bool(profile.get("swallowing_difficulty"))

    auto_goal = (
        "elderly_safe_nutrition_routine" if swallowing else
        "elderly_hydration_routine" if hydration in {"sometimes_low", "often_low"} else
        "elderly_supported_meal_routine" if independence in {"needs_reminder", "needs_setup", "needs_assistance"} or caregiver in {"sometimes", "daily"} else
        "elderly_meal_routine" if appetite == "low" or meals <= 2 else
        "elderly_balanced_meal_routine"
    )
    goal_key = preferred_goal_key if preferred_goal_key in ELDERLY_GOAL_KEYS else auto_goal

    if goal_key == "elderly_safe_nutrition_routine":
        title = "Jaga asupan bergizi dengan pola makan/minum yang sudah aman"
        description = (
            "Program membantu menjaga kesempatan makan, kandungan makanan, dan pola minum sambil memantau kenyamanan. "
            "Aplikasi tidak menentukan level tekstur atau kekentalan terapi."
        )
        baseline_label = "Kesulitan menelan dilaporkan pada assessment" if swallowing else "Pola aman perlu tetap dipertahankan"
        target_label = f"Fokus makan/minum aman terlaksana pada ≥{target_days} dari {duration_days} hari"
        measurement = "hasil aktual To Do makan/minum + log kenyamanan dan cairan"
    elif goal_key == "elderly_hydration_routine":
        title = "Bangun kebiasaan minum yang lebih teratur"
        description = (
            "Program membantu membuat kesempatan minum lebih konsisten bersama pola makan harian tanpa menetapkan target volume cairan individual."
        )
        baseline_label = {
            "sometimes_low": "Kadang minum lebih sedikit",
            "often_low": "Sering minum lebih sedikit",
            "adequate": "Pola minum sudah cukup teratur pada assessment",
        }.get(hydration, "Keteraturan minum perlu dipantau")
        target_label = f"Pola minum teratur/lebih baik pada ≥{target_days} dari {duration_days} hari"
        measurement = "hasil aktual To Do hidrasi + log cairan harian"
    elif goal_key == "elderly_supported_meal_routine":
        title = "Jalankan waktu makan/minum dengan dukungan yang sesuai"
        description = (
            "Program memantau apakah pengingat, persiapan, atau bantuan yang tersedia membuat makan/minum lebih mudah dan tetap realistis."
        )
        baseline_label = {
            "needs_reminder": "Perlu pengingat saat makan/minum",
            "needs_setup": "Perlu makanan/minuman disiapkan",
            "needs_assistance": "Perlu bantuan langsung saat makan/minum",
        }.get(independence, "Dukungan makan/minum digunakan pada assessment")
        target_label = f"Rutinitas dengan dukungan sesuai tercapai pada ≥{target_days} dari {duration_days} hari"
        measurement = "hasil aktual To Do dukungan + log kebutuhan bantuan"
    elif goal_key == "elderly_meal_routine":
        title = "Jaga kesempatan makan utama tetap konsisten"
        description = (
            "Program membantu mempertahankan kesempatan makan utama dan membaca perubahan nafsu makan agar langkah berikutnya bisa diringankan atau ditingkatkan."
        )
        baseline_label = f"{meals} kali makan utama/hari" + (" · nafsu makan menurun" if appetite == "low" else "")
        target_label = f"Pola makan utama terlaksana pada ≥{target_days} dari {duration_days} hari"
        measurement = "hasil aktual To Do waktu makan + log nafsu makan"
    else:
        title = "Pertahankan pola makan seimbang yang konsisten"
        description = (
            "Program membantu menjaga keteraturan makan, sumber energi dan protein, sayur/buah, hidrasi, serta pengalaman menjalankan rencana dari hari ke hari."
        )
        baseline_label = f"{meals} kali makan utama/hari pada assessment"
        target_label = f"Komposisi dan rutinitas harian tercapai pada ≥{target_days} dari {duration_days} hari"
        measurement = "hasil aktual To Do komposisi makan + log harian Lansia"

    condition_labels = [str(x) for x in health_context.get("condition_labels") or [] if str(x).strip()]
    if not condition_labels:
        raw_labels = {
            "diabetes": "Diabetes",
            "hypertension": "Hipertensi",
            "high_cholesterol": "Kolesterol Tinggi",
            "heart_disease": "Penyakit Jantung",
            "kidney_disease": "Penyakit Ginjal",
        }
        for condition in profile.get("conditions") or []:
            key = str(condition)
            if key == "other" and profile.get("other_condition"):
                condition_labels.append(str(profile.get("other_condition")))
            elif key in raw_labels:
                condition_labels.append(raw_labels[key])
    if condition_labels:
        description += " Konteks makanan juga mempertimbangkan kondisi yang dilaporkan: " + ", ".join(condition_labels[:3]) + "."

    return {
        "goal_key": goal_key,
        "title": title,
        "description": description,
        "baseline": 0,
        "target": target_days,
        "unit": "hari berhasil",
        "measurement_method": measurement,
        "duration": duration_days,
        "priority": 1,
        "status": "NOT_STARTED",
        "baseline_label": baseline_label,
        "target_label": target_label,
        "selection_reason": {
            "elderly_safe_nutrition_routine": "Kesulitan menelan membuat program memprioritaskan kecukupan dan kenyamanan tanpa mengatur tekstur terapi.",
            "elderly_hydration_routine": "Assessment atau cycle sebelumnya menunjukkan keteraturan minum sebagai fokus yang paling perlu dibangun.",
            "elderly_supported_meal_routine": "Makan/minum lebih realistis bila dukungan yang sesuai tersedia pada waktu yang dibutuhkan.",
            "elderly_meal_routine": "Kesempatan makan dan nafsu makan menjadi fokus utama agar asupan harian tidak mudah terlewat.",
            "elderly_balanced_meal_routine": "Pola dasar relatif stabil sehingga program dapat menekankan keseimbangan dan variasi kelompok pangan.",
        }[goal_key],
    }
