"""Environment-backed configuration for P2C."""
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    twilio_auth_token: str
    public_base_url: str
    allowed_phone: str
    access_pin: str
    voice_language: str = "en-US"
    session_ttl_seconds: int = 300
    max_pin_attempts: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        required = ("TWILIO_AUTH_TOKEN", "PUBLIC_BASE_URL", "ALLOWED_PHONE", "ACCESS_PIN")
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise RuntimeError("Missing required environment variables: " + ", ".join(missing))

        base_url = os.environ["PUBLIC_BASE_URL"].rstrip("/")
        if not base_url.startswith("https://"):
            raise RuntimeError("PUBLIC_BASE_URL must use HTTPS")

        phone = os.environ["ALLOWED_PHONE"]
        if not phone.startswith("+") or not phone[1:].isdigit():
            raise RuntimeError("ALLOWED_PHONE must be an E.164 number")

        pin = os.environ["ACCESS_PIN"]
        if not pin.isdigit() or len(pin) != 6:
            raise RuntimeError("ACCESS_PIN must contain exactly 6 digits")

        return cls(
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            public_base_url=base_url,
            allowed_phone=phone,
            access_pin=pin,
            voice_language=os.getenv("VOICE_LANGUAGE", "en-US"),
            session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "300")),
            max_pin_attempts=int(os.getenv("MAX_PIN_ATTEMPTS", "5")),
        )
