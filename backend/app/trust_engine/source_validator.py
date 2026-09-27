from urllib.parse import urlparse, urlunparse

AUTHORITY = {
    "government": 1.0,
    "international_health_agency": 1.0,
    "clinical_guideline": 0.95,
    "scientific_organization": 0.92,
    "university": 0.88,
    "peer_reviewed": 0.84,
    "news": 0.55,
    "social": 0.25,
}


def source_authority(source_type: str, declared_score: float | None = None, verified: bool = True) -> float:
    score = declared_score if declared_score is not None else AUTHORITY.get(source_type, 0.4)
    score = max(0.0, min(1.0, score))
    return score if verified else min(score, 0.35)


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host if not port or (scheme == "https" and port == 443) or (scheme == "http" and port == 80) else f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def source_is_usable(url: str, verified: bool) -> bool:
    if not verified:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def source_tier(source_type: str) -> int:
    if source_type in {"government", "international_health_agency"}:
        return 1
    if source_type in {"clinical_guideline", "scientific_organization", "university"}:
        return 2
    if source_type == "peer_reviewed":
        return 3
    if source_type == "news":
        return 4
    return 5


def source_reason(source_type: str, verified: bool) -> str:
    tier = source_tier(source_type)
    if not verified:
        return "Sumber tidak ditandai terverifikasi dan tidak digunakan untuk verdict."
    labels = {
        1: "Sumber otoritas kesehatan pemerintah/internasional.",
        2: "Guideline, organisasi ilmiah, atau institusi akademik.",
        3: "Publikasi ilmiah peer-reviewed atau metadata indeks ilmiah.",
        4: "Media kredibel; digunakan dengan bobot otoritas lebih rendah.",
        5: "Konten pengguna/sosial; bukan sumber utama untuk verdict.",
    }
    return labels[tier]
