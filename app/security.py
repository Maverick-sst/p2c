"""Small security primitives; production deployments should use shared storage."""
from __future__ import annotations

import hmac
import time
from collections import defaultdict
from typing import Mapping

from twilio.request_validator import RequestValidator


class CallSecurity:
    def __init__(self, auth_token: str, allowed_phone: str, access_pin: str,
                 max_pin_attempts: int = 5, session_ttl_seconds: int = 300):
        self.validator = RequestValidator(auth_token)
        self.allowed_phone = allowed_phone
        self.access_pin = access_pin
        self.max_pin_attempts = max_pin_attempts
        self.session_ttl_seconds = session_ttl_seconds
        self.sessions: dict[str, dict] = {}
        self.pin_attempts: dict[str, int] = defaultdict(int)

    def valid_twilio_signature(self, url: str, params: Mapping[str, str],
                                signature: str | None) -> bool:
        if not signature:
            return False
        return self.validator.validate(url, params, signature)

    def caller_allowed(self, caller: str | None) -> bool:
        return bool(caller) and hmac.compare_digest(caller, self.allowed_phone)

    def verify_pin(self, supplied: str, caller: str) -> bool:
        if self.pin_attempts[caller] >= self.max_pin_attempts:
            return False
        valid = hmac.compare_digest(supplied, self.access_pin)
        if valid:
            self.pin_attempts.pop(caller, None)
        else:
            self.pin_attempts[caller] += 1
        return valid

    def create_session(self, call_sid: str) -> None:
        self.sessions[call_sid] = {
            "authenticated": False,
            "created_at": time.monotonic(),
        }

    def is_authenticated(self, call_sid: str) -> bool:
        session = self.sessions.get(call_sid)
        if not session:
            return False
        if time.monotonic() - session["created_at"] > self.session_ttl_seconds:
            self.sessions.pop(call_sid, None)
            return False
        return bool(session["authenticated"])

    def authenticate_session(self, call_sid: str) -> None:
        if call_sid in self.sessions:
            self.sessions[call_sid]["authenticated"] = True

    def close_session(self, call_sid: str) -> None:
        self.sessions.pop(call_sid, None)
