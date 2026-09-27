import re


def normalize_claim(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned[:5000]


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", text.lower()) if len(token) >= 3}


def token_relevance(claim: str, keywords: tuple[str, ...] | list[str]) -> float:
    """Deterministic lexical relevance; no generative model is used.

    Phrase hits receive full credit, while token overlap provides partial
    credit. The result is clamped to 0..1.
    """
    haystack = claim.lower()
    phrase_hits = sum(1 for keyword in keywords if keyword.lower() in haystack)
    keyword_tokens = _tokens(" ".join(keywords))
    claim_tokens = _tokens(claim)
    token_hits = len(keyword_tokens & claim_tokens)

    phrase_score = min(1.0, phrase_hits / 2) if keywords else 0.0
    token_score = min(1.0, token_hits / max(1, min(4, len(keyword_tokens))))
    return round(min(1.0, 0.7 * phrase_score + 0.3 * token_score), 4)


# Common health-claim concepts are grouped by the role they play in a
# relationship.  This is intentionally deterministic: an article must mention
# both sides of a causal/associative claim before it can influence the verdict.
_CONCEPT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Nutrition / daily habits
    ("late_eating", ("telat makan", "terlambat makan", "jarang sarapan", "melewatkan sarapan", "makan malam", "makan malam larut", "makan pada malam", "makan larut", "makan tengah malam", "makan malam hari", "makan sebelum tidur", "makan larut malam", "late eating", "late meal", "late evening meal", "meal timing", "dinner timing", "dinner", "night eating", "eating late", "last meal", "evening intake", "meals before bedtime", "eat before bed")),
    ("sugar", ("makanan manis", "minuman manis", "minuman berpemanis", "minuman bersoda", "soft drink", "soda", "teh manis", "kopi manis", "gula", "gula tambahan", "gula darah", "kemanisan", "pemanis", "added sugar", "sugar-sweetened", "sugar sweetened", "sweetened beverage", "sugary drink", "sweet drink", "soft drinks", "dietary sugar", "fruit juice")),
    ("salt", ("garam", "terlalu asin", "makanan asin", "natrium", "sodium", "salt intake", "high salt", "high sodium")),
    ("fat", ("lemak", "lemak jenuh", "lemak trans", "daging berlemak", "gorengan", "makanan berlemak", "saturated fat", "trans fat", "dietary fat", "fried food", "fatty food")),
    ("fiber", ("serat", "makanan berserat", "tinggi serat", "whole grain", "biji-bijian utuh", "fiber", "dietary fiber")),
    ("fruit_vegetable", ("buah", "sayur", "sayuran", "buah dan sayur", "vegetables", "fruit", "fruits", "vegetable")),
    ("healthy_diet", ("diet sehat", "pola makan sehat", "makan sehat", "gizi seimbang", "makanan sehat", "pola makan", "nutrisi", "gizi", "healthy diet", "healthy eating", "balanced diet", "nutrition", "nutrient")),
    ("vitamin_c", ("vitamin c", "vit c", "asam askorbat", "ascorbic acid", "vitamin c supplement")),
    ("sleep", ("kurang tidur", "tidur kurang", "tidur singkat", "kurang jam tidur", "tidur sedikit", "begadang", "sering begadang", "durasi tidur", "kualitas tidur", "sleep deprivation", "short sleep", "insufficient sleep", "sleep duration", "sleep quality", "sleep loss", "sleep restriction")),
    ("physical_activity", ("aktivitas fisik", "kurang gerak", "banyak duduk", "gaya hidup sedentari", "sedentari", "olahraga", "berolahraga", "latihan", "exercise", "physical activity", "physical inactivity", "sedentary", "sedentary lifestyle", "active lifestyle", "bergerak")),

    # Metabolic / cardiovascular topics
    ("obesity", ("gendut", "gemuk", "kegemukan", "obesitas", "berat badan", "berat badan naik", "berat badan bertambah", "kelebihan berat badan", "overweight", "obesity", "weight gain", "weight", "body weight", "body mass index", "bmi", "indeks massa tubuh", "lingkar pinggang", "abdominal obesity")),
    ("diabetes", ("diabetes", "kencing manis", "gula darah tinggi", "gula darah", "diabetes tipe 2", "diabetes melitus", "diabetes mellitus", "type 2 diabetes", "type 2 diabetes mellitus", "t2d", "blood glucose", "blood sugar", "insulin", "glucose")),
    ("cholesterol", ("kolesterol", "kolesterol tinggi", "ldl", "hdl", "trigliserida", "dislipidemia", "dyslipidemia", "lipid darah", "lemak darah", "blood lipids", "triglycerides", "cholesterol")),
    ("hypertension", ("hipertensi", "tekanan darah tinggi", "tekanan darah", "darah tinggi", "blood pressure", "high blood pressure", "hypertension", "sodium", "stroke")),
    ("cardiovascular", ("jantung", "penyakit jantung", "kardiovaskular", "kardiovaskuler", "serangan jantung", "jantung koroner", "cardiovascular", "heart disease", "heart attack", "coronary heart disease", "stroke")),
    ("stroke", ("stroke", "serangan stroke", "stroke ringan", "stroke berat")),

    # Digestive topics
    ("reflux", ("asam lambung", "asam lambung naik", "maag", "gastroesophageal reflux", "gerd", "refluks", "reflux", "acid reflux", "heartburn", "nyeri ulu hati", "rasa panas di dada", "reflux symptoms", "dyspepsia")),
    ("lactose", ("laktosa", "intoleransi laktosa", "tidak tahan susu", "sensitif susu", "susu", "milk", "lactose", "lactose intolerance")),
    ("diarrhea", ("diare", "mencret", "buang air besar cair", "berak cair", "diarrhea", "loose stool", "watery stool")),
    ("constipation", ("sembelit", "susah buang air besar", "susah bab", "jarang bab", "konstipasi", "constipation", "constipated")),
    ("dehydration", ("dehidrasi", "kurang cairan", "kekurangan cairan", "kurang minum", "jarang minum", "tidak cukup minum", "dehydration", "dehydrated", "fluid loss")),
    ("nausea", ("mual", "muntah", "ingin muntah", "nausea", "vomiting", "vomit")),
    ("abdominal_pain", ("sakit perut", "nyeri perut", "perut sakit", "nyeri abdomen", "abdominal pain", "stomach pain", "belly pain")),
    ("gas_bloating", ("kembung", "perut kembung", "banyak gas", "buang angin", "gas", "bloating", "flatulence")),

    # Infection / respiratory / communicable disease
    ("common_cold", ("pilek", "flu biasa", "masuk angin", "selesma", "common cold", "cold")),
    ("influenza", ("influenza", "flu", "flu musiman", "flu burung", "influenza virus", "virus influenza", "avian influenza")),
    ("antibiotics", ("antibiotik", "antibiotika", "obat antibiotik", "antibiotics", "antibiotic")),
    ("infection", ("infeksi", "terinfeksi", "kuman", "bakteri", "virus", "jamur", "infection", "infected", "bacterial infection", "viral infection", "fungal infection")),
    ("food_safety", ("keamanan pangan", "keracunan makanan", "makanan basi", "makanan terkontaminasi", "kontaminasi makanan", "food safety", "food poisoning", "foodborne", "contamination")),
    ("raw_chicken", ("ayam mentah", "daging ayam mentah", "cuci ayam", "mencuci ayam", "membilas ayam", "raw chicken", "washing chicken")),
    ("dengue", ("dbd", "demam berdarah", "demam dengue", "dengue", "nyamuk aedes", "aedes", "gigitan nyamuk")),
    ("tuberculosis", ("tbc", "tb", "tuberkulosis", "tuberculosis", "batuk lama", "batuk lebih dari 2 minggu", "mycobacterium")),
    ("malaria", ("malaria", "plasmodium", "gigitan nyamuk malaria")),
    ("pneumonia", ("pneumonia", "radang paru", "infeksi paru", "paru-paru", "batuk", "sesak napas", "pneumonia", "respiratory infection")),

    # Wounds / first aid
    ("wound_moisture", ("terkena air", "kena air", "terkena hujan", "luka basah", "basah terus", "luka lembap", "luka lembab", "air terus", "terendam", "direndam", "wet wound", "wet", "moist", "moisture", "water exposure", "water", "soaking", "soaked", "soggy", "excessive moisture", "damp", "dampness", "clean and dry", "keeping dry")),
    ("wound", ("luka", "luka terbuka", "luka sayat", "luka gores", "sayatan", "jahitan", "bekas operasi", "luka operasi", "wound", "cuts", "grazes", "incision", "surgical wound", "wound care")),
    ("wound_infection", ("bernanah", "nanah", "pus", "cairan kuning", "cairan hijau", "luka infeksi", "infeksi luka", "luka terinfeksi", "wound infection", "infected wound", "infection", "abscess", "purulent")),
    ("burn", ("luka bakar", "terbakar", "kena panas", "tersiram air panas", "air panas", "melepuh", "lepuh", "burn", "burns", "scald", "scalds", "blister")),
    ("nosebleed", ("mimisan", "hidung berdarah", "darah dari hidung", "nosebleed", "epistaxis")),
    ("hiccups", ("cegukan", "ceguk", "hiccups", "hiccup")),

    # Skin / oral health
    ("acne", ("jerawat", "bruntusan", "komedo", "acne", "pimples", "breakouts")),
    ("oral_health", ("gigi", "sakit gigi", "gigi berlubang", "karies", "gusi", "gusi berdarah", "bau mulut", "mulut", "oral health", "cavities", "tooth decay", "gingivitis", "gum disease", "toothache", "bad breath")),

    # Mental health
    ("mental_health", ("kesehatan mental", "kesehatan jiwa", "mental", "depresi", "cemas", "kecemasan", "anxiety", "stress", "stres", "depression", "gangguan jiwa", "psychological", "mental health")),

    # Immunization / maternal / child
    ("vaccines", ("vaksin", "vaksinasi", "imunisasi", "imunisasi dasar", "campak", "rubella", "polio", "vaccine", "vaccines", "vaccination", "immunization", "mmr")),
    ("child_health", ("anak", "balita", "bayi", "tumbuh kembang", "pertumbuhan", "perkembangan anak", "anak kecil", "child", "children", "child health", "growth", "development")),
    ("breastfeeding", ("asi", "asi eksklusif", "menyusui", "air susu ibu", "breastfeeding", "breast milk", "exclusive breastfeeding", "infant feeding")),
    ("complementary_feeding", ("mpasi", "makanan pendamping asi", "makanan pendamping", "bayi 6 bulan", "6 bulan", "usia 6 bulan", "anak 6-23 bulan", "complementary feeding")),
    ("pregnancy", ("hamil", "kehamilan", "ibu hamil", "kehamilan trimester", "trimester", "antenatal", "pregnancy", "pregnant", "maternal", "persalinan")),

    # Common symptoms and everyday health topics
    ("fever", ("demam", "demam tinggi", "badan panas", "suhu tubuh naik", "fever", "high fever", "temperature")),
    ("headache", ("sakit kepala", "pusing", "kepala pusing", "nyeri kepala", "headache", "migraine", "migrain")),
    ("sore_throat", ("sakit tenggorokan", "radang tenggorokan", "tenggorokan sakit", "nyeri tenggorokan", "sore throat", "pharyngitis", "tonsillitis")),
    ("cough", ("batuk", "batuk kering", "batuk berdahak", "batuk berdarah", "cough", "dry cough", "productive cough")),
    ("runny_nose", ("hidung tersumbat", "hidung mampet", "pilek", "hidung berair", "bersin", "runny nose", "stuffy nose", "nasal congestion", "sneezing")),
    ("shortness_of_breath", ("sesak napas", "sulit bernapas", "susah bernapas", "napas pendek", "sesak", "shortness of breath", "difficulty breathing", "dyspnea")),
    ("chest_pain", ("nyeri dada", "sakit dada", "dada terasa sakit", "chest pain", "chest discomfort")),
    ("back_pain", ("nyeri punggung", "sakit punggung", "pinggang sakit", "low back pain", "back pain", "lumbar pain")),
    ("joint_pain", ("nyeri sendi", "sakit sendi", "sendi sakit", "radang sendi", "joint pain", "arthritis", "arthralgia")),
    ("muscle_pain", ("nyeri otot", "sakit otot", "pegal", "myalgia", "muscle pain", "muscle ache")),
    ("allergy", ("alergi", "reaksi alergi", "alergi makanan", "alergi obat", "allergy", "allergic reaction", "food allergy", "drug allergy")),
    ("asthma", ("asma", "serangan asma", "mengi", "bengek", "wheezing", "asthma", "asthma attack")),
    ("copd", ("ppok", "penyakit paru obstruktif kronis", "copd", "chronic obstructive pulmonary disease")),
    ("gastritis", ("gastritis", "radang lambung", "lambung", "sakit lambung", "gastritis", "stomach inflammation")),
    ("ulcer", ("tukak lambung", "ulkus lambung", "maag kronis", "peptic ulcer", "gastric ulcer", "duodenal ulcer")),
    ("uti", ("infeksi saluran kemih", "anyang-anyangan", "anyang anyangan", "kencing sakit", "nyeri saat buang air kecil", "uti", "urinary tract infection", "cystitis")),
    ("kidney_stones", ("batu ginjal", "batu saluran kemih", "kidney stone", "kidney stones", "urolithiasis")),
    ("kidney_health", ("ginjal", "penyakit ginjal", "gagal ginjal", "chronic kidney disease", "kidney disease", "kidney failure", "ckd")),
    ("liver_health", ("hati", "penyakit hati", "fungsi hati", "gagal hati", "liver disease", "liver health", "liver failure")),
    ("thyroid", ("tiroid", "hipotiroid", "hipertiroid", "kelenjar tiroid", "thyroid", "hypothyroidism", "hyperthyroidism")),
    ("anemia", ("anemia", "kurang darah", "hemoglobin rendah", "zat besi rendah", "iron deficiency", "iron deficiency anemia", "low hemoglobin")),
    ("osteoporosis", ("osteoporosis", "tulang keropos", "kepadatan tulang", "bone density", "osteoporosis", "bone loss")),
    ("menstrual_health", ("menstruasi", "haid", "nyeri haid", "haid tidak teratur", "menstrual", "menstruation", "period pain", "dysmenorrhea", "irregular periods")),
    ("pcos", ("pcos", "sindrom ovarium polikistik", "polycystic ovary syndrome", "polycystic ovary")),
    ("pregnancy_nausea", ("mual saat hamil", "muntah saat hamil", "morning sickness", "nausea in pregnancy", "hyperemesis")),
    ("diaper_rash", ("ruam popok", "iritasi popok", "diaper rash", "nappy rash")),
    ("eczema", ("eksim", "dermatitis atopik", "dermatitis", "eczema", "atopic dermatitis")),
    ("psoriasis", ("psoriasis", "psoriasis kulit")),
    ("fungal_skin", ("jamur kulit", "kurap", "panu", "kutu air", "tinea", "ringworm", "athlete's foot", "fungal skin infection")),
    ("conjunctivitis", ("mata merah", "konjungtivitis", "belekan", "conjunctivitis", "pink eye")),
    ("ear_infection", ("infeksi telinga", "sakit telinga", "telinga sakit", "otitis", "ear infection", "earache")),
    ("sinusitis", ("sinusitis", "radang sinus", "infeksi sinus", "sinus infection")),
    ("constipation" , ("sembelit", "susah buang air besar", "susah bab", "jarang bab", "konstipasi", "constipation", "constipated")),
    ("vomiting", ("muntah", "muntah terus", "muntah berulang", "vomiting", "repeated vomiting")),
    ("food_allergy", ("alergi makanan", "food allergy", "peanut allergy", "milk allergy", "egg allergy")),
    ("food_intolerance", ("intoleransi makanan", "tidak cocok makanan", "food intolerance", "food sensitivity")),
    ("dehydration_signs", ("mulut kering", "haus berlebihan", "urin sedikit", "air kencing sedikit", "dark urine", "dry mouth", "excessive thirst", "dehydration signs")),
    ("sleep_quality", ("insomnia", "susah tidur", "sulit tidur", "tidak bisa tidur", "gangguan tidur", "insomnia", "sleep disorder", "difficulty sleeping")),
    ("stress", ("stres", "stress", "tekanan psikologis", "beban pikiran", "stres berat", "psychological stress")),
    ("anxiety", ("cemas", "kecemasan", "serangan panik", "panic attack", "anxiety", "anxiety disorder")),
    ("depression", ("depresi", "depression", "gangguan depresi", "major depressive disorder")),
    ("first_aid", ("pertolongan pertama", "pertolongan darurat", "first aid", "emergency first aid")),
    ("pain", ("sakit", "nyeri", "rasa sakit", "pain", "ache", "painful")),
    ("feeling_dizzy", ("pusing", "berkunang-kunang", "kepala terasa ringan", "dizziness", "lightheadedness", "vertigo")),
    ("fainting", ("pingsan", "hilang kesadaran", "sinkop", "fainting", "syncope")),
    ("palpitations", ("jantung berdebar", "berdebar", "palpitasi", "palpitation", "heart palpitations")),
    ("edema", ("bengkak kaki", "kaki bengkak", "pembengkakan", "edema", "swelling")),

    # Cancer and cancer risk factors
    ("cancer", (
        "kanker", "tumor", "tumor ganas", "keganasan", "neoplasma",
        "cancer", "cancers", "malignancy", "malignant", "malignant tumor",
        "cancer prevention", "cancer risk", "risiko kanker", "penyebab kanker",
        "cancer cause", "causes cancer", "carcinogenic", "karsinogen",
        "karsinogenik", "carcinogen", "oncogenic", "onkogenik",
        "kanker paru", "kanker payudara", "kanker usus besar", "kanker kolorektal",
        "kanker serviks", "kanker leher rahim", "kanker hati", "kanker lambung",
        "kanker kerongkongan", "kanker esofagus", "kanker ginjal", "kanker kandung kemih",
        "kanker kulit", "kanker prostat", "kanker endometrium", "kanker ovarium",
        "lung cancer", "breast cancer", "colorectal cancer", "colon cancer",
        "cervical cancer", "liver cancer", "stomach cancer", "gastric cancer",
        "esophageal cancer", "oesophageal cancer", "kidney cancer", "bladder cancer",
        "skin cancer", "prostate cancer", "endometrial cancer", "ovarian cancer",
        "melanoma", "mesothelioma", "leukemia", "leukaemia", "lymphoma",
    )),
    ("smoking", (
        "rokok", "merokok", "perokok", "asap rokok", "nikotin", "tembakau",
        "rokok kretek", "rokok putih", "rokok elektrik", "vape", "vaping",
        "tobacco", "smoking", "smoker", "nicotine", "secondhand smoke",
        "passive smoking", "perokok pasif", "asap tembakau", "tobacco smoke",
        "smokeless tobacco", "chewing tobacco", "tembakau tanpa asap",
    )),
    ("alcohol", (
        "alkohol", "minuman beralkohol", "minuman keras", "miras", "bir", "wine",
        "anggur alkohol", "spirit", "liquor", "beer", "alcohol", "alcohol consumption",
        "alcohol use", "drinking alcohol", "heavy drinking", "alcoholic beverage",
    )),
    ("uv_radiation", (
        "sinar uv", "sinar ultraviolet", "radiasi ultraviolet", "paparan uv",
        "paparan matahari", "sinar matahari", "terlalu banyak matahari", "sunburn",
        "terbakar matahari", "tanning", "sun tanning", "tanning bed", "solarium",
        "ultraviolet", "uv radiation", "ultraviolet radiation", "sunlight", "solar radiation",
        "uv exposure", "artificial tanning",
    )),
    ("ionizing_radiation", (
        "radiasi ionisasi", "radiasi pengion", "paparan radiasi", "radiasi medis",
        "radiasi nuklir", "sinar x", "x-ray", "rontgen", "radiasi gamma",
        "radiasi ionizing", "ionizing radiation", "ionising radiation", "gamma radiation",
        "nuclear radiation", "radiation exposure", "radiation therapy", "radiasi pengionisasi",
    )),
    ("air_pollution", (
        "polusi udara", "pencemaran udara", "udara tercemar", "asap kendaraan",
        "asap knalpot", "partikulat", "partikel halus", "pm2.5", "pm10",
        "polusi dalam ruangan", "asap pembakaran", "asap dapur", "air pollution",
        "outdoor air pollution", "indoor air pollution", "particulate matter", "fine particles",
        "diesel exhaust", "vehicle exhaust", "airborne pollution",
    )),
    ("occupational_carcinogen", (
        "asbes", "paparan asbes", "debu asbes", "bensin", "benzena", "vinil klorida",
        "arsenik", "paparan arsenik", "formaldehida", "silika", "debu silika",
        "kromium", "nikel", "radon", "paparan kerja", "paparan di tempat kerja",
        "bahan kimia di tempat kerja", "occupational exposure", "occupational carcinogen",
        "asbestos", "benzene", "vinyl chloride", "arsenic", "formaldehyde", "silica",
        "chromium", "nickel", "radon", "workplace exposure", "occupational exposure",
    )),
    ("diet_cancer_risk", (
        "daging olahan", "daging proses", "daging merah", "makanan ultra proses",
        "makanan ultra-proses", "ultra processed food", "processed meat", "red meat",
        "processed foods", "diet tinggi kalori", "pola makan tidak sehat", "diet tidak sehat",
        "poor diet", "unhealthy diet", "low fruit and vegetable", "kurang buah dan sayur",
        "asupan buah dan sayur rendah", "dietary risk", "dietary factors", "diet factor",
        "aflatoksin", "aflatoxin",
    )),
    ("cancer_infection", (
        "hpv", "human papillomavirus", "virus papiloma manusia", "papillomavirus",
        "hepatitis b", "hepatitis c", "hbv", "hcv", "ebv", "epstein-barr",
        "virus epstein barr", "helicobacter pylori", "h. pylori", "h pylori",
        "htlv-1", "human t-cell leukemia virus", "kaposi sarcoma", "schistosoma",
        "schistosomiasis", "cancer-causing infection", "cancer causing infection",
        "infeksi penyebab kanker", "infeksi karsinogenik", "oncogenic infection",
    )),
    ("genetic_hereditary", (
        "riwayat keluarga kanker", "riwayat kanker dalam keluarga", "keluarga dengan kanker", "ada anggota keluarga dengan kanker",
        "keturunan kanker", "faktor keturunan", "keturunan", "genetik", "mutasi gen", "mutasi dna", "dna", "gen",
        "gen kanker", "gen yang diwariskan", "mutasi bawaan", "sindrom kanker herediter",
        "hereditary cancer", "family history of cancer", "family history", "genetic predisposition", "genetic mutation", "inherited mutation",
        "inherited gene", "germline mutation", "brca1", "brca2", "lynch syndrome",
    )),
    ("chronic_inflammation", (
        "peradangan kronis", "inflamasi kronis", "radang kronis", "chronic inflammation",
        "chronic inflammatory", "inflammation", "inflammatory disease", "radang menahun",
    )),
    ("immunosuppression", (
        "imunosupresi", "imunosupresif", "sistem imun lemah", "kekebalan tubuh lemah",
        "immunosuppression", "immunosuppressive", "immunocompromised", "weakened immune system",
        "organ transplant", "transplant recipient", "obat imunosupresif",
    )),
    ("hormones", (
        "hormon", "terapi hormon", "terapi pengganti hormon", "hormone therapy",
        "hormone replacement therapy", "estrogen", "estrogen exposure", "hormonal",
    )),
    ("physical_inactivity_cancer", (
        "kurang aktivitas fisik", "kurang olahraga", "jarang olahraga", "tidak aktif secara fisik",
        "physical inactivity", "physical inactivity cancer", "inactive lifestyle", "sedentary lifestyle",
    )),
    ("ageing", ("lansia", "lanjut usia", "orang lanjut usia", "orang tua", "usia lanjut", "usia tua", "semakin tua", "bertambahnya usia", "ageing", "aging", "older adults", "elderly", "usia bertambah", "bertambah usia", "older age")),
)


