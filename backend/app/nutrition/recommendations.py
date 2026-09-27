import re

from app.schemas.nutrition import NutritionRequest

from .calculator import mpasi_age_band
from .constants import STAGE_FOOD_GROUPS, STAGE_PRIORITY_NUTRIENTS
from .meal_templates import MEALS
from .rules import personalization_is_limited
from .elderly_condition_context import contextual_recommendations, contextual_sample_menu


def food_groups(req: NutritionRequest) -> list[str]:
    return list(STAGE_FOOD_GROUPS[req.stage])


def priority_nutrients(req: NutritionRequest) -> list[str]:
    return list(STAGE_PRIORITY_NUTRIENTS[req.stage])


def recommendations(req: NutritionRequest) -> list[str]:
    if req.stage == "mpasi":
        band = mpasi_age_band(int(req.age_months or 6))
        values = [
            "Responsif terhadap tanda lapar dan kenyang; ajak makan dengan sabar tanpa memaksa menghabiskan porsi.",
            "Usahakan keragaman makanan dari hari ke hari, terutama sumber protein hewani dan makanan kaya zat besi.",
        ]
        if band == "6-8":
            values.insert(0, "Fokus pada pengenalan makanan pendamping dengan tekstur lumat/kental dan tingkatkan tekstur bertahap.")
        elif band == "9-11":
            values.insert(0, "Tingkatkan ke tekstur lebih kasar/cincang halus dan berikan kesempatan belajar makan sendiri bila sudah mampu.")
        else:
            values.insert(0, "Arahkan bertahap ke makanan keluarga yang bergizi dengan potongan/tekstur aman untuk usia anak.")

        texture_label = {
            "smooth_mashed": "lumat/halus kental",
            "mashed_lumpy": "lumat lebih kasar/bertekstur",
            "finger_food": "finger food lunak",
            "family_soft": "makanan keluarga lunak",
        }.get(req.texture_level or "", "tekstur yang dipilih")
        values.append(f"Kemampuan tekstur yang dicatat saat ini: {texture_label}; peningkatan tekstur dilakukan bertahap sesuai kemampuan makan.")
        minimum_meals = 2 if band == "6-8" else 3
        if req.meal_frequency and req.meal_frequency < minimum_meals:
            values.append(
                f"Frekuensi yang dimasukkan ({req.meal_frequency} kali/hari) berada di bawah pola makan utama yang umumnya dianjurkan untuk tahap ini; tingkatkan bertahap sesuai toleransi dan sinyal lapar/kenyang."
            )
        if req.appetite == "low":
            values.append("Untuk nafsu makan rendah, gunakan porsi kecil namun padat gizi dan tetap responsif tanpa memaksa.")

        if req.feeding_mode == "breastmilk":
            values.append("Lanjutkan ASI sesuai kebutuhan anak bersamaan dengan makanan pendamping.")
        elif req.feeding_mode == "formula":
            values.append("Jumlah makanan pendamping perlu mempertimbangkan volume formula yang benar-benar dikonsumsi; jangan mengejar angka kalori secara kaku.")
        else:
            values.append("Karena anak mendapat ASI dan formula, kebutuhan dari makanan pendamping tidak dihitung sebagai satu angka pasti.")
        return values

    if req.stage == "toddler":
        values = [
            "Tawarkan makanan beragam berulang kali; penolakan satu kali tidak berarti makanan harus dihapus permanen.",
            "Gunakan jadwal makan yang cukup konsisten dan hindari kebiasaan ngemil terus-menerus sepanjang hari.",
            "Utamakan air putih dan batasi makanan/minuman tinggi gula, garam, serta sangat diproses.",
            "Pantau pertumbuhan melalui layanan kesehatan rutin; SEHATIN tidak menilai status gizi hanya dari satu angka berat badan.",
        ]
        if req.meal_frequency and req.meal_frequency < 3:
            values.append("Frekuensi makan yang dimasukkan cukup rendah; pertimbangkan membangun jadwal makan utama yang lebih teratur.")
        if req.appetite == "low":
            values.append("Untuk nafsu makan rendah, prioritaskan makanan padat gizi dalam porsi kecil dan hindari minuman berkalori menjelang waktu makan.")
        return values

    values = [
        "Sebarkan sumber protein pada beberapa waktu makan untuk membantu mempertahankan fungsi dan massa otot.",
        "Pilih makanan beragam dan padat gizi; sesuaikan porsi dengan nafsu makan dan kemampuan makan.",
        "Minum secara teratur sepanjang hari kecuali dokter memberikan pembatasan cairan.",
    ]
    if req.activity_level == "low":
        values.append("Aktivitas rendah dicatat sebagai konteks; kebutuhan energi aktual dapat lebih rendah dari angka referensi populasi.")
    elif req.activity_level == "high":
        values.append("Aktivitas lebih tinggi dicatat sebagai konteks; kebutuhan energi aktual dapat berbeda dari angka referensi populasi.")
    if req.chewing_difficulty:
        values.append("Pilih sumber protein dan sayur yang dimasak lunak agar lebih mudah dikunyah tanpa hanya mengandalkan makanan cair.")
    if personalization_is_limited(req):
        values.append("Karena ada faktor medis/keamanan, rekomendasi sengaja dibatasi agar tidak berubah menjadi terapi diet individual.")
    return contextual_recommendations(req, values)


def _tokens(values: list[str]) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.update(re.findall(r"[a-z0-9]+", value.lower()))
    return result


def _restriction_blocks(tags: set[str], restrictions: set[str]) -> bool:
    text = " ".join(restrictions)
    if "vegan" in text and ("animal" in tags or "dairy" in tags):
        return True
    if "vegetarian" in text and "animal" in tags:
        return True
    if ("seafood" in text or "ikan" in text) and "seafood" in tags:
        return True
    return False


def sample_menu(req: NutritionRequest) -> list[str]:
    allergens = _tokens(req.allergies)
    restrictions = _tokens(req.dietary_restrictions)

    if req.stage == "mpasi":
        stage_key = "mpasi"
        band = mpasi_age_band(int(req.age_months or 6))
    elif req.stage == "toddler":
        stage_key = "toddler"
        band = "24-59" if int(req.age_months or 24) <= 47 else "24-59"
    else:
        if req.swallowing_difficulty:
            stage_key = "elderly_swallowing"
        else:
            stage_key = "elderly_soft" if req.chewing_difficulty else "elderly"
        band = "standard"

    selected: list[str] = []
    for item in MEALS:
        if item["stage"] != stage_key or band not in item["bands"]:
            continue
        if allergens.intersection(item["allergens"]):
            continue
        if _restriction_blocks(item["tags"], restrictions):
            continue
        selected.append(item["text"])

    if selected:
        menus = selected[:4]
        return contextual_sample_menu(req, menus) if req.stage == "elderly" else menus
    return [
        "Tidak ada contoh menu bawaan yang lolos seluruh filter alergi/batasan. Gunakan kombinasi bahan yang sudah diketahui aman dan sesuai batasan makanan."
    ]
