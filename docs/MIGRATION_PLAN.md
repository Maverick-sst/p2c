# P2C v2 — Repository migration and implementation status

## Current implementation

The local-first v2 application is now implemented on this branch. The original Twilio branch and draft PR #1 remain preserved as a historical prototype.

Implemented:
- FastAPI local API and static frontend hosting.
- One-time pairing code generated from the Mac CLI.
- High-entropy browser sessions stored as SHA-256 token digests.
- SQLite persistence for devices, sessions, runs and audit events.
- Fixed registry for three read-only commands with keypad codes 01, 02 and 03.
- Bounded subprocess execution with fixed executable, fixed script paths, timeout and output cap.
- Authenticated HTTP endpoints and cookie-authenticated, origin-checked WebSocket events.
- React/Vite hybrid dashboard and keypad.
- Local server CLI, trusted-LAN mode, setup documentation and backend/frontend CI jobs.

Not yet verified:
- Python tests have been authored but not executed in a local runtime in this session.
- npm dependency installation and Vite production build have not been executed here.
- The actual Mac and Android phone have not been paired or smoke-tested.
- Local HTTPS and a macOS LaunchAgent remain deployment follow-ups.

## Implemented phases

### Phase 1 — Command domain
- [x] Stable command IDs and two-digit keypad codes.
- [x] Existing system, disk and network diagnostic scripts retained.
- [x] Unknown command IDs and codes rejected.
- [x] No client-provided executable path or shell text.

### Phase 2 — Pairing and authentication
- [x] CLI generates a short-lived one-time pairing code.
- [x] Pairing code is stored as a digest and consumed once.
- [x] Browser session is high-entropy and stored as a digest.
- [x] Session expiry and logout revocation.
- [x] SameSite=Strict, HttpOnly cookie and same-origin validation.
- [x] CLI can revoke all paired devices.

### Phase 3 — API and execution
- [x] Versioned health, pairing, device, command, run and logout endpoints.
- [x] SQLite run and audit persistence.
- [x] Single-flight executor, fixed registry, timeout and output cap.
- [x] Authenticated WebSocket status events.
- [x] Restart recovery marks interrupted runs failed.

### Phase 4 — Hybrid frontend
- [x] React/Vite dashboard.
- [x] Numeric keypad: two digits, * clear, # submit.
- [x] Dashboard and keypad share the same server command catalogue.
- [x] Connection status, run output, recent activity and reconnect handling.
- [x] Mobile-first responsive styling.

### Phase 5 — Local networking
- [x] Loopback mode by default.
- [x] Explicit LAN mode binds to the primary LAN address.
- [x] Pairing instructions and trusted-network warning.
- [ ] Local HTTPS certificate provisioning and Secure cookie configuration.
- [ ] Verify Android hotspot routing and macOS firewall behavior.

### Phase 6 — Telephony removal
- [x] Twilio dependency removed from requirements.
- [x] Twilio-only configuration removed from the active application.
- [x] README and macOS setup rewritten for local-first use.
- [x] Remove obsolete Twilio-only source/docs from the active branch.
- [ ] Confirm backend tests and frontend build pass in CI (workflow configured; result not yet available).
- [ ] Complete physical Mac + Android smoke test.

## Repository layout

```text
app/
  auth.py
  cli.py
  commands.py
  config.py
  executor.py
  main.py
  realtime.py
  storage.py
scripts/
  system_status.py
  disk_status.py
  network_status.py
frontend/
  index.html
  package.json
  vite.config.js
  src/main.jsx
  src/style.css
tests/
  test_app.py
  test_api.py
  test_commands.py
  test_security.py
  test_storage.py
docs/
  LOCAL_FIRST_ARCHITECTURE.md
  API_CONTRACTS.md
  MIGRATION_PLAN.md
  SECURITY.md
  MACOS_SETUP.md
```

## Local run instructions

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make frontend-install
make frontend-build
make pair
make run-lan
```

Run `make pair` and `make run-lan` in separate terminals. Open the printed LAN URL on the phone and enter the pairing code.

## Known limitations

- No ordinary cellular dialer/PSTN call support. That requires a carrier or telephony hardware.
- Plain LAN HTTP is not encrypted. Use only a trusted private network until local HTTPS is configured.
- Single user, one Uvicorn worker, one command at a time.
- Mac must be awake and connected to the same LAN as the phone.
- No arbitrary terminal, destructive commands, internet relay or remote access.
