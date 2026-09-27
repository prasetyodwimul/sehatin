from app.trust_engine.demo_evidence import DemoEvidenceProvider
from app.trust_engine.live_evidence_provider import build_pubmed_query
from app.trust_engine.trust_engine import TrustEngine


def test_curated_registry_covers_broad_who_and_kemkes_domains_without_duplicate_urls():
    records = DemoEvidenceProvider().records()
    urls = [record.url for record in records]
    assert len(records) >= 30
    assert len(urls) == len(set(urls))

    who = [record for record in records if record.source == "World Health Organization"]
    kemkes = [record for record in records if record.source == "Kementerian Kesehatan Republik Indonesia"]
    assert len(who) >= 20
    assert len(kemkes) >= 8

    joined = " ".join(" ".join(record.keywords) for record in records).lower()
    for keyword in ("diabetes", "hipertensi", "kanker", "dengue", "tuberkulosis", "kesehatan mental", "imunisasi", "mpasi", "lansia"):
        assert keyword in joined


def test_common_health_claims_can_reach_authoritative_curated_sources():
    engine = TrustEngine(DemoEvidenceProvider())

    hypertension = engine.analyze("Garam tinggi dapat meningkatkan tekanan darah")
    assert hypertension.verdict == "SUPPORTED"
    assert any(item.source == "World Health Organization" for item in hypertension.supporting_evidence)

    complementary_feeding = engine.analyze("MPASI mulai usia 6 bulan")
    assert complementary_feeding.verdict == "SUPPORTED"
    sources = {item.source for item in complementary_feeding.supporting_evidence}
    assert "World Health Organization" in sources
    assert "Kementerian Kesehatan Republik Indonesia" in sources


def test_pubmed_query_translation_covers_broad_health_terms():
    query = build_pubmed_query(
        "Apakah aktivitas fisik membantu diabetes, hipertensi, kesehatan mental, obesitas, dan risiko jantung?"
    ).lower()
    for term in ("physical", "diabetes", "hypertension", "mental", "obesity", "cardiovascular"):
        assert term in query
