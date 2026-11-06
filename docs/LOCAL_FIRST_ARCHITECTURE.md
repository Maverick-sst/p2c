# P2C v2 — Local-first hybrid architecture

## Product decision

P2C v2 is a local-network remote control for a Mac. It does not receive cellular calls and does not depend on Twilio, a SIP trunk, a DID, Asterisk, a VPS, or a cloud API.

The Android phone opens a responsive web interface hosted by the Mac. The interface combines:
- a dashboard of named, allowlisted actions;
- a two-digit command keypad, with `#` to submit and `*` to clear;
- live execution state and bounded output.

The keypad preserves the fast command-code interaction from the original DTMF concept. These are application key presses, not telephone DTMF tones.

## Runtime topology

```text
Android browser / installable web app
            |
            | same Wi-Fi or phone hotspot
            | HTTP for initial LAN prototype; trusted local HTTPS before
            | enabling service-worker/PWA features or using untrusted networks
            v
Mac: one FastAPI + Uvicorn process
  - serves the built frontend from the same origin
  - pairing and session endpoints
  - command catalogue and run API
  - authenticated WebSocket event channel
            |
            v
Command registry -> bounded executor -> existing scripts/
            |
            v
SQLite state + audit history
```

No inbound internet exposure is required. Bind to the Mac's LAN interface only when the user explicitly starts LAN mode; otherwise bind to loopback. Never add router port forwarding or a public tunnel as part of the default setup.

## UI contract

### Shared shell

- Header: P2C mark, Mac device name, connection indicator.
- Connection states: Disconnected, Connecting, Connected, Reconnecting.
- Main content: Dashboard and Keypad tabs or a compact segmented switch.
- Activity panel: latest run, timestamp, duration, status and output preview.
- No controls for arbitrary shell commands, filesystem paths or free-form script arguments.

### Dashboard

Initial read-only cards:
- System status — command `system.status`, keypad code `01`.
- Disk usage — command `system.disk`, keypad code `02`.
- Network status — command `system.network`, keypad code `03`.

A card displays a concise description and last-run status. Tapping a card submits that registered command. While a run is active, disable duplicate taps for that command and show progress. The result view shows a bounded output block, exit status and duration.

### Keypad

- Digits 0–9 append to a maximum two-character buffer.
- `*` clears the buffer.
- `#` submits the matching registered code.
- A valid code resolves to the same command registry as a dashboard card.
- Unknown or incomplete codes are rejected locally and by the API.
- Never interpret keypad content as a shell command or a path.

### Responsive and accessibility requirements

- Mobile-first layout, comfortable touch targets (at least 44 CSS px).
- Visible focus state and keyboard navigation.
- Status is conveyed with text and icon, not color alone.
- Respect reduced-motion preferences.
- Do not rely on service workers for basic operation. PWA installation/offline shell can be added after local HTTPS is solved.

## Service boundaries

### FastAPI application
Owns HTTP routing, static frontend hosting, validation, auth dependencies, WebSocket authentication and lifecycle.

### Pairing and sessions
Issues short-lived one-time pairing challenges and revocable device sessions. The pairing secret is generated on the Mac and displayed locally. Store only a hash of the challenge and session-token hashes.

### Command registry
Maps stable command IDs and keypad codes to fixed server-side handlers. It is the sole authority for what can execute.

### Executor
Runs registered Python handlers only. Apply per-command timeout, output-size limit, concurrency limit and structured result handling. Do not use `shell=True`; do not accept caller-provided executable names or arguments.

### Storage
SQLite stores paired devices, session metadata, command runs and audit events. Use parameterized queries and schema migrations.

### Frontend
React + Vite, built to static assets and served by FastAPI from the same origin. Same-origin hosting avoids permissive CORS configuration.

## Local network and transport

For the first functional prototype, support:
1. Mac and phone on the same trusted Wi-Fi network.
2. Mac-hosted hotspot or phone hotspot, if the phone can reach the Mac's LAN address.

Show the exact LAN URL and pairing challenge in the Mac terminal. Provide a CLI command to print the URL again.

LAN HTTP is acceptable only as a controlled development step on a trusted private network. Before enabling PWA service workers or using the system on networks you do not trust, add local HTTPS with a locally trusted certificate (for example, a user-installed local CA). Do not silently fall back to public tunnels or cloud relays.

## Initial command policy

Only read-only diagnostics are in scope:
- `system.status` -> existing system status script
- `system.disk` -> existing disk status script
- `system.network` -> existing network status script

Process listing may be added after reviewing the output for sensitive process arguments. No shutdown, reboot, deletion, arbitrary terminal, file upload, or privileged operation in v2 MVP.

## Operational constraints

- One Uvicorn worker for the initial local service.
- Mac must be awake and the service running.
- The phone and Mac must have LAN reachability; internet access is not required.
- The Mac's IP may change. Provide a discoverable URL/CLI status command; do not assume a fixed address.
- The app is a convenience remote, not a hardened remote-administration product.
