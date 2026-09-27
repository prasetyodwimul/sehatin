from __future__ import annotations

from .base_rules import ValidationIssue


def validate_elderly(*, age_years: int, sex: str, weight_kg: float, height_cm: float) -> tuple[list[ValidationIssue], list[dict]]:
    issues: list[ValidationIssue] = []
    indicators: list[dict] = []
    if age_years < 60:
        issues.append(ValidationIssue("INVALID", "AGE_RANGE", "Modul lansia ditujukan untuk usia 60 tahun ke atas."))
    if not 25.0 <= weight_kg <= 250.0:
        issues.append(ValidationIssue("INVALID", "WEIGHT_TECHNICAL_RANGE", "Berat badan tidak dapat diproses karena nilainya berada di luar batas input teknis modul lansia."))
    if not 120.0 <= height_cm <= 220.0:
        issues.append(ValidationIssue("INVALID", "HEIGHT_TECHNICAL_RANGE", "Tinggi badan tidak dapat diproses karena nilainya berada di luar batas input teknis modul lansia."))
    if issues:
        return issues, indicators

    bmi = weight_kg / ((height_cm / 100.0) ** 2)
    indicators.append({
        "indicator": "body_mass_index_context",
        "value": round(bmi, 1),
        "unit": "kg/m²",
        "interpretation": "BMI ditampilkan sebagai konteks ukuran tubuh dan bukan diagnosis atau penetapan status kesehatan.",
    })
    if bmi < 10.0 or bmi > 60.0:
        issues.append(ValidationIssue("INVALID", "WEIGHT_HEIGHT_INCONSISTENT", "Nilai berat badan tampaknya tidak sesuai dengan tinggi badan yang dimasukkan. Periksa kembali data dan satuan."))
    elif bmi < 15.0 or bmi > 45.0:
        issues.append(ValidationIssue("WARNING", "EXTREME_BODY_SIZE_CONTEXT", "Kombinasi berat dan tinggi berada di luar rentang umum yang digunakan sistem untuk personalisasi. Pastikan pengukuran benar; panduan akan dibatasi pada informasi umum."))
    return issues, indicators
