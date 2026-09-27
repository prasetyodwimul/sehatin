from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.blood.demo_provider import DEMO_FACILITIES
from app.main import app
from app.models import Base, BloodFacilityModel, EvidenceDocumentModel, EvidenceSourceModel
from app.scripts.seed_demo_data import seed_demo_data
from app.security import RateLimitMiddleware
from app.trust_engine.evidence_provider import EvidenceRecord
from app.trust_engine.demo_evidence import DemoEvidenceProvider
from app.trust_engine.source_validator import source_is_usable
from app.trust_engine.trust_engine import TrustEngine

client = TestClient(app)

EXPECTED_TABLES = {
    "nutrition_requests",
    "nutrition_recommendations",
    "blood_facilities",
    "blood_inventory",
    "blood_requests",
    "health_claims",
    "evidence_sources",
    "evidence_documents",
    "claim_evidence",
    "system_logs",
}
PERSISTENT_AUTH_TABLES = {"users", "auth_sessions", "nutrition_profiles", "nutrition_programs", "nutrition_program_days", "nutrition_meal_logs", "nutrition_evaluations"}


def test_sqlalchemy_metadata_preserves_public_request_schema_and_scopes_auth_to_persistence():
    tables = set(Base.metadata.tables)
    assert EXPECTED_TABLES.issubset(tables)
    assert PERSISTENT_AUTH_TABLES.issubset(tables)
    # Public health/blood claims remain request-based and are not account-owned.
    for name in {"health_claims", "blood_requests", "claim_evidence"}:
        assert "user_id" not in Base.metadata.tables[name].columns
    # Credentials live only in the account table; no plaintext password column exists.
    assert "password_hash" in Base.metadata.tables["users"].columns
    assert "password" not in Base.metadata.tables["users"].columns


def test_schema_can_be_created_from_empty_database():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
    finally:
        engine.dispose()


def test_alembic_upgrade_works_from_blank_database(tmp_path, monkeypatch):
    db_path = tmp_path / "migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))
    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(tables)
        assert "alembic_version" in tables
    finally:
        engine.dispose()



def test_alembic_upgrade_from_previous_core_schema_to_guided_nutrition(tmp_path, monkeypatch):
    db_path = tmp_path / "upgrade_existing.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))

    command.upgrade(cfg, "20260915_0001")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        before = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.issubset(before)
        assert "users" not in before
    finally:
        engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        after = set(inspector.get_table_names())
        assert EXPECTED_TABLES.issubset(after)
        assert PERSISTENT_AUTH_TABLES.issubset(after)
        recommendation_columns = {column["name"] for column in inspector.get_columns("nutrition_recommendations")}
        assert {"user_id", "profile_id"}.issubset(recommendation_columns)
        request_columns = {column["name"] for column in inspector.get_columns("nutrition_requests")}
        assert "height_cm" in request_columns
        program_columns = {column["name"] for column in inspector.get_columns("nutrition_programs")}
        assert "completed_at" in program_columns
        assert "cancelled_at" in program_columns
    finally:
        engine.dispose()

