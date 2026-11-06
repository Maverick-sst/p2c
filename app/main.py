"""Twilio Voice webhook application for the P2C local macOS agent."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.commands import get_command
from app.config import Settings
from app.security import CallSecurity

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("p2c")

settings = Settings.from_env()
security = CallSecurity(
    auth_token=settings.twilio_auth_token,
    allowed_phone=settings.allowed_phone,
    access_pin=settings.access_pin,
    max_pin_attempts=settings.max_pin_attempts,
    session_ttl_seconds=settings.session_ttl_seconds,
)

app = FastAPI(title="P2C — Phone to Computer", version="0.1.0")


def xml(response: VoiceResponse) -> Response:
    return Response(content=str(response), media_type="application/xml")


def callback_url(path: str) -> str:
    return f"{settings.public_base_url}{path}"


async def validated_form(request: Request):
    form = await request.form()
    # Twilio signs the externally visible URL, not the localhost URL behind ngrok.
    external_url = callback_url(request.url.path)
    if request.url.query:
        external_url += "?" + request.url.query
    signature = request.headers.get("X-Twilio-Signature")
    if not security.valid_twilio_signature(external_url, dict(form), signature):
        logger.warning("Rejected webhook with invalid Twilio signature")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    return form


def say(response: VoiceResponse, message: str) -> None:
    response.say(message, language=settings.voice_language)


def end_call(response: VoiceResponse, call_sid: str | None = None) -> Response:
    response.hangup()
    if call_sid:
        security.close_session(call_sid)
    return xml(response)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "p2c"}


@app.post("/voice")
async def incoming_call(request: Request):
    form = await validated_form(request)
    caller = form.get("From")
    call_sid = form.get("CallSid")
    response = VoiceResponse()

    if not security.caller_allowed(caller) or not call_sid:
        say(response, "This number is not authorized. Goodbye.")
        return end_call(response)

    security.create_session(call_sid)
    gather = Gather(
        input="dtmf",
        num_digits=6,
        timeout=8,
        action=callback_url("/verify-pin"),
        method="POST",
        action_on_empty_result=True,
    )
    say(gather, "Welcome. Please enter your six digit security PIN.")
    response.append(gather)
    say(response, "No PIN received. Goodbye.")
    return end_call(response, call_sid)


@app.post("/verify-pin")
async def verify_pin(request: Request):
    form = await validated_form(request)
    call_sid = form.get("CallSid", "")
    caller = form.get("From", "")
    digits = form.get("Digits", "")
    response = VoiceResponse()

    if not security.is_authenticated(call_sid) and call_sid not in security.sessions:
        say(response, "This call session has expired. Goodbye.")
        return end_call(response, call_sid)

    if not security.caller_allowed(caller) or not security.verify_pin(digits, caller):
        say(response, "Authentication failed. Goodbye.")
        logger.warning("PIN authentication failed for call %s", call_sid)
        return end_call(response, call_sid)

    security.authenticate_session(call_sid)
    gather = Gather(
        input="dtmf",
        num_digits=1,
        timeout=10,
        action=callback_url("/execute"),
        method="POST",
        action_on_empty_result=True,
    )
    say(
        gather,
        "Authentication successful. Press 1 for system summary. "
        "Press 2 for disk usage. Press 3 for network summary. "
        "Press 9 to end the call.",
    )
    response.append(gather)
    say(response, "No selection received. Goodbye.")
    return end_call(response, call_sid)


async def run_allowlisted_script(script: Path) -> tuple[int, str]:
    # Paths originate only from app.commands; no user-supplied shell is executed.
    if not script.is_file() or script.parent != (Path(__file__).resolve().parents[1] / "scripts"):
        raise ValueError("Script is not in the approved scripts directory")

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script),
        cwd=str(script.parent.parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=12)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise
    output = (stdout.decode(errors="replace") or stderr.decode(errors="replace")).strip()
    return process.returncode or 0, output[:1200]


@app.post("/execute")
async def execute_command(request: Request):
    form = await validated_form(request)
    call_sid = form.get("CallSid", "")
    caller = form.get("From", "")
    digit = form.get("Digits", "")
    response = VoiceResponse()

    if not security.caller_allowed(caller) or not security.is_authenticated(call_sid):
        say(response, "Authentication required. Goodbye.")
        return end_call(response, call_sid)

    if digit == "9":
        say(response, "Disconnecting. Goodbye.")
        return end_call(response, call_sid)

    command = get_command(digit)
    if command is None:
        say(response, "Invalid selection. Goodbye.")
        logger.warning("Rejected command key %r for call %s", digit, call_sid)
        return end_call(response, call_sid)

    try:
        exit_code, output = await run_allowlisted_script(command.script)
        if exit_code == 0:
            logger.info("Call %s completed task %s: %s", call_sid, command.key, output)
            say(response, f"The {command.label} task completed successfully.")
        else:
            logger.error("Task %s failed for call %s: %s", command.key, call_sid, output)
            say(response, "The task reported an error. Check the Mac logs.")
    except asyncio.TimeoutError:
        logger.error("Task %s timed out for call %s", command.key, call_sid)
        say(response, "The task timed out.")
    except Exception:
        logger.exception("Task %s failed unexpectedly", command.key)
        say(response, "The task could not be completed.")

    say(response, "Goodbye.")
    return end_call(response, call_sid)
