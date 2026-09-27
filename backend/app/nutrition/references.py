"""Internal evidence/reference layer for the Nutrition Engine.

This module is intentionally NOT serialized to the public nutrition API. It is
used to keep numerical references and rule provenance auditable in code while
keeping the user-facing result focused on practical guidance.

Primary references verified for this revision:
- Indonesia Ministry of Health, Permenkes No. 28/2019 (AKG)
  https://jdih.kemkes.go.id/storage/documents/pdfs/2019permenkes028.pdf
- WHO Guideline for complementary feeding of infants and young children 6-23 months (2023)
  https://www.who.int/publications/i/item/9789240081864
- WHO Complementary feeding / Infant and young child feeding
  https://www.who.int/health-topics/complementary-feeding
- ESPEN practical guideline: Clinical nutrition and hydration in geriatrics (2022)
  https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_guideline_Clinical_nutrition_and_hydration_in_geriatrics.pdf
- WHO Healthy diet (updated 2026)
  https://www.who.int/news-room/fact-sheets/detail/healthy-diet
- Kementerian Kesehatan RI — Isi Piringku
  https://ayosehat.kemkes.go.id/isi-piringku-kebutuhan-gizi-harian-seimbang
- IDDSI Framework Documents
  https://www.iddsi.org/resources/framework-documents
- CDC Infant and Toddler Nutrition: foods and drinks to avoid or limit (honey <12 months)
  https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/foods-and-drinks-to-avoid-or-limit.html

These are reference values for healthy populations / educational guidance, not
individual medical prescriptions.
"""


