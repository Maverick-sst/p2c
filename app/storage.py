"""SQLite persistence for one local P2C process."""
import sqlite3
import time
from contextlib import contextmanager
from app.config import DB_PATH


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def connection():
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connection() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS pairing_codes (
            code_hash TEXT PRIMARY KEY, expires_at REAL NOT NULL, consumed_at REAL
        );
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, paired_at REAL NOT NULL, revoked_at REAL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, device_id TEXT NOT NULL REFERENCES devices(id),
            created_at REAL NOT NULL, expires_at REAL NOT NULL, revoked_at REAL
        );
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, command_id TEXT NOT NULL, source TEXT NOT NULL,
            status TEXT NOT NULL, idempotency_key TEXT UNIQUE, exit_code INTEGER, output TEXT NOT NULL DEFAULT '',
            output_truncated INTEGER NOT NULL DEFAULT 0, duration_ms INTEGER,
            created_at REAL NOT NULL, finished_at REAL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
            device_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
        CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
        """)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(runs)")}
        if "idempotency_key" not in columns:
            db.execute("ALTER TABLE runs ADD COLUMN idempotency_key TEXT")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_idempotency ON runs(idempotency_key)")


def recover_stale_runs():
    with connection() as db:
        db.execute(
            "UPDATE runs SET status='failed', output='Service restarted before completion', finished_at=? "
            "WHERE status IN ('queued','running')", (time.time(),)
        )


def audit(event, device_id=None, detail=""):
    with connection() as db:
        db.execute("INSERT INTO audit_events(at,device_id,event,detail) VALUES(?,?,?,?)",
                   (time.time(), device_id, event, detail[:240]))


def create_pairing_code(code_hash, expires_at):
    with connection() as db:
        db.execute("UPDATE pairing_codes SET consumed_at=COALESCE(consumed_at,?)", (time.time(),))
        db.execute("INSERT INTO pairing_codes(code_hash,expires_at) VALUES(?,?)", (code_hash, expires_at))


def claim_pairing_code(code_hash, device_id, device_name, now, token_hash, session_expires):
    with connection() as db:
        cursor = db.execute(
            "UPDATE pairing_codes SET consumed_at=? "
            "WHERE code_hash=? AND consumed_at IS NULL AND expires_at>?",
            (now, code_hash, now)
        )
        if cursor.rowcount != 1:
            return False
        db.execute("INSERT INTO devices(id,name,paired_at) VALUES(?,?,?)", (device_id, device_name, now))
        db.execute("INSERT INTO sessions(token_hash,device_id,created_at,expires_at) VALUES(?,?,?,?)",
                   (token_hash, device_id, now, session_expires))
        db.execute("INSERT INTO audit_events(at,device_id,event,detail) VALUES(?,?,?,?)",
                   (now, device_id, "device.paired", "Phone paired locally"))
        return True


def get_session(token_hash, now):
    with connection() as db:
        row = db.execute("""
            SELECT s.device_id,s.expires_at,d.name FROM sessions s
            JOIN devices d ON d.id=s.device_id
            WHERE s.token_hash=? AND s.revoked_at IS NULL AND d.revoked_at IS NULL AND s.expires_at>?
        """, (token_hash, now)).fetchone()
        return dict(row) if row else None


def revoke_session(token_hash, now):
    with connection() as db:
        db.execute("UPDATE sessions SET revoked_at=? WHERE token_hash=?", (now, token_hash))


def revoke_all_devices(now):
    with connection() as db:
        db.execute("UPDATE devices SET revoked_at=? WHERE revoked_at IS NULL", (now,))
        cursor = db.execute("UPDATE sessions SET revoked_at=? WHERE revoked_at IS NULL", (now,))
        return cursor.rowcount


def create_run(run):
    run.setdefault("idempotency_key", None)
    with connection() as db:
        db.execute(
            "INSERT INTO runs(id,command_id,source,status,created_at,idempotency_key) "
            "VALUES(:id,:command_id,:source,:status,:created_at,:idempotency_key)", run
        )


def get_run_by_idempotency(key):
    with connection() as db:
        row = db.execute("SELECT * FROM runs WHERE idempotency_key=?", (key,)).fetchone()
        return dict(row) if row else None


def update_run(run_id, **fields):
    allowed = {"status", "exit_code", "output", "output_truncated", "duration_ms", "finished_at"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if fields:
        clause = ", ".join(k + "=?" for k in fields)
        with connection() as db:
            db.execute("UPDATE runs SET " + clause + " WHERE id=?", (*fields.values(), run_id))


def get_run(run_id):
    with connection() as db:
        row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None


def list_runs(limit=20):
    with connection() as db:
        rows = db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                          (max(1, min(limit, 50)),)).fetchall()
        return [dict(row) for row in rows]
