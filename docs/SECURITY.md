# P2C local security model

## Threat model

P2C is a single-user local-network convenience tool. It is not an internet-facing remote administration service. The main risks are an untrusted device on the same LAN, a stolen paired phone, accidental command expansion, and sensitive diagnostic output.

## Controls

- Pairing code is generated on the Mac, has a short expiry, is one-time and stored only as a SHA-256 digest.
- Browser sessions use high-entropy random tokens. Only token digests are stored in SQLite.
- Session cookies are HttpOnly and SameSite=Strict; enable Secure when using local HTTPS.
- Pairing attempts are rate-limited per source IP in the running process.
- Every API and WebSocket connection requires a valid paired session.
- State-changing requests validate same-origin when the browser supplies an Origin header.
- The WebSocket validates its Origin and authenticates using the session cookie.
- Commands resolve only through a fixed server-side registry. No client-supplied executable, path, shell string or arbitrary arguments are accepted.
- The executor uses create_subprocess_exec, a fixed Python interpreter, fixed working directory, restricted environment, per-command timeout and bounded returned output.
- SQLite records command runs and audit events.
- Only read-only system, disk and network diagnostics are enabled.

## Operational rules

1. Use LAN mode only on a trusted private network.
2. Never port-forward the P2C port or expose it through a public tunnel.
3. Plain HTTP on a LAN is not encrypted. Do not use public Wi-Fi. Local HTTPS is required before broader deployment.
4. Set P2C_COOKIE_SECURE=1 when serving over HTTPS.
5. Revoke devices with python -m app.cli revoke-all if a phone is lost.
6. Keep the Mac account non-admin for routine operation where practical.
7. Do not add destructive commands or arbitrary terminal access to the MVP.
8. Keep Uvicorn to one worker; the WebSocket hub and execution lock are process-local.

## Known MVP limitations

- The per-IP pairing throttle is in-memory and resets on restart.
- Session expiry is enforced on each request, but there is no background cleanup job.
- A command is single-flight and the current run manager is in-process. A service restart marks unfinished runs failed.
- Output is capped after process completion; the three built-in scripts are small, bounded diagnostics. Do not register untrusted or high-output scripts.
- Plain LAN HTTP exposes session cookies to network observers. Local HTTPS and trusted certificate setup remain deployment work.
- The first release does not implement multi-user roles, internet access, remote wake, or cellular telephony.
