import asyncio
import time
from app import storage
from app.commands import get_command
from app.executor import execute


def test_registered_network_command_executes_and_persists_result(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "p2c.sqlite3")
    storage.init_db()
    run_id = "run-test-network"
    storage.create_run({
        "id": run_id, "command_id": "system.network", "source": "dashboard",
        "status": "queued", "created_at": time.time(),
    })
    events = []

    async def publish(event):
        events.append(event)

    asyncio.run(execute(run_id, get_command("system.network"), publish))
    result = storage.get_run(run_id)
    assert result["status"] == "succeeded"
    assert result["exit_code"] == 0
    assert result["output"]
    assert any(event["type"] == "run.completed" for event in events)
