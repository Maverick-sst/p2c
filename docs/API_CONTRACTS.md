# P2C v2 — HTTP and WebSocket contracts

Base path: `/api/v1`. JSON uses UTF-8. The frontend is served by the same FastAPI origin.

## Conventions

- Stable identifiers use lowercase dotted names, e.g. `system.status`.
- Timestamps are ISO-8601 UTC strings.
- All authenticated routes require a valid P2C device session.
- The browser session is delivered as a Secure, HttpOnly, SameSite=Strict cookie when local HTTPS is configured. During LAN-HTTP development, document the weaker transport explicitly and never reuse the session on another network.
- Never put bearer tokens in URLs, query strings, logs or WebSocket query parameters.
- Request bodies are schema-validated; unknown fields are rejected.
- Mutating requests accept an `Idempotency-Key` header.

## Response envelope

Successful responses use the resource shape shown by each endpoint. Errors use:

```json
{
  "error": {
    "code": "COMMAND_NOT_FOUND",
    "message": "No command is registered for that identifier.",
    "request_id": "req_..."
  }
}
```

Do not return stack traces, filesystem paths, environment variables or secrets to the phone.

## Pairing and session lifecycle

### GET /api/v1/health

Unauthenticated. Returns service availability without disclosing secrets.

Response:
```json
{ "status": "ok", "service": "p2c", "version": "0.2.0" }
```

### GET /api/v1/pairing/status

Unauthenticated, local-network only. Indicates whether pairing is currently open; never returns the pairing code or its hash.

Response:
```json
{ "pairing_open": true, "expires_at": "2026-11-06T12:00:00Z" }
```

### POST /api/v1/pairing/claim

Consumes a one-time code displayed by the Mac CLI. Rate-limited. A successful claim creates a paired device and a browser session.

Request:
```json
{ "pairing_code": "one-time-code", "device_name": "Android phone" }
```

Response:
```json
{
  "device": { "id": "dev_...", "name": "Android phone", "paired_at": "2026-11-06T12:00:00Z" },
  "session": { "expires_at": "2026-11-06T20:00:00Z" }
}
```

The server sets the session cookie; the raw session secret is not returned in JSON. Pairing codes expire quickly, are single-use, stored hashed, and are invalidated after a small number of failed attempts. A CLI command can revoke all devices.

### POST /api/v1/auth/logout

Authenticated. Revokes the current session and clears the cookie.

### GET /api/v1/device

Authenticated. Returns the paired device identity and server status.

## Command catalogue

### GET /api/v1/commands

Authenticated. Returns only enabled, user-visible commands.

Response:
```json
{
  "commands": [
    {
      "id": "system.status",
      "key": "01",
      "label": "System status",
      "description": "CPU, memory and operating-system summary",
      "risk": "read_only",
      "enabled": true,
      "timeout_seconds": 12
    }
  ]
}
```

The server owns the catalogue. The client must not submit executable names, script paths or shell text.

## Command execution

### POST /api/v1/commands/{command_id}/runs

Authenticated. Starts one registered command.

Headers:
- `Idempotency-Key: <random-client-generated-value>`

Request:
```json
{ "source": "dashboard" }
```

For keypad submissions, the UI resolves the two-digit code using the server-provided command catalogue, then submits the stable command ID. The API revalidates that ID against the server registry. Never accept a raw code as an executable instruction.

Response (202 Accepted):
```json
{
  "run": {
    "id": "run_...",
    "command_id": "system.status",
    "status": "queued",
    "created_at": "2026-11-06T12:00:00Z"
  }
}
```

Possible statuses: `queued`, `running`, `succeeded`, `failed`, `timed_out`, `cancelled`.

### GET /api/v1/runs/{run_id}

Authenticated. Returns current state and, when finished, bounded output.

Response:
```json
{
  "run": {
    "id": "run_...",
    "command_id": "system.status",
    "status": "succeeded",
    "exit_code": 0,
    "output": "…",
    "output_truncated": false,
    "duration_ms": 184,
    "created_at": "2026-11-06T12:00:00Z",
    "finished_at": "2026-11-06T12:00:01Z"
  }
}
```

Output is capped server-side (initial limit: 8 KiB). Do not persist unlimited stdout/stderr.

### GET /api/v1/runs?limit=20

Authenticated. Returns the most recent run summaries, with a hard maximum limit of 50.

## WebSocket

### WS /api/v1/ws

Authenticated using the same-origin session cookie. Reject unauthenticated connections before accepting them. Enforce an origin allowlist matching the local app origin.

Server events:
```json
{ "type": "run.updated", "run": { "id": "run_...", "status": "running" } }
{ "type": "run.completed", "run": { "id": "run_...", "status": "succeeded", "duration_ms": 184 } }
{ "type": "server.heartbeat", "at": "2026-11-06T12:00:00Z" }
```

Client messages are limited to a heartbeat acknowledgement in the MVP. Commands are submitted through HTTP, not arbitrary WebSocket payloads. The client reconnects with bounded exponential backoff and refreshes run state through HTTP after reconnecting.

## Keypad mapping

| Code | Command ID | Label |
|---|---|---|
| 01 | system.status | System status |
| 02 | system.disk | Disk usage |
| 03 | system.network | Network status |

The keypad UI uses `*` to clear and `#` to submit. These characters are UI controls and are not sent as command IDs.

## Validation and status codes

- `200`: read succeeded / logout succeeded.
- `202`: run accepted.
- `400`: malformed request or invalid keypad input.
- `401`: missing, expired or revoked session.
- `403`: pairing or command policy denied.
- `404`: unknown command or run.
- `409`: duplicate active run or idempotency conflict.
- `422`: schema validation failure.
- `429`: pairing/authentication/command rate limit.
- `503`: executor unavailable or service shutting down.

## Security invariants

1. No endpoint accepts a shell command, executable, script path or arbitrary argument list.
2. Dashboard and keypad resolve to the same server-side command registry.
3. Every run is tied to a paired device/session and has an audit record.
4. Pairing codes are one-time, short-lived and rate-limited.
5. Session secrets are stored hashed server-side and are revocable.
6. WebSocket is authenticated and origin-checked.
7. Executor uses argument arrays with `shell=False`, fixed working directory, timeout, output cap and concurrency limit.
8. All initial commands are read-only and run as the logged-in macOS user.
