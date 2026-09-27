from __future__ import annotations

from typing import Any

from app.schemas.nutrition import NutritionRequest

# Centralized elderly chronic-condition education mapping.  These rules only
# interpret conditions the user explicitly reports; they never infer a diagnosis.
CONDITION_LABELS: dict[str, str] = {
    "diabetes": "Diabetes",
    "hypertension": "Hipertensi",
    "high_cholesterol": "Kolesterol Tinggi",
    "heart_disease": "Penyakit Jantung",
    "kidney_disease": "Penyakit Ginjal",
    "other": "Lainnya",
}

CONDITION_RULES: dict[str, dict[str, list[str] | bool]] = {
    "diabetes": {
        "focus": ["Keteraturan waktu makan", "Kualitas sumber karbohidrat", "Batasi makanan/minuman tinggi gula tambahan"],
        "recommendations": [
            "Pertahankan waktu makan yang cukup teratur dan pilih karbohidrat dari makanan utuh/berserat bila sesuai toleransi.",
            "Batasi makanan dan minuman dengan gula tambahan tinggi sebagai bagian dari pola makan seimbang.",
        ],
        "food_guidance": ["Padukan sumber karbohidrat dengan sayur, sumber protein, dan lemak sehat dalam pola makan seimbang."],
        "daily_actions": ["Pilih satu waktu makan hari ini untuk memadukan karbohidrat dengan sayur dan sumber protein."],
        "consult": False,
    },
    "hypertension": {
        "focus": ["Kesadaran garam/natrium", "Pilih makanan segar dan minim proses", "Pola makan seimbang"],
        "recommendations": [
            "Kurangi kebiasaan menambahkan garam berlebih dan batasi pilihan makanan sangat asin/tinggi natrium.",
            "Utamakan makanan segar dan olahan minimal sebagai bagian dari pola makan sehari-hari.",
        ],
        "food_guidance": ["Pilih lauk dan pendamping yang tidak bergantung pada bumbu sangat asin atau makanan sangat diproses."],
        "daily_actions": ["Pada satu waktu makan hari ini, pilih makanan yang lebih rendah garam dan minim proses."],
        "consult": False,
    },
    "high_cholesterol": {
        "focus": ["Kualitas lemak", "Serat dari sayur, buah, dan pangan utuh", "Kurangi lemak jenuh/trans"],
        "recommendations": [
            "Prioritaskan sumber lemak tidak jenuh dan kurangi pilihan yang tinggi lemak jenuh atau lemak trans.",
            "Sertakan sayur, buah, dan pangan utuh kaya serat secara teratur.",
        ],
        "food_guidance": ["Pilih cara masak dan bahan yang membantu mengurangi lemak jenuh tanpa mengurangi kecukupan makan."],
        "daily_actions": ["Pilih satu sumber lemak yang lebih baik dan sertakan sayur atau buah pada salah satu waktu makan."],
        "consult": False,
    },
    "heart_disease": {
        "focus": ["Pola makan seimbang untuk kesehatan jantung", "Kualitas lemak", "Kesadaran garam/natrium"],
        "recommendations": [
            "Gunakan pola makan seimbang dengan lebih banyak makanan utuh, sayur/buah, serta sumber lemak yang lebih baik.",
            "Perhatikan asupan makanan sangat asin dan pilihan tinggi lemak jenuh sebagai bagian dari pola makan harian.",
        ],
        "food_guidance": ["Utamakan variasi makanan utuh dengan cara masak sederhana dan bumbu yang tidak berlebihan."],
        "daily_actions": ["Pada satu waktu makan hari ini, pilih kombinasi makanan utuh dengan sayur/buah dan bumbu secukupnya."],
        "consult": False,
    },
    "kidney_disease": {
        "focus": ["Pola makan cukup dan teratur", "Penyesuaian khusus mengikuti arahan klinis yang sudah dimiliki"],
        "recommendations": [
            "Gunakan prinsip makan seimbang secara umum dan ikuti pembatasan diet yang memang sudah diberikan oleh tenaga kesehatan.",
            "Kebutuhan protein, kalium, fosfor, natrium, dan cairan dapat berbeda menurut kondisi klinis sehingga SEHATIN tidak menetapkan pembatasan spesifik otomatis.",
        ],
        "food_guidance": ["Contoh makanan tetap bersifat umum; jangan mengubah pembatasan protein, mineral, atau cairan yang sudah diberikan tenaga kesehatan."],
        "daily_actions": ["Ikuti pola makan yang sudah dapat ditoleransi dan pertahankan pembatasan yang memang sudah diarahkan tenaga kesehatan."],
        "consult": True,
    },
    "other": {
        "focus": ["Pola makan seimbang dan cukup", "Penyesuaian spesifik hanya bila didukung informasi klinis yang memadai"],
        "recommendations": [
            "Gunakan prinsip pola makan seimbang secara umum. SEHATIN tidak membuat aturan diet penyakit hanya dari nama kondisi yang dimasukkan.",
        ],
        "food_guidance": ["Contoh makanan tetap bersifat umum sampai ada panduan klinis yang memang diketahui."],
        "daily_actions": ["Pertahankan pola makan yang seimbang dan catat bagian yang sulit diterapkan untuk dibahas lebih lanjut bila diperlukan."],
        "consult": True,
    },
}


