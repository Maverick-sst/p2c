import time
from app import storage


def test_pairing_code_is_one_time_and_session_is_revocable(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "p2c.sqlite3")
    storage.init_db()
    now = time.time()
    storage.create_pairing_code("code-hash", now + 60)
    assert storage.claim_pairing_code("code-hash", "dev_test", "Test phone", now, "token-hash", now + 600)
    assert not storage.claim_pairing_code("code-hash", "dev_other", "Other phone", now, "other-token", now + 600)
    assert storage.get_session("token-hash", now)["name"] == "Test phone"
    storage.revoke_session("token-hash", now + 1)
    assert storage.get_session("token-hash", now + 2) is None


def test_run_records_are_retrievable(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "p2c.sqlite3")
    storage.init_db()
    for index in range(3):
        storage.create_run({"id": f"run-{index}", "command_id": "system.status",
                            "source": "dashboard", "status": "queued", "created_at": time.time() + index})
    assert len(storage.list_runs(2)) == 2
