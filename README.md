# P2C — Phone-to-Computer (Local-first v2)

P2C is a self-hosted remote control for your Mac. Open its web interface on your Android phone over the same trusted local network, then launch predefined diagnostic tasks from a dashboard or numeric keypad.

**No Twilio, SIP trunk, Asterisk, VPS, cloud API, API key or recurring subscription.**

P2C v2 does not receive ordinary cellular phone calls. Cellular/PSTN access requires a carrier connection or telephony hardware, which conflicts with the zero-subscription/no-hardware requirement. The keypad is an in-app command keypad, not telephone DTMF.

## Features

- Hybrid dashboard and two-digit keypad.
- One-time pairing code displayed on the Mac.
- Revocable, expiring browser sessions.
- Authenticated HTTP API and WebSocket run updates.
- SQLite run history and audit events.
- Static allowlist of read-only diagnostic scripts.
- Local-only operation; no public tunnel or port forwarding.

## Requirements

- macOS with Python 3.11+.
- Node.js 20+ and npm, only to build the frontend.
- Android phone or another browser on the same trusted Wi-Fi network.
- No external service or paid account.

## Quick start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
make install
make frontend-install
make frontend-build
```

Create a one-time pairing code in one terminal:

```bash
make pair
```

Start the server in another terminal:

```bash
make run-lan
```

The terminal prints the local URL, typically `http://<mac-lan-ip>:8000`. Open that address on the phone and enter the pairing code. The code expires quickly and can be used once.

For Mac-only browser testing, use `make run` and open `http://127.0.0.1:8000`.

## Using P2C

- Dashboard: tap System status, Disk usage or Network status.
- Keypad: enter `01`, `02` or `03`, then press `#`.
- Press `*` to clear the keypad.
- View execution status, output and recent history in the app.

## Security and network limitations

- LAN mode binds to the Mac's primary LAN address, not all interfaces.
- Use only on a trusted private network. Plain HTTP does not encrypt session cookies; anyone able to observe traffic on that network may be able to steal a session.
- Do not use public Wi-Fi. Do not configure router port forwarding or expose port 8000 to the internet.
- The initial MVP uses a same-origin HttpOnly, SameSite=Strict cookie. Configure local HTTPS and `P2C_COOKIE_SECURE=1` before using it on less-trusted networks.
- Pairing code is one-time and short-lived. Use `make pair` to rotate it.
- Commands run as your logged-in macOS user. Only three read-only commands are enabled. Do not add arbitrary shell execution.
- The app is single-user and single-process. Run one Uvicorn worker.
- Mac must remain awake and the service running. Phone and Mac need LAN connectivity.

## Local administration

Revoke every paired device:

```bash
python3 -m app.cli revoke-all
```

Create a new pairing code:

```bash
python3 -m app.cli pair
```

## Development

```bash
make test
make lint
```

Frontend source is in `frontend/`; run `npm run dev -- --host 127.0.0.1` there for UI work. The production build is served by FastAPI from `frontend/dist`.

## Project docs

- [Local-first architecture](docs/LOCAL_FIRST_ARCHITECTURE.md)
- [API contracts](docs/API_CONTRACTS.md)
- [Migration plan](docs/MIGRATION_PLAN.md)
- [Security model](docs/SECURITY.md)
- [macOS setup](docs/MACOS_SETUP.md)
