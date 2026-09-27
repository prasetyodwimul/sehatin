from __future__ import annotations

import socket

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.article_extractor import extract_article_from_html
from app.services.health_checker_service import SlidingWindowLimiter
from app.services.url_safety import UnsafeUrlError, validate_external_url
from app.trust_engine.claim_extractor import classify_claim, extract_claims
from app.trust_engine.demo_evidence import DemoEvidenceProvider
from app.trust_engine.trust_engine import TrustEngine
from app.trust_engine.live_evidence_provider import build_pubmed_query

client = TestClient(app)


def test_claim_extractor_splits_article_into_multiple_checkable_claims():
    claims = extract_claims(
        "Makan sayur dan buah mendukung pola makan sehat. "
        "Antibiotik bisa menyembuhkan flu karena virus. "
        "Tidur cukup membantu kesehatan umum."
    )
    assert len(claims) == 3
    assert claims[0].claim_id.startswith("claim-1-")
    assert claims[1].claim_type in {"MEDICATION", "HEALTH_TREATMENT"}
    assert claims[0].topic


def test_claim_type_classification_covers_common_health_domains():
    assert classify_claim("Vaksin membantu pencegahan penyakit") == "VACCINE"
    assert classify_claim("Antibiotik adalah obat untuk infeksi bakteri") == "MEDICATION"
    assert classify_claim("Asupan protein penting untuk nutrisi") == "NUTRITION"


def test_article_api_returns_multi_claim_results_and_legacy_top_level_contract():
    response = client.post(
        "/api/health-checker/analyze",
        json={
            "input_type": "article",
            "text": "Makan sayur dan buah mendukung pola makan sehat. Antibiotik bisa menyembuhkan flu karena virus.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input_type"] == "article"
    assert body["checked_claims"] == 2
    assert len(body["claims"]) == 2
    assert body["claim"] == body["claims"][0]["claim"]
    assert body["verdict"] == body["claims"][0]["verdict"]
    assert body["run_id"]


def test_unknown_claim_remains_insufficient_without_fake_confidence():
    response = client.post(
        "/api/health-checker/analyze",
        json={"input_type": "claim", "text": "Klaim eksperimental xyzabc yang belum memiliki evidence di sistem."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert body["trust_score"] == 0
    assert body["confidence"] == 0


def test_url_security_blocks_localhost_private_and_unsafe_schemes():
    for url in [
        "http://127.0.0.1/admin",
        "http://10.0.0.10/private",
        "http://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
        "ftp://example.com/file",
    ]:
        with pytest.raises(UnsafeUrlError):
            validate_external_url(url)


def test_url_security_blocks_hostname_that_resolves_private(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 443))],
    )
    with pytest.raises(UnsafeUrlError):
        validate_external_url("https://example.test/article")


def test_url_security_allows_public_http_https_after_dns_validation(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    validated = validate_external_url("https://example.com/article")
    assert validated.hostname == "example.com"
    assert validated.resolved_ips == ("93.184.216.34",)


def test_url_endpoint_rejects_private_target_without_fetching_it():
    response = client.post(
        "/api/health-checker/analyze-url",
        json={"input_type": "url", "url": "http://127.0.0.1/internal"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSAFE_URL"


def test_article_extractor_removes_script_and_keeps_readable_metadata():
    html = """
    <html><head>
      <title>Judul Artikel</title>
      <meta property="og:site_name" content="Publisher Demo">
      <meta name="author" content="Penulis Demo">
      <meta property="article:published_time" content="2026-09-18">
      <script>IGNORE_ME = 'prompt injection';</script>
    </head><body>
      <nav>Menu yang tidak relevan</nav>
      <article><h1>Judul Artikel</h1>
      <p>Ini adalah paragraf utama yang berisi informasi kesehatan dan cukup panjang untuk dapat diekstrak secara aman.</p>
      <p>Paragraf kedua menjelaskan konteks evidence tanpa mengeksekusi HTML atau script dari halaman.</p></article>
    </body></html>
    """
    article = extract_article_from_html(html, final_url="https://example.com/a")
    assert article.title == "Judul Artikel"
    assert article.publisher == "Publisher Demo"
    assert article.author == "Penulis Demo"
    assert "IGNORE_ME" not in article.main_text
    assert "Menu yang tidak relevan" not in article.main_text
    assert "paragraf utama" in article.main_text


def test_pubmed_query_builder_maps_common_indonesian_health_terms():
    query = build_pubmed_query("Antibiotik bisa menyembuhkan flu karena virus")
    lowered = query.lower()
    assert "antibiotic" in lowered
    assert "influenza" in lowered


def test_pubmed_query_builder_maps_nutrition_and_lipid_terms():
    query = build_pubmed_query("Makan daging bisa bikin kolesterol tinggi karena lemak jenuh")
    lowered = query.lower()
    assert "cholesterol" in lowered
    assert "dyslipidemia" in lowered
    assert "saturated fat" in lowered or "saturated" in lowered


def test_pubmed_query_builder_expands_late_eating_claim():
    query = build_pubmed_query("Makan pada malam hari dapat membuat gendut")
    lowered = query.lower()
    assert "late eating" in lowered
    assert "meal timing" in lowered
    assert "obesity" in lowered
    assert "weight gain" in lowered


def test_curated_corpus_includes_who_and_kemkes_lipid_sources():
    records = DemoEvidenceProvider().records()
    sources = {record.source for record in records}
    assert "World Health Organization" in sources
    assert "Kementerian Kesehatan Republik Indonesia" in sources

    result = TrustEngine(DemoEvidenceProvider()).analyze("Makan daging bisa bikin kolesterol")
    assert result.sources_checked >= 3
    assert any(item.source == "World Health Organization" for item in result.supporting_evidence)
    assert any(item.source == "Kementerian Kesehatan Republik Indonesia" for item in result.supporting_evidence)
    assert result.verdict in {"SUPPORTED", "PARTIALLY_SUPPORTED"}


def test_health_checker_specific_rate_limiter_uses_sliding_window():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-b") is True


def test_url_security_rejects_mixed_public_private_dns_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443)),
        ],
    )
    with pytest.raises(UnsafeUrlError):
        validate_external_url("https://mixed.example.test/article")


