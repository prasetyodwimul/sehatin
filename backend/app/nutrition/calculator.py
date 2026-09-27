from app.schemas.nutrition import NutritionRequest

from .references import (
    CHILD_AKG,
    ELDERLY_AKG,
    GERIATRIC_PROTEIN_MIN_G_PER_KG,
    MPASI_COMPLEMENTARY_ENERGY_KCAL,
    MPASI_PATTERN,
)
from .rules import has_medical_context
from .elderly_condition_context import build_elderly_health_context


def mpasi_age_band(age_months: int) -> str:
    if age_months <= 8:
        return "6-8"
    if age_months <= 11:
        return "9-11"
    return "12-23"


def child_akg_band(age_months: int) -> str:
    if age_months <= 11:
        return "6-11_months"
    if age_months <= 47:
        return "1-3_years"
    return "4-6_years"


def elderly_akg_band(age_years: int) -> str:
    if age_years <= 64:
        return "60-64"
    if age_years <= 80:
        return "65-80"
    return "81+"


def age_band_label(req: NutritionRequest) -> str:
    if req.stage == "mpasi":
        return f"MPASI {mpasi_age_band(int(req.age_months or 6))} bulan"
    if req.stage == "toddler":
        return "Toddler 24–59 bulan"
    band = elderly_akg_band(int(req.age_years or 60))
    return f"Lansia {band} tahun" if band != "81+" else "Lansia 81+ tahun"


def _format_akg(values: dict[str, int]) -> dict[str, str]:
    return {
        "energi_referensi": f"{values['energy_kcal']} kkal/hari",
        "protein_referensi": f"{values['protein_g']} g/hari",
        "lemak_referensi": f"{values['fat_g']} g/hari",
        "karbohidrat_referensi": f"{values['carbohydrate_g']} g/hari",
        "serat_referensi": f"{values['fiber_g']} g/hari",
        "air_referensi": f"{values['water_ml']} mL/hari dari total asupan cairan/makanan sebagai angka kecukupan populasi",
    }


def calculate_estimated_needs(req: NutritionRequest) -> dict[str, str]:
    """Return population-reference values with stage-specific context.

    These are intentionally called *referensi*, not prescriptions. Individual
    needs vary with growth, intake, activity, illness and clinical status.
    """
    if req.stage in {"mpasi", "toddler"}:
        age = int(req.age_months or 6)
        values = CHILD_AKG[child_akg_band(age)]
        result = _format_akg(values)

        if req.stage == "mpasi":
            band = mpasi_age_band(age)
            if req.feeding_mode == "breastmilk":
                result["energi_dari_mpasi"] = (
                    f"Sekitar {MPASI_COMPLEMENTARY_ENERGY_KCAL[band]} kkal/hari dari makanan pendamping "
                    "sebagai panduan populasi untuk anak yang masih mendapat ASI."
                )
            else:
                result["energi_dari_mpasi"] = (
                    "Tidak dihitung sebagai angka tunggal karena kebutuhan dari makanan pendamping bergantung pada "
                    "jumlah ASI/formula yang benar-benar dikonsumsi. Gunakan pola makan dan sinyal lapar/kenyang sebagai panduan."
                )
        return result

    age = int(req.age_years or 60)
    sex = "male" if req.sex == "male" else "female"
    values = ELDERLY_AKG[sex][elderly_akg_band(age)]
    result = _format_akg(values)

    if req.weight_kg and not has_medical_context(req) and not req.has_condition:
        protein_orientation = req.weight_kg * GERIATRIC_PROTEIN_MIN_G_PER_KG
        result["protein_berdasarkan_berat"] = (
            f"Sekitar {protein_orientation:.0f} g/hari sebagai orientasi umum minimal berbasis berat badan untuk lansia sehat; "
            "angka ini perlu disesuaikan bila ada penyakit atau kebutuhan klinis."
        )
    return result


def meal_pattern(req: NutritionRequest) -> dict[str, str]:
    if req.stage == "mpasi":
        return dict(MPASI_PATTERN[mpasi_age_band(int(req.age_months or 6))])

    if req.stage == "toddler":
        pattern = {
            "ritme": "3 waktu makan utama dengan 1–2 camilan bergizi sebagai pola praktis; sesuaikan dengan rutinitas dan rasa lapar anak.",
            "porsi": "Mulai dari porsi anak yang wajar dan biarkan anak menentukan berapa banyak yang dihabiskan; jangan memaksa makan.",
            "minuman": "Utamakan air putih; hindari menjadikan minuman manis sebagai minuman rutin.",
        }
        if req.appetite == "low":
            pattern["penyesuaian_nafsu_makan"] = "Gunakan porsi lebih kecil namun teratur dan pilih makanan padat gizi."
        elif req.appetite == "high":
            pattern["penyesuaian_nafsu_makan"] = "Pertahankan jadwal makan teratur dan tawarkan tambahan dari makanan utuh bergizi bila masih lapar."
        return pattern

    pattern = {
        "ritme": "3 waktu makan utama; tambahkan 1–2 selingan bila membantu memenuhi kebutuhan atau nafsu makan rendah.",
        "protein": "Sebarkan sumber protein pada beberapa waktu makan, bukan hanya satu kali sehari.",
        "cairan": "Minum secara teratur sepanjang hari kecuali tenaga kesehatan memberikan pembatasan cairan.",
    }
    if req.appetite == "low":
        pattern["penyesuaian_nafsu_makan"] = "Porsi lebih kecil dan lebih sering dapat lebih mudah dipenuhi dibanding porsi besar."
    if req.chewing_difficulty:
        pattern["tekstur"] = "Pilih makanan lunak dan mudah dikunyah tanpa mengurangi kepadatan gizi."
    if req.swallowing_difficulty:
        pattern["tekstur"] = "Tekstur makanan/minuman tidak dipersonalisasi karena gangguan menelan memerlukan penilaian profesional."
    health_context = build_elderly_health_context(req)
    if health_context.get("has_condition") and health_context.get("food_guidance"):
        pattern["konteks_kesehatan"] = " ".join((health_context.get("food_guidance") or [])[:2])
    return pattern
