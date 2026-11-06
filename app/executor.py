"""Bounded executor. Only the static registry can select a script."""
import asyncio
import sys
import time
from app.commands import ROOT
from app.config import MAX_OUTPUT_BYTES
from app import storage

_EXECUTION_LOCK = asyncio.Lock()


async def execute(run_id, command, publish):
    started = time.monotonic()
    storage.update_run(run_id, status="running")
    await publish({"type": "run.updated", "run": {"id": run_id, "status": "running"}})
    exit_code, output, truncated, status = 1, "", False, "failed"
    try:
        expected_dir = (ROOT / "scripts").resolve()
        script = command.script.resolve(strict=True)
        if script.parent != expected_dir or script.suffix != ".py":
            raise ValueError("Registered script is outside approved directory")
        async with _EXECUTION_LOCK:
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script), cwd=str(ROOT),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONIOENCODING": "utf-8"},
            )
            try:
                raw, _ = await asyncio.wait_for(process.communicate(), timeout=command.timeout_seconds)
                exit_code = process.returncode or 0
                truncated = len(raw) > MAX_OUTPUT_BYTES
                output = raw[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
                status = "succeeded" if exit_code == 0 else "failed"
            except asyncio.TimeoutError:
                process.kill()
                raw, _ = await process.communicate()
                output = raw[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace") + "\nExecution timed out."
                truncated = len(raw) > MAX_OUTPUT_BYTES
                status = "timed_out"
    except Exception as exc:
        output = "Execution failed: " + type(exc).__name__
    duration = int((time.monotonic() - started) * 1000)
    storage.update_run(run_id, status=status, exit_code=exit_code, output=output,
                       output_truncated=int(truncated), duration_ms=duration, finished_at=time.time())
    await publish({"type": "run.completed", "run": {"id": run_id, "status": status, "duration_ms": duration}})