def concept_groups(text: str) -> dict[str, set[str]]:
    lowered = text.lower()
    found: dict[str, set[str]] = {}
    for name, aliases in _CONCEPT_GROUPS:
        raw_hits = {alias for alias in aliases if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", lowered)}
        # Prefer the most specific phrase. For example, "luka bakar" should
        # activate the burn concept, not also activate the generic wound
        # concept merely because the word "luka" appears inside the phrase.
        hits = {
            alias
            for alias in raw_hits
            if not any(alias != other and alias in other and len(other) > len(alias) for other in raw_hits)
        }
        if hits:
            found[name] = hits
    # Remove generic groups that are fully subsumed by a more specific phrase
    # in another group (e.g. wound="luka" vs burn="luka bakar").
    for name, hits in list(found.items()):
        if any(
            other_name != name
            and any(h != other_h and h in other_h and len(other_h) > len(h) for other_h in other_hits for h in hits)
            for other_name, other_hits in found.items()
        ):
            found.pop(name, None)
    return found


def claim_evidence_relevance(claim: str, evidence_text: str) -> float:
    """Check whether evidence actually discusses the claim's concepts.

    For relationship claims, evidence must contain at least one concept from
    each side of the relationship. This prevents an article about a wound
    abscess from being treated as evidence for the separate claim that water
    exposure causes pus, merely because both mention wounds and infection.
    """
    claim_groups = concept_groups(claim)
    if not claim_groups:
        return 0.0
    evidence_groups = concept_groups(evidence_text)

    lowered_claim = claim.lower()
    relationship_cues = ("menyebabkan", "mengakibatkan", "membuat", "meningkatkan", "menurunkan", "mencegah", "mengurangi", "berisiko", "risk", "associated", "association", "causes", "cause", "prevents", "reduces", "increases")
    is_relationship = len(claim_groups) >= 2 or any(cue in lowered_claim for cue in relationship_cues)

    required_groups = set(claim_groups)
    # Generic context concepts such as "wound" should not become a third
    # required side of a relationship claim when the meaningful relationship
    # is exposure -> outcome (for example water/moisture -> wound infection).
    if is_relationship:
        required_groups.discard("wound")

    if is_relationship and len(required_groups) >= 2:
        matched = sum(1 for name in required_groups if name in evidence_groups)
        return round(matched / len(required_groups), 4)

    matched = sum(1 for name in required_groups if name in evidence_groups)
    return round(matched / max(1, len(required_groups)), 4)


def has_simple_negation(claim: str) -> bool:
    """Detect common Indonesian/English negation used in simple factual claims.

    This is deliberately conservative and only supports the demo corpus. A
    future semantic provider can replace it without changing TrustEngine.
    """
    lowered = claim.lower()
    patterns = (
        r"\btidak\b",
        r"\bbukan\b",
        r"\btak\b",
        r"\bnggak\b",
        r"\bga(k)?\b",
        r"\bdoes not\b",
        r"\bdo not\b",
        r"\bdoesn't\b",
        r"\bdon't\b",
        r"\bno link\b",
    )
    return any(re.search(pattern, lowered) for pattern in patterns)


def orient_stance(base_stance: str, claim: str) -> str:
    """Flip support/contradict for a plainly negated version of a demo claim."""
    if base_stance not in {"support", "contradict"} or not has_simple_negation(claim):
        return base_stance
    return "support" if base_stance == "contradict" else "contradict"