def test_pinned_http_connection_rejects_changed_actual_peer(monkeypatch):
    from app.services.url_safety import PinnedHTTPConnection

    seen: list[tuple[str, int]] = []

    class FakeSocket:
        def getpeername(self):
            return ("127.0.0.1", 80)

        def close(self):
            pass

    def fake_create_connection(address, *args, **kwargs):
        seen.append(address)
        return FakeSocket()

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    connection = PinnedHTTPConnection("example.test", "93.184.216.34", port=80, timeout=1.0)
    with pytest.raises(UnsafeUrlError):
        connection.connect()
    assert seen == [("93.184.216.34", 80)]


def test_pinned_https_connection_keeps_original_hostname_for_tls(monkeypatch):
    from app.services.url_safety import PinnedHTTPSConnection

    wrapped: dict[str, str] = {}

    class FakeSocket:
        def getpeername(self):
            return ("93.184.216.34", 443)

        def close(self):
            pass

    class FakeContext:
        def wrap_socket(self, sock, *, server_hostname):
            wrapped["server_hostname"] = server_hostname
            return sock

    monkeypatch.setattr(socket, "create_connection", lambda *args, **kwargs: FakeSocket())
    connection = PinnedHTTPSConnection(
        "evidence.example.test",
        "93.184.216.34",
        port=443,
        timeout=1.0,
        context=FakeContext(),  # type: ignore[arg-type]
    )
    connection.connect()
    assert wrapped["server_hostname"] == "evidence.example.test"


def test_article_redirect_to_private_target_is_rejected_before_second_connection(monkeypatch):
    import app.services.article_extractor as article_extractor

    calls = 0

    class FakeResponse:
        status = 302
        headers = {"Location": "http://127.0.0.1/internal"}

        def close(self):
            pass

    class FakeConnection:
        def close(self):
            pass

    def fake_open(*args, **kwargs):
        nonlocal calls
        calls += 1
        return FakeConnection(), FakeResponse()

    monkeypatch.setattr(article_extractor, "_open_validated_response", fake_open)
    with pytest.raises(UnsafeUrlError):
        article_extractor.fetch_article("http://93.184.216.34/start")
    assert calls == 1


