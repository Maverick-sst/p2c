# P2C — Phone-to-Computer

Control a small, explicitly allowlisted set of local macOS tasks by calling a Twilio Voice number and entering DTMF digits.

## Architecture

Phone call → Twilio Programmable Voice → HTTPS tunnel (ngrok during development) → FastAPI on your Mac → authenticated call session → allowlisted Python script.

The Mac runs the webhook service locally and exposes it only through the tunnel. No arbitrary shell commands are accepted, and no public endpoint accepts a command string.

## Status

This repository contains the implementation scaffold and automated tests. Live telephony, number reachability from India, Twilio credentials, and macOS runtime behavior must be verified by the owner.

## Quick start

1. Use Python 3.11 or newer.
2. Create a virtual environment and install dependencies from requirements.txt.
3. Copy .env.example to .env and fill in Twilio credentials, your E.164 caller number, a strong PIN, and the public HTTPS tunnel URL.
4. Start the app with make run.
5. Start ngrok with ngrok http 8000.
6. Configure the Twilio number's incoming Voice webhook to https://<your-tunnel>/voice using HTTP POST.
7. Call the Twilio number, enter your PIN, then choose an allowlisted task.

See docs/TWILIO_SETUP.md, docs/SECURITY.md, and docs/MACOS_SETUP.md.

## Important

- Twilio does not currently offer local or mobile Indian numbers. You need a supported international voice number, and you must test whether your Indian carrier can reach it (international dialing/ISD may need to be enabled). Number availability and inbound reachability are separate checks.
- Do not commit .env or share your Auth Token.
- The in-memory call-session store is intended for a single local process/MVP. Do not run multiple workers or use this as a production remote administration service.
- Only scripts explicitly registered in app/commands.py can run. Never add an arbitrary shell-command endpoint.
- The app binds to 127.0.0.1; expose it through a narrowly scoped HTTPS tunnel, not a router port-forward.

## Commands

| Key | Task |
|---|---|
| 1 | System summary |
| 2 | Disk usage |
| 3 | Network summary |
| 9 | End call |

## Development

    make install
    make test
    make run

The test suite validates command allowlisting, caller/PIN checks, and basic application behavior. It does not replace a live Twilio call test.