REFERENCE_PROVENANCE = {
    "akg_indonesia_2019": {
        "title": "Permenkes No. 28 Tahun 2019 — Angka Kecukupan Gizi yang Dianjurkan untuk Masyarakat Indonesia",
        "publisher": "Kementerian Kesehatan Republik Indonesia",
        "url": "https://jdih.kemkes.go.id/storage/documents/pdfs/2019permenkes028.pdf",
        "use": "Referensi energi, protein, lemak, karbohidrat, serat, dan air menurut kelompok usia/jenis kelamin.",
    },
    "who_complementary_feeding_2023": {
        "title": "WHO Guideline for complementary feeding of infants and young children 6-23 months of age",
        "publisher": "World Health Organization",
        "url": "https://www.who.int/publications/i/item/9789240081864",
        "use": "Usia mulai MPASI, keragaman, responsive feeding, dan prinsip complementary feeding.",
    },
    "who_complementary_feeding_practical": {
        "title": "Complementary feeding",
        "publisher": "World Health Organization",
        "url": "https://www.who.int/health-topics/complementary-feeding",
        "use": "Frekuensi makan, perkembangan tekstur, dan porsi praktis menurut usia.",
    },
    "espen_geriatrics_2022": {
        "title": "ESPEN practical guideline: Clinical nutrition and hydration in geriatrics",
        "publisher": "ESPEN",
        "url": "https://www.espen.org/files/ESPEN-Guidelines/ESPEN_practical_guideline_Clinical_nutrition_and_hydration_in_geriatrics.pdf",
        "use": "Orientasi nutrisi/hidrasi geriatrik dan prinsip individualisasi pada lansia.",
    },
    "who_healthy_diet_2026": {
        "title": "Healthy diet",
        "publisher": "World Health Organization",
        "url": "https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        "use": "Prinsip adequacy, balance, moderation, diversity serta pola makan berbasis pangan bergizi/minim proses.",
    },
    "kemenkes_isi_piringku": {
        "title": "Isi Piringku — Panduan Kebutuhan Gizi Seimbang Harian",
        "publisher": "Kementerian Kesehatan Republik Indonesia",
        "url": "https://ayosehat.kemkes.go.id/isi-piringku-kebutuhan-gizi-harian-seimbang",
        "use": "Komposisi makan praktis Indonesia: makanan pokok, lauk berprotein, sayur, dan buah serta pembatasan gula/garam/lemak.",
    },
    "iddsi_framework": {
        "title": "IDDSI Framework and Detailed Level Definitions",
        "publisher": "International Dysphagia Diet Standardisation Initiative",
        "url": "https://www.iddsi.org/resources/framework-documents",
        "use": "Standar terminologi tekstur makanan/kekentalan minuman; aplikasi tidak menetapkan level tekstur tanpa penilaian yang sesuai.",
    },
    "who_iycf_indicators_2021": {
        "title": "Indicators for assessing infant and young child feeding practices: definitions and measurement methods (2021)",
        "publisher": "World Health Organization / UNICEF",
        "url": "https://www.who.int/publications/i/item/9789240018389",
        "use": "Kerangka pengukuran praktik makan anak dan indikator minimum dietary diversity/meal frequency.",
    },
    "kemenkes_mpasi_monitoring_2024": {
        "title": "Petunjuk Teknis Pemantauan Praktik MP-ASI Anak Usia 6–23 Bulan (2024)",
        "publisher": "Kementerian Kesehatan Republik Indonesia",
        "url": "https://www.kemkes.go.id/id/pemberian-mpasi-harus-penuhi-4-syarat-ini",
        "use": "Pemantauan praktik MPASI Indonesia: tepat waktu, adekuat, aman, dan cara pemberian yang benar.",
    },
    "toddler_vegetable_exposure_review": {
        "title": "A Systematic Review of Methods for Increasing Vegetable Consumption in Early Childhood",
        "publisher": "PubMed indexed review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/28596931/",
        "use": "Repeated exposure strategies for children 2–5 years.",
    },
    "toddler_ssb_review": {
        "title": "A systematic review of strategies to reduce sugar-sweetened beverage consumption among 0-year to 5-year olds",
        "publisher": "PubMed indexed systematic review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30019442/",
        "use": "Behavioral and environmental strategies for reducing SSB exposure in young children.",
    },
    "caregiver_feeding_review": {
        "title": "Systematic review/meta-analysis of caregiver feeding practices and interventions in young children",
        "publisher": "PubMed indexed review",
        "url": "https://pubmed.ncbi.nlm.nih.gov/30982865/",
        "use": "Caregiver feeding behavior, including responsive feeding/pressure-related practices, as a program-monitoring context.",
    },
    "cdc_infant_food_safety_2026": {
        "title": "Foods and Drinks to Avoid or Limit — Infant and Toddler Nutrition",
        "publisher": "CDC",
        "url": "https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/foods-and-drinks-to-avoid-or-limit.html",
        "use": "Keamanan madu sebelum usia 12 bulan.",
    },
}

# Indonesian AKG: energy kcal, protein g, fat g, carbohydrate g, fibre g, water mL.
CHILD_AKG = {
    "6-11_months": {
        "energy_kcal": 800,
        "protein_g": 15,
        "fat_g": 35,
        "carbohydrate_g": 105,
        "fiber_g": 11,
        "water_ml": 900,
    },
    "1-3_years": {
        "energy_kcal": 1350,
        "protein_g": 20,
        "fat_g": 45,
        "carbohydrate_g": 215,
        "fiber_g": 19,
        "water_ml": 1150,
    },
    "4-6_years": {
        "energy_kcal": 1400,
        "protein_g": 25,
        "fat_g": 50,
        "carbohydrate_g": 220,
        "fiber_g": 20,
        "water_ml": 1450,
    },
}

