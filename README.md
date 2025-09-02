# kommo-lang-select

Background worker that listens to Firebase Realtime Database changes and logs events.

## Features

- Connects to Firebase Realtime Database via Firebase Admin SDK
- Auth using Google service account JSON file
- Logs all insert/update events to console (no HTTP server)
- Real-time event listening with automatic reconnection
- Typed config via environment variables

## Project layout

- `src/kommo_lang_select/`: package source
- `src/kommo_lang_select/app.py`: app entry and main loop
- `src/kommo_lang_select/firebase_admin_listener.py`: Firebase Admin SDK listener for RTDB
- `src/kommo_lang_select/config.py`: env config via Pydantic
- `src/kommo_lang_select/logging_setup.py`: logging config

## Requirements

- Python 3.9+

## Setup

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

2. Configure environment:

- Copy `.env.example` to `.env` and fill values.
- Or set environment variables directly.

Required:

- `FIREBASE_DATABASE_URL`: like `https://<project-id>-default-rtdb.firebaseio.com`
- `GOOGLE_SERVICE_ACCOUNT_FILE`: path to Firebase service account JSON file

Optional:

- `FIREBASE_PATH` (default `/`)
- `LOG_LEVEL` (default `INFO`)
- `LOG_JSON` (`1` to enable JSON-like logs)

## Run

```bash
# Load env vars (if using .env)
export $(grep -v '^#' .env | xargs) 2>/dev/null || true

# Run
python -m kommo_lang_select
# Or the console script
kommo-lang-select
```

You should see logs like:

```
INFO | Connected to Firebase stream
INFO | Event | event=child_added path=/some/path data={...}
```

## Notes

- Ensure your service account has the `Firebase Realtime Database Editor` role.
- Firebase Realtime Database must be enabled in your Firebase project.
- This app does not expose any HTTP endpoint; it's a background listener.

## Next steps (optional)

- Add structured logging library (e.g., `structlog`)
- Add unit/integration tests for the listener
- Add processing pipeline for specific events
