# AI Coding Agent Instructions for kommo-lang-select

## General Guidelines

- **Always code with industry best practices** - follow established patterns, proper error handling, type hints, and clean architecture principles
- **Ask for clarification** when there's confusion or you need more context and additional information before proceeding
- **Don't create unit tests or summary files or any md files** until you confirm with the user first

## Project Overview

Firebase Realtime Database listener - a background worker (not web service) that connects via Firebase Admin SDK and logs database events in real-time.

## Core Architecture

**Event Flow**: `app.py` (entry/config) → `firebase_admin_listener.py` (RTDB connection) → event processing (currently logging)

**Authentication**: Firebase Admin SDK with service account JSON file (`GOOGLE_SERVICE_ACCOUNT_FILE`)

**Configuration**: Pydantic-based settings in `config.py` with env variable loading and validation

## Key Development Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run
python -m kommo_lang_select

# Debug Firebase
python test_firebase_admin.py  # Admin SDK testing
python diagnose_firebase.py    # Comprehensive diagnostics
```

## Required Environment Variables

```
FIREBASE_DATABASE_URL=https://project-id-default-rtdb.firebaseio.com
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/serviceAccountKey.json
```

## Project-Specific Patterns

**Threading**: Separate listener thread + event queue + signal-aware main loop with `GracefulKiller` for clean shutdown

**Firebase Events**: `@dataclass FirebaseEvent` with `event`, `path`, `data` fields

**Logging**: Structured with `extra` field: `logger.info("Event", extra={"event": ..., "path": ..., "data": ...})`

**Error Handling**: Graceful degradation with config validation and helpful error messages

**Testing**: Pytest with monkeypatch for env variables, focus on config validation

## Quality Tools (pyproject.toml)

Black (line length 100), Ruff (import sorting), MyPy (strict typing). Install dev deps: `pip install -e ".[dev]"`
