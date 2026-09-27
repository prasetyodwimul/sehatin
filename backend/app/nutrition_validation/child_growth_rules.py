from __future__ import annotations

from .base_rules import ValidationIssue
from .who_reference import weight_for_age_band, weight_for_length_height_bounds


def validate_child(*, age_months: int, sex: str, weight_kg: float, height_cm: float) -> tuple[list[ValidationIssue], list[dict]]:
    issues: list[ValidationIssue] = []
    indicators: list[dict] = []

    if not 2.0 <= weight_kg <= 40.0:
        issues.append(ValidationIssue("INVALID", "WEIGHT_TECHNICAL_RANGE", "Berat badan tidak dapat diproses karena nilainya berada di luar batas input teknis modul anak."))
    if not 45.0 <= height_cm <= 125.0:
        issues.append(ValidationIssue("INVALID", "HEIGHT_TECHNICAL_RANGE", "Length/height tidak dapat diproses karena nilainya berada di luar batas input teknis modul anak."))
    if issues:
        return issues, indicators

    bmi = weight_kg / ((height_cm / 100.0) ** 2)
    indicators.append({"indicator": "technical_weight_height_consistency", "value": round(bmi, 1), "unit": "kg/m²", "interpretation": "Digunakan hanya untuk mendeteksi kemungkinan salah input, bukan klasifikasi BMI anak."})
    if bmi < 6.0 or bmi > 45.0:
        issues.append(ValidationIssue("INVALID", "WEIGHT_HEIGHT_INCONSISTENT", "Nilai berat badan tampaknya tidak sesuai dengan length/height yang dimasukkan. Periksa kembali satuan dan pengukuran."))
        return issues, indicators

    wfa = weight_for_age_band(sex, age_months)
    if wfa:
        in_wfa = wfa.low_3sd <= weight_kg <= wfa.high_3sd
        indicators.append({
            "indicator": "weight_for_age",
            "reference": "WHO Child Growth Standards 2006",
            "range_3sd": f"{wfa.low_3sd:.1f}–{wfa.high_3sd:.1f} kg",
            "median": f"{wfa.median:.1f} kg",
            "within_reference": in_wfa,
        })
        if not in_wfa:
            issues.append(ValidationIssue("WARNING", "WFA_OUTSIDE_REFERENCE", "Berat badan berada di luar rentang ±3 SD weight-for-age pada referensi WHO yang digunakan sistem. Pastikan pengukuran benar dan pertimbangkan diskusi dengan tenaga kesehatan."))

    wlh = weight_for_length_height_bounds(sex, age_months, height_cm)
    if wlh:
        low, high = wlh
        in_wlh = low <= weight_kg <= high
        indicators.append({
            "indicator": "weight_for_length" if age_months < 24 else "weight_for_height",
            "reference": "WHO Child Growth Standards 2006",
            "range_3sd": f"{low:.1f}–{high:.1f} kg",
            "within_reference": in_wlh,
            "note": "Batas diinterpolasi dari anchor tabel lapangan WHO untuk screening konsistensi input.",
        })
        if not in_wlh:
            issues.append(ValidationIssue("WARNING", "WLH_OUTSIDE_REFERENCE", "Berat terhadap length/height berada di luar rentang referensi yang digunakan sistem. Hasil ini bukan diagnosis; periksa pengukuran dan pertimbangkan konsultasi tenaga kesehatan."))
    else:
        issues.append(ValidationIssue("WARNING", "HEIGHT_REFERENCE_UNAVAILABLE", "Length/height berada di luar rentang tabel weight-for-length/height yang digunakan modul ini. Sistem tetap dapat memberi panduan umum, tetapi interpretasi antropometri dibatasi."))

    return issues, indicators
