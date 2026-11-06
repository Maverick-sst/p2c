# macOS setup

## Runtime

Use Python 3.11+ and a dedicated virtual environment. From the repository root:

    python3 -m venv .venv
    source .venv/bin/activate
    make install
    cp .env.example .env

Edit .env with your real Twilio Auth Token, public HTTPS tunnel URL, your caller ID in E.164 format, and a unique 6–8 digit PIN.

## Start manually first

    make test
    make run

In another terminal:

    ngrok http 8000

Open http://127.0.0.1:8000/health and confirm {"status":"ok","service":"p2c"}.

## LaunchAgent (optional, after manual testing)

A sample plist is provided in launchd. Replace every placeholder path and username with the actual absolute path on your Mac. Keep the environment file private. Load the LaunchAgent only after the manual app and live call test succeeds.

The sample LaunchAgent starts Uvicorn on localhost. It does not start ngrok; start and supervise the tunnel separately.
