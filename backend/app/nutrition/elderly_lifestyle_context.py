from __future__ import annotations

from typing import Any

from app.schemas.nutrition import NutritionRequest

HYDRATION_LABELS = {
    "regular": "Minum cukup teratur",
    "sometimes_low": "Kadang minum lebih sedikit",
    "often_low": "Sering minum lebih sedikit",
    "unknown": "Belum yakin dengan kebiasaan minum",
}

INDEPENDENCE_LABELS = {
    "independent": "Makan mandiri",
    "needs_reminder": "Perlu diingatkan saat makan/minum",
    "needs_setup": "Perlu disiapkan makanan/minuman",
    "needs_assistance": "Perlu bantuan langsung saat makan/minum",
    "unknown": "Kemandirian makan belum ditentukan",
}

CAREGIVER_LABELS = {
    "none": "Tidak ada dukungan rutin",
    "sometimes": "Dukungan tersedia sesekali",
    "daily": "Dukungan tersedia setiap hari",
    "unknown": "Dukungan caregiver belum ditentukan",
}


def build_elderly_lifestyle_context(req: NutritionRequest) -> dict[str, Any]:
    if req.stage != "elderly":
        return {}

    hydration = req.hydration_pattern or "unknown"
    independence = req.eating_independence or "unknown"
    caregiver = req.caregiver_support or "unknown"

    focus: list[str] = []
    daily_actions: list[str] = []
    notes: list[str] = []

    if hydration in {"sometimes_low", "often_low"}:
        focus.append("Bangun kebiasaan minum yang lebih teratur sesuai arahan yang sudah dimiliki")
        daily_actions.append("Siapkan akses minum yang mudah dijangkau dan catat apakah kebiasaan minum dapat dijalankan hari ini.")
        notes.append("SEHATIN tidak menetapkan target volume cairan individual karena kebutuhan dapat berbeda menurut kondisi kesehatan dan arahan klinis.")
    elif hydration == "regular":
        focus.append("Pertahankan kebiasaan minum yang teratur")

    if independence == "needs_reminder":
        focus.append("Gunakan pengingat makan/minum yang konsisten")
        daily_actions.append("Gunakan satu pengingat sederhana pada waktu makan atau minum yang paling sering terlewat.")
    elif independence == "needs_setup":
        focus.append("Siapkan makanan/minuman agar lebih mudah diakses")
        daily_actions.append("Siapkan satu waktu makan atau minum terlebih dahulu agar lebih mudah dijalankan.")
    elif independence == "needs_assistance":
        focus.append("Sesuaikan rencana dengan bantuan makan/minum yang tersedia")
        daily_actions.append("Pilih satu waktu makan yang dapat didampingi tanpa menambah beban berlebihan.")

    if caregiver == "none":
        notes.append("Program memprioritaskan langkah yang dapat dijalankan mandiri karena dukungan rutin tidak tersedia.")
    elif caregiver == "sometimes":
        focus.append("Gunakan dukungan caregiver pada waktu yang paling dibutuhkan")
    elif caregiver == "daily":
        focus.append("Libatkan caregiver untuk menjaga keteraturan bila diperlukan")

    # Keep this context educational and functional. It is not a functional-status
    # diagnosis and does not score dependency as good/bad.
    return {
        "hydration_pattern": hydration,
        "hydration_label": HYDRATION_LABELS[hydration],
        "eating_independence": independence,
        "eating_independence_label": INDEPENDENCE_LABELS[independence],
        "caregiver_support": caregiver,
        "caregiver_support_label": CAREGIVER_LABELS[caregiver],
        "focus": list(dict.fromkeys(focus))[:5],
        "daily_actions": list(dict.fromkeys(daily_actions))[:5],
        "notes": list(dict.fromkeys(notes))[:4],
        "context_kind": "USER_REPORTED_FUNCTIONAL_EATING_CONTEXT",
    }