# Indonesian AKG values for age bands used by the elderly module.
ELDERLY_AKG = {
    "male": {
        "60-64": {"energy_kcal": 2150, "protein_g": 65, "fat_g": 60, "carbohydrate_g": 340, "fiber_g": 30, "water_ml": 2500},
        "65-80": {"energy_kcal": 1800, "protein_g": 64, "fat_g": 50, "carbohydrate_g": 275, "fiber_g": 25, "water_ml": 1800},
        "81+": {"energy_kcal": 1600, "protein_g": 64, "fat_g": 45, "carbohydrate_g": 235, "fiber_g": 22, "water_ml": 1600},
    },
    "female": {
        "60-64": {"energy_kcal": 1800, "protein_g": 60, "fat_g": 50, "carbohydrate_g": 280, "fiber_g": 25, "water_ml": 2350},
        "65-80": {"energy_kcal": 1550, "protein_g": 58, "fat_g": 45, "carbohydrate_g": 230, "fiber_g": 22, "water_ml": 1550},
        "81+": {"energy_kcal": 1400, "protein_g": 58, "fat_g": 40, "carbohydrate_g": 200, "fiber_g": 20, "water_ml": 1400},
    },
}

# Expected energy from complementary foods for breastfed children. These are
# population guidance bands; milk intake and individual growth change the actual need.
MPASI_COMPLEMENTARY_ENERGY_KCAL = {
    "6-8": 200,
    "9-11": 300,
    "12-23": 550,
}

MPASI_PATTERN = {
    "6-8": {
        "meals": "2–3 kali makan/hari",
        "snacks": "Camilan belum wajib; ikuti rasa lapar dan kenyang bayi.",
        "texture": "Mulai dari lumat/kental; tingkatkan tekstur secara bertahap.",
        "portion": "Mulai beberapa sendok makan dan naikkan bertahap hingga sekitar 1/2 mangkuk 250 mL sesuai kemampuan.",
    },
    "9-11": {
        "meals": "3–4 kali makan/hari",
        "snacks": "1–2 camilan bergizi dapat diberikan sesuai nafsu makan.",
        "texture": "Lumat lebih kasar/cincang halus; finger food lunak dapat dikenalkan bila kemampuan makan siap.",
        "portion": "Sekitar 1/2 mangkuk 250 mL per makan sebagai panduan, mengikuti sinyal lapar/kenyang.",
    },
    "12-23": {
        "meals": "3–4 kali makan/hari",
        "snacks": "1–2 camilan bergizi sesuai kebutuhan dan nafsu makan.",
        "texture": "Makanan keluarga yang lunak/aman, dicincang atau dilumat bila masih diperlukan.",
        "portion": "Sekitar 3/4 hingga 1 mangkuk 250 mL per makan sebagai panduan, tidak dipaksakan.",
    },
}

# ESPEN general orientation for healthy older adults. Not used when the request
# contains medical conditions where a disease-specific target may be unsafe.
GERIATRIC_PROTEIN_MIN_G_PER_KG = 1.0



def public_reference_labels(req) -> list[str]:
    """Reference labels for API auditability; frontend may choose not to render them."""
    labels = ["Kementerian Kesehatan RI — AKG (Permenkes No. 28 Tahun 2019)"]
    if req.stage == "mpasi":
        labels.extend([
            "WHO — Guideline for complementary feeding of infants and young children 6–23 months (2023)",
            "WHO/UNICEF — IYCF Indicators (2021)",
            "Kementerian Kesehatan RI — Petunjuk Teknis Pemantauan Praktik MP-ASI 6–23 Bulan (2024)",
        ])
    if req.stage == "toddler":
        labels.extend([
            "PubMed — Systematic review repeated vegetable exposure in children 2–5 years",
            "PubMed — Systematic review reducing sugar-sweetened beverages in children 0–5 years",
            "WHO — Responsive feeding / complementary feeding principles",
        ])
    if req.stage == "elderly":
        labels.extend([
            "WHO — Healthy Diet (adequacy, balance, moderation, diversity)",
            "Kementerian Kesehatan RI — Isi Piringku / Pedoman Gizi Seimbang",
            "ESPEN — Clinical nutrition and hydration in geriatrics (2022)",
        ])
        if getattr(req, "swallowing_difficulty", False):
            labels.append("IDDSI — Framework for food texture and drink thickness terminology")
    return labels
