"""One-time pairing and high-entropy browser session tokens."""
import hashlib
import secrets
import time
import uuid
from fastapi import Cookie, HTTPException, Request
from urllib.parse import urlparse
from app.config import COOKIE_NAME, COOKIE_SECURE, PAIRING_TTL_SECONDS, SESSION_TTL_SECONDS
from app import storage

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_pairing_code():
    code = "".join(secrets.choice(ALPHABET) for _ in range(10))
    expires = time.time() + PAIRING_TTL_SECONDS
    storage.create_pairing_code(digest(code), expires)
    return code, expires


def claim_pairing(code, device_name):
    if not code or len(code) > 32:
        return None
    now = time.time()
    token = secrets.token_urlsafe(32)
    device_id = "dev_" + uuid.uuid4().hex[:16]
    expires = now + SESSION_TTL_SECONDS
    ok = storage.claim_pairing_code(digest(code.strip().upper()), device_id,
                                    device_name, now, digest(token), expires)
    return (token, {"id": device_id, "name": device_name,
                    "paired_at": now, "expires_at": expires}) if ok else None


def current_session(request: Request, p2c_session: str | None = Cookie(default=None, alias=COOKIE_NAME)):
    if not p2c_session:
        raise HTTPException(status_code=401, detail="Pair this device to continue")
    session = storage.get_session(digest(p2c_session), time.time())
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    return session


def set_session_cookie(response, token):
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE,
                        samesite="strict", max_age=SESSION_TTL_SECONDS, path="/")


def clear_session_cookie(response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True,
                           secure=COOKIE_SECURE, samesite="strict")


def require_same_origin(request):
    origin = request.headers.get("origin")
    if not origin:
        return
    host = request.headers.get("host", "")
    parsed = urlparse(origin)
    if parsed.netloc != host or parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=403, detail="Cross-origin request rejected")