def test_alembic_upgrade_from_existing_guided_schema_to_progress_fix(tmp_path, monkeypatch):
    db_path = tmp_path / "upgrade_guided_0002.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    backend = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "alembic"))

    command.upgrade(cfg, "20260916_0002")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    before_columns = {column["name"] for column in inspect(engine).get_columns("nutrition_programs")}
    assert "completed_at" not in before_columns
    engine.dispose()

    command.upgrade(cfg, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    after_columns = {column["name"] for column in inspect(engine).get_columns("nutrition_programs")}
    assert "completed_at" in after_columns
    with engine.connect() as connection:
        version = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
    assert version == "20260926_0008"
    engine.dispose()


def test_demo_seed_is_idempotent_and_source_traceable():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            first = seed_demo_data(db)
            db.commit()
            second = seed_demo_data(db)
            db.commit()
            assert first["blood_facilities"] == len(DEMO_FACILITIES)
            assert second["evidence_documents"] == len(DemoEvidenceProvider().records())
            assert len(db.scalars(select(BloodFacilityModel)).all()) == len(DEMO_FACILITIES)
            sources = db.scalars(select(EvidenceSourceModel)).all()
            docs = db.scalars(select(EvidenceDocumentModel)).all()
            assert len(sources) == len(DemoEvidenceProvider().records())
            assert len(docs) == len(DemoEvidenceProvider().records())
            assert all(source.url.startswith("https://") for source in sources)
            assert all(source.verified for source in sources)
            assert all(doc.source_id for doc in docs)
    finally:
        engine.dispose()


def test_health_checker_part1_contract_and_provenance():
    response = client.post("/api/health-checker/analyze", json={"text": "Antibiotik bisa menyembuhkan flu karena virus."})
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == body["verdict"] == "CONTRADICTED"
    assert body["confidence"] == body["evidence_confidence"]
    assert body["summary"] == body["explanation"]
    assert body["reason"] == body["why_this_result"]
    assert body["sources"]
    assert all(item["url"].startswith("https://") for item in body["sources"])


def test_unverified_or_non_https_evidence_is_not_used():
    class UnsafeProvider:
        @property
        def is_demo(self):
            return True

        def records(self):
            return [
                EvidenceRecord(
                    id="unsafe",
                    keywords=("antibiotik", "virus"),
                    title="Unverified",
                    source="Unknown",
                    source_type="social",
                    publication_date="2026-01-01",
                    retrieved_at="2026-09-15",
                    url="http://example.invalid/source",
                    stance="support",
                    excerpt="Unverified content",
                    quality=0.2,
                    authority_level=5,
                    verified=False,
                    demo=True,
                )
            ]

    result = TrustEngine(UnsafeProvider()).analyze("Antibiotik untuk virus")
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert result.sources_checked == 0
    assert source_is_usable("http://example.invalid", True) is False


def test_blood_api_has_quantity_facility_filter_and_demo_label():
    response = client.get("/api/blood/inventory", params={"blood_type": "O", "rhesus": "+", "facility": "Bandung"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["demo_data"] is True
    assert body[0]["verified"] is False
    assert body[0]["inventory"][0]["quantity"] == body[0]["inventory"][0]["units"]


def test_security_headers_request_limit_and_sql_injection_shaped_input():
    health = client.get("/health")
    assert health.headers["x-content-type-options"] == "nosniff"
    assert health.headers["x-frame-options"] == "DENY"
    assert "x-request-id" in health.headers

    too_large = client.post(
        "/api/health-checker/analyze",
        content=b"x" * 70000,
        headers={"content-type": "application/json"},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "REQUEST_TOO_LARGE"

    shaped = client.get("/api/blood/facilities", params={"city": "Bandung' OR 1=1 --"})
    assert shaped.status_code == 200
    assert shaped.json() == []


def test_basic_rate_limiter_returns_429():
    tiny = FastAPI()
    tiny.add_middleware(RateLimitMiddleware, requests_per_minute=2)

    @tiny.get("/limited")
    def limited():
        return {"ok": True}

    c = TestClient(tiny)
    assert c.get("/limited").status_code == 200
    assert c.get("/limited").status_code == 200
    third = c.get("/limited")
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "RATE_LIMITED"


def test_nutrition_contract_includes_guidance_and_reference_labels():
    response = client.post(
        "/api/nutrition/recommendation",
        json={"stage": "mpasi", "age_months": 8, "feeding_mode": "breastmilk", "sex": "male", "weight_kg": 8.2, "height_cm": 69.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guidance"]
    assert body["references"]
    assert all("http" not in reference.lower() for reference in body["references"])
    assert "Estimasi" in body["summary"] or "rekomendasi edukatif" in body["summary"].lower()


def test_sqlalchemy_persistence_and_database_providers(tmp_path):
    from app.blood.database_provider import DatabaseBloodProvider
    from app.config import get_settings
    from app.database import get_engine, reset_database_caches, session_scope
    from app.knowledge_base.database_provider import DatabaseEvidenceProvider
    from app.schemas.nutrition import NutritionRequest
    from app.services.nutrition_service import generate_nutrition_recommendation
    from app.services.persistence import persist_health_analysis, persist_nutrition_result
    from app.trust_engine.trust_engine import TrustEngine

    settings = get_settings()
    old_url = settings.database_url
    old_persistence = settings.persistence_enabled
    old_anonymous_nutrition = settings.persist_anonymous_nutrition_personal_data
    db_path = tmp_path / "runtime.db"
    try:
        settings.database_url = f"sqlite:///{db_path.as_posix()}"
        settings.persistence_enabled = True
        settings.persist_anonymous_nutrition_personal_data = True
        reset_database_caches()
        Base.metadata.create_all(get_engine())
        with session_scope() as db:
            seed_demo_data(db)

        nutrition_request = NutritionRequest(stage="toddler", age_months=36, sex="female", weight_kg=14, height_cm=95)
        nutrition_result = generate_nutrition_recommendation(nutrition_request)
        assert persist_nutrition_result(nutrition_request, nutrition_result)

        evidence_provider = DatabaseEvidenceProvider()
        assert len(evidence_provider.records()) == len(DemoEvidenceProvider().records())
        blood_provider = DatabaseBloodProvider()
        assert len(blood_provider.list_facilities()) == len(DEMO_FACILITIES)

        analysis = TrustEngine(evidence_provider).analyze("Antibiotik bisa menyembuhkan flu karena virus.")
        assert analysis.verdict == "CONTRADICTED"
        assert persist_health_analysis("Antibiotik bisa menyembuhkan flu karena virus.", analysis)
    finally:
        settings.database_url = old_url
        settings.persistence_enabled = old_persistence
        settings.persist_anonymous_nutrition_personal_data = old_anonymous_nutrition
        reset_database_caches()


def test_nutrition_day_interval_can_be_accelerated_only_outside_production(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("NUTRITION_DAY_INTERVAL_SECONDS", "30")
    get_settings.cache_clear()
    assert get_settings().effective_nutrition_day_interval_seconds == 30

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_PEPPER", "production-test-pepper")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "true")
    get_settings.cache_clear()
    assert get_settings().effective_nutrition_day_interval_seconds == 86400

    get_settings.cache_clear()
