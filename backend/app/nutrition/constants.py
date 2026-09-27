"""General nutrition rule constants used by the deterministic engine."""

MEDICAL_CONTEXT_TERMS = {
    "diabetes",
    "ginjal",
    "gagal ginjal",
    "ckd",
    "hipertensi",
    "darah tinggi",
    "jantung",
    "gagal jantung",
    "stroke",
    "kanker",
    "alergi berat",
    "gangguan menelan",
    "disfagia",
    "celiac",
    "penyakit hati",
    "sirosis",
    "dialisis",
}

STAGE_FOOD_GROUPS = {
    "mpasi": [
        "Makanan pokok/sumber energi",
        "Protein hewani",
        "Kacang-kacangan atau sumber protein nabati yang sesuai",
        "Sayur dan buah beragam",
        "Lemak dari bahan makanan/minyak dalam jumlah wajar",
    ],
    "toddler": [
        "Makanan pokok",
        "Protein hewani dan/atau nabati",
        "Sayur",
        "Buah",
        "Susu atau alternatif yang sesuai bila dikonsumsi",
        "Lemak sehat dari pola makan beragam",
    ],
    "elderly": [
        "Protein berkualitas pada waktu makan",
        "Sayur dan buah",
        "Makanan pokok/karbohidrat",
        "Kacang-kacangan bila sesuai",
        "Cairan yang cukup",
    ],
}

STAGE_PRIORITY_NUTRIENTS = {
    "mpasi": ["Protein", "Zat besi", "Zinc", "Lemak", "Vitamin dan mineral dari makanan beragam"],
    "toddler": ["Protein", "Zat besi", "Kalsium", "Serat", "Vitamin dan mineral dari makanan beragam"],
    "elderly": ["Protein", "Cairan", "Serat", "Kalsium", "Vitamin D dan mikronutrien dari makanan beragam"],
}
