from pathlib import Path

from fastapi.testclient import TestClient

from app.blood.demo_provider import DemoBloodProvider
from app.main import app
from app.trust_engine.confidence_score import agreement_score
from app.trust_engine.source_validator import source_authority, source_tier
from app.trust_engine.trust_engine import analyze_claim

client = TestClient(app)


def test_demo_blood_covers_all_abo_rh_combinations():
    combinations = {
        f"{item.blood_type}{item.rhesus}"
        for facility in DemoBloodProvider().list_facilities()
        for item in facility.inventory
    }
    assert {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}.issubset(combinations)


def test_blood_response_exposes_simulated_mode_and_refresh_hint():
    response = client.get("/api/blood/inventory")
    assert response.status_code == 200
    rows = response.json()
    assert rows
    assert all(row["data_mode"] == "SIMULATED" for row in rows)
    assert all(row["refresh_hint_seconds"] >= 15 for row in rows)


def test_health_checker_has_all_demo_verdict_categories():
    supported = analyze_claim("Makan sayur dan buah mendukung pola makan sehat.")
    partial = analyze_claim("Vitamin C mencegah pilek dan membuat pilek lebih singkat.")
    insufficient = analyze_claim("Minum air lemon setiap pagi dapat menyembuhkan maag.")
    contradicted = analyze_claim("Antibiotik bisa menyembuhkan flu karena virus.")

    assert supported.verdict == "SUPPORTED"
    assert partial.verdict == "PARTIALLY_SUPPORTED"
    assert insufficient.verdict == "INSUFFICIENT_EVIDENCE"
    assert contradicted.verdict == "CONTRADICTED"


def test_partial_verdict_is_based_on_real_source_metadata_and_mixed_evidence():
    result = analyze_claim("Vitamin C mencegah pilek dan membuat pilek lebih singkat.")
    assert result.verdict == "PARTIALLY_SUPPORTED"
    assert result.supporting_evidence
    assert result.contradicting_evidence
    urls = {item.url for item in result.supporting_evidence + result.contradicting_evidence}
    assert any("ods.od.nih.gov" in url for url in urls)
    assert any("cochrane.org" in url for url in urls)
    assert result.score_breakdown.source_agreement < 1.0


def test_trust_engine_exposes_weights_and_evidence_level():
    response = client.post(
        "/api/health-checker/analyze",
        json={"text": "Antibiotik bisa menyembuhkan flu karena virus."},
    )
    assert response.status_code == 200
    body = response.json()
    weights = body["scoring_weights"]
    assert weights == {
        "source_authority": 0.3,
        "evidence_quality": 0.3,
        "recency": 0.15,
        "claim_relevance": 0.25,
    }
    assert body["evidence_level"] in {"HIGH", "MODERATE", "LOW", "INSUFFICIENT"}


def test_source_hierarchy_is_relative_and_ordered():
    assert source_tier("government") == 1
    assert source_tier("clinical_guideline") == 2
    assert source_tier("peer_reviewed") == 3
    assert source_tier("news") == 4
    assert source_tier("social") == 5
    assert source_authority("government") > source_authority("news") > source_authority("social")


def test_mixed_same_publisher_does_not_count_as_full_agreement():
    assert agreement_score({"Publisher A"}, {"Publisher A"}) == 0.5


def test_public_core_routes_keep_auth_optional():
    app_root = Path(__file__).resolve().parents[2] / "frontend" / "src" / "app"
    # Public product routes remain usable without auth, while direct account routes
    # are available for users who intentionally want persistence.
    assert (app_root / "login" / "page.tsx").exists()
    assert (app_root / "register" / "page.tsx").exists()
    assert (app_root / "nutrition" / "page.tsx").exists()
    assert (app_root / "blood" / "page.tsx").exists()
    assert (app_root / "health-checker" / "page.tsx").exists()
    assert not (app_root / "account").exists()
    assert not (app_root / "dashboard").exists()
    # Persistent nutrition is intentionally scoped below /nutrition/program.
    assert (app_root / "nutrition").exists()


def test_request_size_limit_covers_streamed_body_without_content_length():
    import asyncio

    from app.security import RequestSizeLimitMiddleware

    async def downstream(scope, receive, send):
        while True:
            message = await receive()
            if message["type"] == "http.request" and not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped = RequestSizeLimitMiddleware(downstream, max_bytes=5)
    incoming = [
        {"type": "http.request", "body": b"abc", "more_body": True},
        {"type": "http.request", "body": b"def", "more_body": False},
    ]
    outgoing = []

    async def receive():
        return incoming.pop(0)

    async def send(message):
        outgoing.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/stream",
        "raw_path": b"/stream",
        "query_string": b"",
        "headers": [(b"content-type", b"application/octet-stream")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    asyncio.run(wrapped(scope, receive, send))
    starts = [message for message in outgoing if message["type"] == "http.response.start"]
    assert starts and starts[0]["status"] == 413
