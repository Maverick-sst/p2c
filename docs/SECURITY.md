# Security model and limitations

- The app binds to 127.0.0.1. Do not bind it to 0.0.0.0 or create router port forwards for this MVP.
- Twilio's X-Twilio-Signature is validated against the externally visible HTTPS URL and submitted form parameters.
- The caller number must exactly match ALLOWED_PHONE and the caller must enter ACCESS_PIN.
- The PIN is compared in constant time and failed attempts are limited in process memory.
- Call sessions expire and are tied to Twilio CallSid.
- DTMF keys map to a static allowlist. No caller-supplied command, path, argument, or shell expression is accepted.
- Scripts execute with the permissions of the macOS user running the app. Keep that account unprivileged and avoid adding destructive tasks.
- Keep .env private. Rotate the Twilio Auth Token if it is exposed.
- Use a long random PIN dedicated to this project. Do not use a banking, Apple ID, or device unlock PIN.

## MVP limitations

The session and PIN attempt stores are in-memory. A restart clears them, and multiple Uvicorn workers would not share them. Run one worker only. Before production or unattended use, move state to Redis/SQLite with atomic rate limits, add request replay protection and audit persistence, and consider a dedicated least-privilege macOS account.

Caller ID is not strong authentication by itself. The PIN is required, but DTMF is not end-to-end encrypted as a secret channel. Do not use this system for sensitive or destructive operations.
