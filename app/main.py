"""Local-first P2C API and static frontend host."""
import asyncio
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import storage
from app.auth import claim_pairing, clear_session_cookie, current_session, digest, require_same_origin, set_session_cookie
from app.commands import get_command, public_commands
from app.config import APP_VERSION, COOKIE_NAME
from app.executor import execute
from app.realtime import EventHub

app = FastAPI(title="P2C — Local Mac Remote", version=APP_VERSION)
hub = EventHub()
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")


class PairRequest(BaseModel):
    pairing_code: str = Field(min_length=6, max_length=32)
    device_name: str = Field(default="Phone", min_length=1, max_length=40)


class RunRequest(BaseModel):
    source: str = Field(pattern="^(dashboard|keypad)$")


def run_json(row):
    return {
        "id": row["id"], "command_id": row["command_id"], "status": row["status"],
        "exit_code": row["exit_code"], "output": row["output"],
        "output_truncated": bool(row["output_truncated"]),
        "duration_ms": row["duration_ms"], "created_at": row["created_at"],
        "finished_at": row["finished_at"],
    }


@app.on_event("startup")
async def startup():
    storage.init_db()
    storage.recover_stale_runs()
    app.state.executor_busy = False


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "p2c", "version": APP_VERSION}


@app.get("/api/v1/pairing/status")
async def pairing_status():
    from app.config import DB_PATH
    if not DB_PATH.exists():
        return {"pairing_open": False, "expires_at": None}
    with storage.connection() as db:
        row = db.execute(
            "SELECT expires_at FROM pairing_codes WHERE consumed_at IS NULL AND expires_at>? ORDER BY expires_at DESC LIMIT 1",
            (time.time(),),
        ).fetchone()
    return {"pairing_open": bool(row), "expires_at": row["expires_at"] if row else None}


_pair_failures = {}


@app.post("/api/v1/pairing/claim")
async def pairing_claim(payload: PairRequest, request: Request):
    require_same_origin(request)
    peer = request.client.host if request.client else "unknown"
    now = time.time()
    failures = [stamp for stamp in _pair_failures.get(peer, []) if now - stamp < 300]
    if len(failures) >= 8:
        raise HTTPException(status_code=429, detail="Too many pairing attempts")
    device_name = payload.device_name.strip() or "Phone"
    result = claim_pairing(payload.pairing_code, device_name)
    if not result:
        failures.append(now)
        _pair_failures[peer] = failures
        raise HTTPException(status_code=403, detail="Pairing code is invalid, expired or already used")
    _pair_failures.pop(peer, None)
    token, device = result
    response = JSONResponse({
        "device": {"id": device["id"], "name": device["name"], "paired_at": device["paired_at"]},
        "session": {"expires_at": device["expires_at"]},
    })
    set_session_cookie(response, token)
    return response


@app.post("/api/v1/auth/logout", status_code=204)
async def logout(request: Request, session=Depends(current_session)):
    require_same_origin(request)
    storage.revoke_session(digest(request.cookies.get(COOKIE_NAME, "")), time.time())
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


@app.get("/api/v1/device")
async def device(session=Depends(current_session)):
    return {"device": {"id": session["device_id"], "name": session["name"]}, "server": "online"}


@app.get("/api/v1/commands")
async def commands(session=Depends(current_session)):
    return {"commands": public_commands()}


@app.post("/api/v1/commands/{command_id}/runs", status_code=202)
async def start_run(command_id: str, payload: RunRequest, request: Request, session=Depends(current_session)):
    require_same_origin(request)
    command = get_command(command_id)
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    if app.state.executor_busy:
        raise HTTPException(status_code=409, detail="Another command is already running")
    idempotency_key = request.headers.get("Idempotency-Key", "")
    if len(idempotency_key) < 8 or len(idempotency_key) > 128:
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key header is required")
    existing = storage.get_run_by_idempotency(idempotency_key)
    if existing:
        return {"run": run_json(existing)}
    run_id = "run_" + uuid.uuid4().hex[:20]
    created = time.time()
    storage.create_run({"id": run_id, "command_id": command.id, "source": payload.source,
                        "status": "queued", "created_at": created, "idempotency_key": idempotency_key})
    storage.audit("command.started", session["device_id"], command.id)
    app.state.executor_busy = True

    async def task():
        try:
            await execute(run_id, command, hub.publish)
            row = storage.get_run(run_id)
            storage.audit("command.finished", session["device_id"], command.id + ":" + row["status"])
        finally:
            app.state.executor_busy = False

    asyncio.create_task(task())
    await hub.publish({"type": "run.updated", "run": {"id": run_id, "status": "queued"}})
    return {"run": {"id": run_id, "command_id": command.id, "status": "queued", "created_at": created}}


@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: str, session=Depends(current_session)):
    row = storage.get_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run_json(row)}


@app.get("/api/v1/runs")
async def recent_runs(limit: int = 20, session=Depends(current_session)):
    return {"runs": [run_json(row) for row in storage.list_runs(limit)]}


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get(COOKIE_NAME)
    if not token or not storage.get_session(digest(token), time.time()):
        await websocket.close(code=4401)
        return
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host", "")
    if origin:
        parsed = urlparse(origin)
        if parsed.netloc != host or parsed.scheme not in {"http", "https"}:
            await websocket.close(code=4403)
            return
    queue = await hub.connect(websocket)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25)
                await websocket.send_json(event)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "server.heartbeat", "at": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(queue)


@app.get("/", include_in_schema=False)
async def index():
    path = frontend_dist / "index.html"
    if path.is_file():
        return FileResponse(path)
    return JSONResponse({"service": "P2C", "message": "Build frontend in frontend/ with npm run build."})


@app.get("/{path:path}", include_in_schema=False)
async def frontend_fallback(path: str):
    if path.startswith("api/") or path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not found")
    index_path = frontend_dist / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend is not built")
