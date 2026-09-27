"""Curated meal examples used by the educational recommendation engine.

The engine deliberately avoids claiming precise nutrient totals for these meals
until a full, versioned food-composition database (e.g. TKPI) is integrated.
"""

MEALS = [
    # MPASI 6-8 months
    {"stage": "mpasi", "bands": {"6-8"}, "text": "Bubur nasi kental + ayam matang yang dilumat + labu + sedikit minyak", "allergens": set(), "tags": {"animal", "soft"}},
    {"stage": "mpasi", "bands": {"6-8"}, "text": "Kentang lumat + ikan matang tanpa duri yang dilumat + wortel", "allergens": {"ikan", "seafood"}, "tags": {"animal", "soft", "seafood"}},
    {"stage": "mpasi", "bands": {"6-8"}, "text": "Bubur beras + telur matang yang dilumat + bayam + sedikit minyak", "allergens": {"telur", "egg"}, "tags": {"animal", "soft"}},
    # MPASI 9-11 months
    {"stage": "mpasi", "bands": {"9-11"}, "text": "Nasi tim lembut + daging sapi cincang halus + wortel", "allergens": set(), "tags": {"animal", "soft"}},
    {"stage": "mpasi", "bands": {"9-11"}, "text": "Kentang lumat kasar + ikan matang tanpa duri + brokoli lunak", "allergens": {"ikan", "seafood"}, "tags": {"animal", "soft", "seafood"}},
    {"stage": "mpasi", "bands": {"9-11"}, "text": "Nasi tim + ayam cincang halus + tahu + labu", "allergens": {"kedelai", "soy"}, "tags": {"animal", "soft"}},
    # MPASI 12-23 months
    {"stage": "mpasi", "bands": {"12-23"}, "text": "Nasi lembut + ayam suwir kecil + tumis sayur lunak + buah lunak", "allergens": set(), "tags": {"animal", "family"}},
    {"stage": "mpasi", "bands": {"12-23"}, "text": "Nasi + ikan matang tanpa duri + tahu + sayur bening", "allergens": {"ikan", "seafood", "kedelai", "soy"}, "tags": {"animal", "family", "seafood"}},
    {"stage": "mpasi", "bands": {"12-23"}, "text": "Nasi + telur matang + tempe + sayur lunak", "allergens": {"telur", "egg", "kedelai", "soy"}, "tags": {"family"}},
    # Toddler
    {"stage": "toddler", "bands": {"24-59"}, "text": "Sarapan: nasi + telur matang + sayur; buah sebagai pendamping", "allergens": {"telur", "egg"}, "tags": {"animal"}},
    {"stage": "toddler", "bands": {"24-59"}, "text": "Makan utama: nasi + ayam + sayur + buah", "allergens": set(), "tags": {"animal"}},
    {"stage": "toddler", "bands": {"24-59"}, "text": "Makan utama: nasi + ikan matang tanpa duri + tempe + sayur", "allergens": {"ikan", "seafood", "kedelai", "soy"}, "tags": {"animal", "seafood"}},
    {"stage": "toddler", "bands": {"24-59"}, "text": "Camilan: buah potong sesuai kemampuan makan + yogurt tawar", "allergens": {"susu", "milk", "dairy"}, "tags": {"snack", "dairy"}},
    {"stage": "toddler", "bands": {"24-59"}, "text": "Camilan: pisang + ubi kukus", "allergens": set(), "tags": {"snack", "vegetarian", "vegan"}},
    # Elderly standard
    {"stage": "elderly", "bands": {"standard"}, "text": "Sarapan: oatmeal + telur matang + buah", "allergens": {"telur", "egg"}, "tags": {"animal"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Makan utama: nasi + ikan matang + sayur bening + buah", "allergens": {"ikan", "seafood"}, "tags": {"animal", "seafood"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Makan utama: nasi + ayam + tahu + sayur", "allergens": {"kedelai", "soy"}, "tags": {"animal"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Selingan: buah + kacang yang aman dikunyah", "allergens": {"kacang", "peanut", "nuts"}, "tags": {"snack"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Sarapan: nasi + telur matang + tumis sayur + pepaya", "allergens": {"telur", "egg"}, "tags": {"animal", "local"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Makan utama: nasi + tempe + sayur asem/bening + pisang", "allergens": {"kedelai", "soy"}, "tags": {"vegetarian", "local"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Makan utama: ubi atau kentang + ikan matang + sayur + buah", "allergens": {"ikan", "seafood"}, "tags": {"animal", "seafood", "local"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Makan utama: nasi + tahu + ayam + sayur bening", "allergens": {"kedelai", "soy"}, "tags": {"animal", "local"}},
    {"stage": "elderly", "bands": {"standard"}, "text": "Selingan: pisang atau pepaya + sumber protein yang biasa dikonsumsi", "allergens": set(), "tags": {"snack", "local"}},
    # Elderly swallowing-context examples: composition only. These examples do
    # not prescribe texture/thickness; users should keep the form already known
    # to be safe for them.
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Nasi + ikan matang tanpa duri + sayur + pepaya; gunakan bentuk/tekstur yang sudah diketahui aman", "allergens": {"ikan", "seafood"}, "tags": {"animal", "seafood"}},
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Nasi + tahu atau tempe + sayur + pisang; gunakan bentuk/tekstur yang sudah diketahui aman", "allergens": {"kedelai", "soy"}, "tags": {"vegetarian"}},
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Kentang atau ubi + ayam + sayur + buah; gunakan bentuk/tekstur yang sudah diketahui aman", "allergens": set(), "tags": {"animal"}},
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Oat + telur matang + buah; gunakan bentuk/tekstur yang sudah diketahui aman", "allergens": {"telur", "egg"}, "tags": {"animal"}},
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Nasi + telur matang + sayur + pepaya; pertahankan bentuk/tekstur yang sudah diketahui aman", "allergens": {"telur", "egg"}, "tags": {"animal", "local"}},
    {"stage": "elderly_swallowing", "bands": {"standard"}, "text": "Ubi atau kentang + tahu/tempe + sayur + pisang; pertahankan bentuk/tekstur yang sudah diketahui aman", "allergens": {"kedelai", "soy"}, "tags": {"vegetarian", "local"}},
    # Elderly chewing-friendly (not dysphagia therapy)
    {"stage": "elderly_soft", "bands": {"standard"}, "text": "Bubur/nasi lunak + ayam cincang lembut + sayur lunak", "allergens": set(), "tags": {"animal", "soft"}},
    {"stage": "elderly_soft", "bands": {"standard"}, "text": "Kentang lumat + ikan matang lembut tanpa duri + sayur yang dimasak lunak", "allergens": {"ikan", "seafood"}, "tags": {"animal", "soft", "seafood"}},
    {"stage": "elderly_soft", "bands": {"standard"}, "text": "Oatmeal lembut + pisang matang + telur orak-arik matang", "allergens": {"telur", "egg"}, "tags": {"animal", "soft"}},
]
