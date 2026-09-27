from app.schemas.nutrition import NutritionRequest

from .elderly_condition_context import build_elderly_health_context
from .elderly_lifestyle_context import build_elderly_lifestyle_context

from .constants import MEDICAL_CONTEXT_TERMS


def has_medical_context(req: NutritionRequest) -> bool:
    text = " ".join(filter(None, [req.medical_context, req.notes])).lower()
    return bool(req.medical_context) or any(term in text for term in MEDICAL_CONTEXT_TERMS)


def personalization_is_limited(req: NutritionRequest) -> bool:
    return has_medical_context(req) or req.swallowing_difficulty


def build_input_summary(req: NutritionRequest) -> list[str]:
    items: list[str] = []
    if req.stage in {"mpasi", "toddler"}:
        items.append(f"Usia: {req.age_months} bulan")
    else:
        sex_label = "Laki-laki" if req.sex == "male" else "Perempuan"
        items.extend([f"Usia: {req.age_years} tahun", f"Jenis kelamin: {sex_label}"])

    if req.stage == "mpasi" and req.feeding_mode:
        feed_label = {
            "breastmilk": "ASI",
            "formula": "Formula",
            "mixed": "ASI + formula",
        }[req.feeding_mode]
        items.append(f"Pola susu: {feed_label}")
    if req.weight_kg:
        items.append(f"Berat badan: {req.weight_kg:g} kg")
    appetite_label = {"low": "rendah", "typical": "biasa", "high": "tinggi"}[req.appetite]
    items.append(f"Nafsu makan: {appetite_label}")
    if req.stage == "mpasi" and req.texture_level:
        texture_label = {
            "smooth_mashed": "lumat/halus kental",
            "mashed_lumpy": "lumat lebih kasar/bertekstur",
            "finger_food": "finger food lunak",
            "family_soft": "makanan keluarga lunak",
        }[req.texture_level]
        items.append(f"Tekstur yang mampu dimakan: {texture_label}")
    if req.meal_frequency and req.stage in {"mpasi", "toddler"}:
        items.append(f"Frekuensi makan/camilan padat saat ini: {req.meal_frequency} kali/hari")
    if req.stage == "elderly":
        activity_label = {"low": "rendah", "moderate": "sedang", "high": "tinggi"}[req.activity_level]
        items.append(f"Aktivitas harian: {activity_label}")
        health_context = build_elderly_health_context(req)
        if health_context.get("has_condition"):
            items.append("Kondisi kesehatan yang dilaporkan: " + ", ".join(health_context.get("condition_labels") or []))
        lifestyle = build_elderly_lifestyle_context(req)
        items.append("Kebiasaan minum: " + str(lifestyle.get("hydration_label") or "Belum ditentukan"))
        items.append("Kemandirian makan: " + str(lifestyle.get("eating_independence_label") or "Belum ditentukan"))
        items.append("Dukungan caregiver: " + str(lifestyle.get("caregiver_support_label") or "Belum ditentukan"))
    if req.allergies:
        items.append("Alergi yang difilter: " + ", ".join(req.allergies))
    if req.dietary_restrictions:
        items.append("Batasan makanan: " + ", ".join(req.dietary_restrictions))
    return items


def build_safety_notes(req: NutritionRequest) -> list[str]:
    notes = [
        "Hasil merupakan panduan edukatif berbasis referensi populasi, bukan diagnosis atau resep diet medis.",
        "Jangan mengubah obat, terapi, atau pembatasan diet dari tenaga kesehatan berdasarkan hasil ini.",
    ]

    if req.allergies:
        notes.append(
            "Bahan yang cocok dengan alergi yang dicantumkan telah difilter dari contoh menu. Riwayat alergi berat tetap memerlukan arahan tenaga kesehatan."
        )

    if has_medical_context(req):
        notes.append(
            "Kondisi medis terdeteksi. Personalisasi dibatasi pada panduan umum karena kebutuhan penyakit dapat berbeda dari referensi populasi."
        )

    if req.stage == "mpasi":
        notes.append("Pastikan makanan matang, higienis, dan teksturnya sesuai kemampuan makan untuk mengurangi risiko tersedak.")
        if int(req.age_months or 6) < 12:
            notes.append("Untuk usia di bawah 12 bulan, jangan gunakan madu sebagai bahan makanan.")

    if req.stage == "toddler":
        notes.append("Potong dan siapkan makanan sesuai kemampuan mengunyah anak; hindari bentuk makanan yang mudah menyebabkan tersedak.")

    if req.stage == "elderly" and req.has_condition:
        notes.append("Kondisi kesehatan yang ditampilkan berasal dari input user dan digunakan sebagai konteks edukasi nutrisi; SEHATIN tidak menyimpulkan diagnosis.")
    if req.stage == "elderly" and req.chewing_difficulty:
        notes.append("Kesulitan mengunyah terdeteksi; contoh menu diarahkan ke pilihan yang lebih lunak.")
    if req.stage == "elderly" and req.swallowing_difficulty:
        notes.append(
            "Gangguan menelan dapat meningkatkan risiko tersedak/aspirasi. SEHATIN tidak menentukan kekentalan atau tekstur terapi; minta penilaian tenaga kesehatan."
        )

    return notes
