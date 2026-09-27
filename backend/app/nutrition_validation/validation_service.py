from __future__ import annotations

from .adult_rules import validate_elderly
from .base_rules import ValidationIssue, worst_level
from .child_growth_rules import validate_child
from .who_reference import WHO_CHILD_GROWTH_META


def validate_anthropometrics(*, stage: str, age_months: int | None, age_years: int | None, sex: str, weight_kg: float, height_cm: float) -> dict:
    issues: list[ValidationIssue] = []
    indicators: list[dict] = []

    if stage in {"mpasi", "toddler"}:
        if age_months is None:
            issues.append(ValidationIssue("INVALID", "AGE_REQUIRED", "Usia dalam bulan diperlukan untuk validasi anak."))
        elif sex not in {"female", "male"}:
            issues.append(ValidationIssue("INVALID", "SEX_REQUIRED", "Jenis kelamin diperlukan karena referensi pertumbuhan WHO bersifat spesifik menurut jenis kelamin."))
        else:
            child_issues, indicators = validate_child(age_months=age_months, sex=sex, weight_kg=weight_kg, height_cm=height_cm)
            issues.extend(child_issues)
    elif stage == "elderly":
        if age_years is None:
            issues.append(ValidationIssue("INVALID", "AGE_REQUIRED", "Usia dalam tahun diperlukan untuk validasi lansia."))
        else:
            adult_issues, indicators = validate_elderly(age_years=age_years, sex=sex, weight_kg=weight_kg, height_cm=height_cm)
            issues.extend(adult_issues)
    else:
        issues.append(ValidationIssue("INVALID", "UNSUPPORTED_STAGE", "Kategori nutrisi tidak dikenali."))

    status = worst_level(issues)
    if status == "VALID":
        message = "Data dapat diproses. Pengukuran berada dalam batas validasi yang digunakan sistem."
    elif status == "WARNING":
        message = "Data dapat diproses dengan catatan. Satu atau lebih nilai berada di luar rentang referensi yang digunakan sistem."
    else:
        message = "Data belum dapat diproses. Periksa kembali nilai, satuan, dan pengukuran yang dimasukkan."

    references = []
    if stage in {"mpasi", "toddler"}:
        references.append({
            **WHO_CHILD_GROWTH_META,
            "indicators": ["weight-for-age", "weight-for-length/height"],
        })

    return {
        "status": status,
        "can_process": status != "INVALID",
        "message": message,
        "issues": [{"level": i.level, "code": i.code, "message": i.message} for i in issues],
        "indicators": indicators,
        "references": references,
    }
