# macOS setup

## Requirements

- macOS
- Python 3.11+
- Node.js 20+ and npm (frontend build only)

## Install and build

```bash
git clone https://github.com/Maverick-sst/p2c.git
cd p2c
git checkout feat/local-first-hybrid
python3 -m venv .venv
source .venv/bin/activate
make install
make frontend-install
make frontend-build
```

## Pair and run

Terminal 1:

```bash
make pair
```

Terminal 2:

```bash
make run-lan
```

Open the printed local URL on your Android phone while both devices are connected to the same trusted Wi-Fi network. Enter the one-time code printed by the pairing command.

For a Mac-only smoke test, run `make run` and open `http://127.0.0.1:8000`.

## Stop and revoke

Stop the service with Ctrl+C. Revoke all paired sessions with:

```bash
python3 -m app.cli revoke-all
```

## Network troubleshooting

- Confirm phone and Mac are on the same Wi-Fi and the router does not enable client isolation.
- Check the Mac's local IP with System Settings → Network.
- macOS may ask whether Python/Uvicorn can accept incoming connections; allow it on the private network.
- A phone hotspot may isolate connected clients or prevent access to the host; test it on the actual devices.
- Do not use router port forwarding, public tunnels or public Wi-Fi.

## HTTPS and startup

The initial local prototype uses HTTP on a trusted LAN. This is not suitable for hostile networks because browser session cookies are not encrypted in transit. Add a locally trusted HTTPS certificate and set `P2C_COOKIE_SECURE=1` before using P2C outside a trusted private network.

Configure a LaunchAgent only after manual startup and phone pairing have been tested. The first release intentionally starts manually so the user can see the pairing URL and service state.
