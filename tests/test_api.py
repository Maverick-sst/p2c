from fastapi.testclient import TestClient
from app import storage
from app.main import app
from app.auth import issue_pairing_code


def test_health_pairing_and_authorized_catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "p2c.sqlite3")
    storage.init_db()
    code, _ = issue_pairing_code()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/commands").status_code == 401
        paired = client.post("/api/v1/pairing/claim", json={"pairing_code": code, "device_name": "Test phone"})
        assert paired.status_code == 200
        assert "p2c_session" in paired.cookies
        catalog = client.get("/api/v1/commands")
        assert catalog.status_code == 200
        assert {item["key"] for item in catalog.json()["commands"]} == {"01", "02", "03"}
        assert client.post("/api/v1/commands/unknown/runs", json={"source": "dashboard"}).status_code == 404
        headers = {"Idempotency-Key": "test-run-key-0001"}
        first = client.post("/api/v1/commands/system.network/runs",
                            json={"source": "dashboard"}, headers=headers)
        assert first.status_code == 202
        second = client.post("/api/v1/commands/system.network/runs",
                             json={"source": "dashboard"}, headers=headers)
        assert second.status_code == 202
        assert second.json()["run"]["id"] == first.json()["run"]["id"]
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/commands").status_code == 401
