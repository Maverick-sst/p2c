# P2C v2 — Repository migration plan

## Starting point

Migration branch is based on `feat/phone-to-computer-mvp`, preserving the existing draft PR and Twilio implementation.

Current implementation facts:
- `app/main.py` contains Twilio Voice webhook routes: `/voice`, `/verify-pin`, `/execute`.
- `app/config.py` requires Twilio Auth Token, public HTTPS base URL, allowed caller number and access PIN.
- `app/security.py` validates Twilio signatures, caller allowlisting, PIN attempts and in-memory call sessions.
- `app/commands.py` defines a useful static command allowlist.
- `scripts/system_status.py`, `scripts/disk_status.py`, and `scripts/network_status.py` are reusable starting points.
- Existing tests cover the Twilio flow and command allowlist; they need to be replaced or refactored for local device sessions and HTTP/WebSocket execution.
- `requirements.txt` includes the Twilio SDK, which is not needed in the local-first target.

## Migration strategy

Do not rewrite the existing Twilio branch in place. Build v2 on `feat/local-first-hybrid`. Keep the old branch and PR #1 available as a historical implementation until v2 has been tested on the actual Mac and phone.

### Phase 0 — Documentation and contracts (current)

- [x] Confirm hybrid dashboard + keypad UX.
- [x] Define local-only runtime topology.
- [x] Define HTTP and WebSocket API contracts.
- [x] Record repository migration sequence.
- [ ] Review contracts before implementation.

### Phase 1 — Extract the command domain

1. Refactor `app/commands.py` into a server-owned registry keyed by stable IDs and keypad codes.
2. Preserve existing script implementations and their read-only behavior.
3. Replace the Twilio-specific `Command(key, label, script)` model with explicit metadata: ID, key, label, description, handler, timeout and risk classification.
4. Add tests for every mapping and rejection of unknown IDs/codes.
5. Do not add arbitrary command strings or client-supplied script paths.

Acceptance:
- The three original diagnostic tasks still run from the registry.
- No Twilio imports are needed by the command domain.

### Phase 2 — Replace call security with local pairing

1. Remove `CallSecurity` and create pairing/session services.
2. Generate a short-lived, one-time pairing code from a local CLI command.
3. Store only hashes of pairing challenges and session secrets.
4. Add paired-device records, expiry, revocation and rate limits.
5. Use same-origin HttpOnly cookies for browser sessions; use Secure cookies once local HTTPS is configured.
6. Add CLI commands to show the local URL and revoke paired devices.

Acceptance:
- A phone can pair only with a code displayed by the Mac.
- A consumed/expired code cannot be reused.
- Revoked and expired sessions cannot call protected APIs.

### Phase 3 — Build the local API and execution lifecycle

1. Replace Twilio routes with `/api/v1` endpoints from `docs/API_CONTRACTS.md`.
2. Add SQLite persistence for devices, sessions, runs and audit events.
3. Add bounded executor with `shell=False`, fixed script registry, timeouts, output caps and concurrency control.
4. Add run status retrieval and idempotency handling.
5. Add authenticated WebSocket notifications; HTTP remains the command submission path.

Acceptance:
- Only registered read-only commands execute.
- Every run has an auditable lifecycle and bounded output.
- WebSocket reconnect does not lose authoritative run state.

### Phase 4 — Build the hybrid frontend

1. Add `frontend/` with React + Vite.
2. Implement dashboard cards for system, disk and network status.
3. Implement keypad with two-digit buffer, `*` clear and `#` submit.
4. Add connection indicator, run status, output viewer and recent activity.
5. Serve the production frontend build from FastAPI on the same origin.

Acceptance:
- A dashboard tile and its keypad code execute the exact same command ID.
- The UI handles disconnected, queued, running, success and error states.
- Layout is usable on a small Android screen and desktop browser.

### Phase 5 — Local networking and macOS lifecycle

1. Add explicit loopback and LAN bind modes; default to loopback until the owner enables LAN mode.
2. Print the LAN URL and pairing instructions in the terminal.
3. Document same-Wi-Fi and hotspot testing.
4. Add macOS LaunchAgent configuration after manual execution is stable.
5. Add local HTTPS with a locally trusted certificate before enabling service-worker installation or using untrusted networks.
6. Do not introduce ngrok, a public VPS, port forwarding or cloud relay.

Acceptance:
- Phone reaches Mac only on the local network.
- Service restarts cleanly and can be stopped/revoked locally.
- No external network dependency is required for core functionality.

### Phase 6 — Remove telephony dependencies and close the migration

1. Remove Twilio SDK and Twilio-only configuration.
2. Delete or archive Twilio setup docs after preserving the old branch.
3. Update README, .env.example, Makefile and CI for local-first setup.
4. Replace Twilio tests with pairing, API, executor, WebSocket and frontend tests.
5. Run the full test suite and manual phone-to-Mac smoke test.
6. Update the v2 PR description with actual validation evidence; do not claim unrun tests.

Acceptance:
- No Twilio credentials, phone-number allowlist, public callback URL or tunnel is required.
- A fresh install can pair a phone and execute the three diagnostic commands locally.
- Security review confirms there is no arbitrary shell execution path.

## Planned repository target

```text
app/
  main.py
  config.py
  api/
    health.py
    pairing.py
    commands.py
    runs.py
    websocket.py
  auth/
    pairing.py
    sessions.py
  core/
    registry.py
    executor.py
    run_manager.py
  storage/
    database.py
    models.py
scripts/
frontend/
  src/
    components/
    pages/
    services/
    hooks/
tests/
docs/
  LOCAL_FIRST_ARCHITECTURE.md
  API_CONTRACTS.md
  MIGRATION_PLAN.md
launchagent/
```

## Dependency changes

Remove:
- `twilio`

Keep initially:
- `fastapi`
- `uvicorn`
- `python-multipart` only if a remaining form endpoint requires it
- `python-dotenv`
- `psutil`
- `pytest`
- `httpx`

Add when implementation starts:
- SQLite access via Python standard library `sqlite3` initially (no ORM required for MVP).
- A maintained password/token hashing dependency only if the standard library primitives selected are insufficient; prefer standard-library `secrets` and `hashlib` for high-entropy random tokens.
- Frontend dependencies pinned through the frontend lockfile.

## Explicitly out of scope for v2 MVP

- Ordinary cellular dialer/PSTN calling.
- Twilio, SIP trunks, Asterisk, DID provisioning and GSM hardware.
- Cloud hosting, public tunnels, remote access over the internet.
- Arbitrary shell commands, remote terminal, destructive operations and privileged commands.
- Multi-user accounts or internet-facing deployment.

## Risks and decisions to resolve during implementation

- Android browser access to the Mac's LAN IP depends on Wi-Fi client isolation and hotspot routing; verify on the actual devices.
- PWA service workers require a secure context. Do not promise install/offline support over plain LAN HTTP; solve local HTTPS first.
- macOS firewall prompts and changing DHCP addresses need clear setup guidance.
- A browser session on LAN HTTP can be intercepted by someone on the same network. Keep the prototype on a trusted network and prioritize local HTTPS before broader use.
- Process information can expose command-line arguments and secrets; do not enable process listing until output is reviewed.
- SQLite is sufficient for a single-user, single-process local MVP. Keep Uvicorn at one worker until coordination is designed.