def _unique(values: list[str], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if limit and len(result) >= limit:
            break
    return result


def build_elderly_health_context(req: NutritionRequest) -> dict[str, Any]:
    if req.stage != "elderly" or not req.has_condition:
        return {"has_condition": False, "conditions": [], "condition_labels": [], "other_condition": None}

    conditions = [str(value) for value in req.conditions]
    labels: list[str] = []
    focus: list[str] = []
    recommendations: list[str] = []
    food_guidance: list[str] = []
    daily_actions: list[str] = []
    needs_consult = False

    for condition in conditions:
        rule = CONDITION_RULES.get(condition)
        if not rule:
            continue
        if condition == "other" and req.other_condition:
            labels.append(req.other_condition)
        else:
            labels.append(CONDITION_LABELS.get(condition, condition))
        focus.extend(rule.get("focus", []))
        recommendations.extend(rule.get("recommendations", []))
        food_guidance.extend(rule.get("food_guidance", []))
        daily_actions.extend(rule.get("daily_actions", []))
        needs_consult = needs_consult or bool(rule.get("consult"))

    consultation_note = None
    if needs_consult:
        consultation_note = (
            "Untuk penyesuaian pola makan yang spesifik terhadap kondisi ini, gunakan arahan tenaga kesehatan yang mengetahui kondisi klinis dan terapi yang sedang dijalani."
        )

    return {
        "has_condition": True,
        "conditions": conditions,
        "condition_labels": _unique(labels),
        "other_condition": req.other_condition,
        "nutrition_focus": _unique(focus, limit=6),
        "recommendations": _unique(recommendations, limit=8),
        "food_guidance": _unique(food_guidance, limit=5),
        "daily_actions": _unique(daily_actions, limit=6),
        "program_focus": _unique(focus, limit=4),
        "needs_clinical_consultation": needs_consult,
        "consultation_note": consultation_note,
        "mapping_kind": "USER_REPORTED_CONTEXT_MAPPING",
        "evidence_rule_status": "NO_CONDITION_SPECIFIC_RULE_IN_EXISTING_NUTRITION_ENGINE",
        "source_note": "Kondisi kesehatan berasal dari informasi yang dilaporkan user; mapping digunakan sebagai konteks edukasi dan bukan evidence rule klinis atau diagnosis.",
    }


def contextual_recommendations(req: NutritionRequest, base: list[str]) -> list[str]:
    context = build_elderly_health_context(req)
    if not context.get("has_condition"):
        return base
    return _unique([*context.get("recommendations", []), *base], limit=10)


def contextual_sample_menu(req: NutritionRequest, menus: list[str]) -> list[str]:
    context = build_elderly_health_context(req)
    if not context.get("has_condition") or not menus:
        return menus
    guidance = list(context.get("food_guidance") or [])
    if not guidance:
        return menus
    note = " ".join(guidance[:2])
    return [f"{menu} Catatan konteks: {note}" for menu in menus]