def test_health_checker_diabetes_claim_does_not_mix_antibiotic_evidence():
    response = client.post(
        "/api/health-checker/analyze",
        json={"text": "mengonsumsi makanan atau minuman manis setiap hari dapat menyebabkan diabetes"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["claim"] == "mengonsumsi makanan atau minuman manis setiap hari dapat menyebabkan diabetes"
    assert all("antibiotik" not in item["excerpt"].lower() for item in body["supporting_evidence"] + body["contradicting_evidence"])
    assert all("antibiotik" not in item["title"].lower() for item in body["sources"])


def test_auto_provider_never_falls_back_to_demo_in_production(monkeypatch):
    from app.knowledge_base.provider_factory import AutoEvidenceProvider
    import app.knowledge_base.provider_factory as provider_factory

    class FakeSettings:
        environment = "production"

    provider = AutoEvidenceProvider()
    monkeypatch.setattr(provider.database, "records", lambda: [])
    monkeypatch.setattr(provider_factory, "get_settings", lambda: FakeSettings())

    records = provider.records()
    assert records
    assert all(record.demo is False for record in records)
    assert provider.is_demo is False


def test_curated_late_eating_claim_has_directional_evidence_without_live_network():
    result = TrustEngine(DemoEvidenceProvider()).analyze("Makan pada malam hari dapat membuat gendut")
    assert result.sources_checked >= 3
    assert len(result.supporting_evidence) >= 2
    assert any("late eating" in item.title.lower() for item in result.supporting_evidence)
    assert result.verdict in {"SUPPORTED", "PARTIALLY_SUPPORTED"}
    assert result.demo_evidence is False


def test_curated_sugar_diabetes_claim_has_multiple_independent_pubmed_sources():
    result = TrustEngine(DemoEvidenceProvider()).analyze("Makan dan minum manis terlalu sering dapat mengakibatkan diabetes")
    assert result.sources_checked >= 3
    assert len(result.supporting_evidence) >= 2
    assert len({item.independent_group for item in result.supporting_evidence}) >= 2
    assert result.verdict in {"SUPPORTED", "PARTIALLY_SUPPORTED"}


def test_late_eating_does_not_match_unrelated_sugar_evidence():
    result = TrustEngine(DemoEvidenceProvider()).analyze("Makan pada malam hari dapat membuat gendut")
    titles = [item.title.lower() for item in result.supporting_evidence]
    assert not any("sugar sweetened" in title or "sugar-sweetened" in title for title in titles)


def test_pubmed_query_builder_expands_late_eating_and_acid_reflux_terms():
    query = build_pubmed_query("Telat makan dapat menyebabkan asam lambung")
    lowered = query.lower()
    assert "late eating" in lowered
    assert "gastroesophageal reflux" in lowered
    assert "gerd" in lowered
    assert "acid reflux" in lowered


def test_curated_corpus_covers_common_late_meal_reflux_claim():
    result = TrustEngine(DemoEvidenceProvider()).analyze("Telat makan dapat menyebabkan asam lambung")
    assert result.sources_checked >= 3
    assert any("reflux" in item.title.lower() or "gerd" in item.title.lower() for item in result.supporting_evidence)
    assert result.verdict in {"SUPPORTED", "PARTIALLY_SUPPORTED"}


def test_curated_common_wound_claim_supports_moisture_infection_link_without_absolute_causation():
    result = TrustEngine(DemoEvidenceProvider()).analyze("luka jika terkena air terus menerus dapat bernanah")
    assert result.sources_checked >= 3
    assert len(result.supporting_evidence) >= 2
    assert len(result.neutral_evidence) >= 2
    assert result.verdict == "PARTIALLY_SUPPORTED"
    assert "sebab-akibat" in result.explanation.lower()


def test_common_everyday_health_claims_have_curated_fallback_coverage():
    provider = DemoEvidenceProvider()
    checks = {
        "Telat makan dapat menyebabkan asam lambung": "NIDDK",
        "Kurang tidur dapat membuat gemuk": "CDC",
        "Mencuci ayam mentah dapat menyebabkan keracunan makanan": "CDC",
        "Kalau mimisan kepala harus ditengadahkan": "NHS",
        "Luka bakar harus disiram air mengalir": "NHS",
        "Susu menyebabkan diare pada orang intoleransi laktosa": "NIDDK",
    }
    for claim, _source in checks.items():
        result = TrustEngine(provider).analyze(claim)
        assert result.sources_checked >= 1, claim
        assert all(item.url.startswith("http") for item in result.sources), claim


def test_europe_pmc_provider_parses_core_result_without_network(monkeypatch):
    from app.trust_engine.europe_pmc_evidence_provider import EuropePMCEvidenceProvider

    payload = {
        "resultList": {
            "result": [
                {
                    "id": "123456",
                    "pmid": "123456",
                    "source": "MED",
                    "title": "Late eating and obesity risk",
                    "abstractText": "Late eating was associated with higher risk of obesity in adults in this observational study.",
                    "journalTitle": "Example Medical Journal",
                    "firstPublicationDate": "2024-05-01",
                }
            ]
        }
    }

    provider = EuropePMCEvidenceProvider()
    monkeypatch.setattr(provider, "_get", lambda params: __import__("json").dumps(payload).encode())
    records, outage = provider.search("makan malam dapat membuat gemuk")
    assert outage is None
    assert len(records) == 1
    assert records[0].provider == "europepmc-live"
    assert records[0].verified is True
    assert records[0].demo is False
