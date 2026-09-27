"""
Phase 1 test: confirms the app boots and /health responds correctly, even
without a live database connection (matches app/database.py's
fail-soft design).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok_status():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "SEHATIN"
    assert body["database"] in ("connected", "unavailable")


def test_root_returns_a_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "SEHATIN" in response.json()["message"]
