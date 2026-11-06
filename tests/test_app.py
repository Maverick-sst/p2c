import importlib
import os


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-auth-token")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.ngrok.app")
    monkeypatch.setenv("ALLOWED_PHONE", "+919999999999")
    monkeypatch.setenv("ACCESS_PIN", "123456")

    module = importlib.import_module("app.main")
    from fastapi.testclient import TestClient

    client = TestClient(module.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "p2c"}
