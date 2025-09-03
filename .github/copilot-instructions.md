---
applyTo: "**"
---

# AI Coding Agent Instructions for kommo-lang-select

## General Guidelines

- **Always code with industry best practices** - follow established patterns, proper error handling, type hints, and clean architecture principles
- **Ask for clarification** when there's confusion or you need more context and additional information before proceeding
- **Don't create unit tests or summary files or any md files** until you confirm with the user first

## Project Overview

Multi-service background worker that processes Firebase Realtime Database events, manages sessions in Firestore, and synchronizes data with Kommo CRM. Architecture uses an extensible handler system for event processing.

## Core Architecture

**Data Flow**: `app.py` → `service_factory.py` (service creation) → `HandlerManager` → registered handlers → Firebase/Firestore/Kommo operations

**Services**:

- `FirebaseAdminListener` (RTDB events)
- `FirestoreService` (session persistence)
- `KommoAPIService` (CRM integration)

**Event Processing**: Handlers inherit from `BaseHandler`, implement `can_handle()` and `handle()` methods. Manager routes events to capable handlers.

## Key Development Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run application
python -m kommo_lang_select

# Test services independently
python test_firebase_admin.py      # Firebase RTDB
python test_firestore_sessions.py  # Firestore sessions
python test_kommo_api.py           # Kommo CRM API
python example_kommo_usage.py      # Kommo usage examples

# Quality tools
pip install -e ".[dev]"  # Install Black, Ruff, MyPy, pytest
```

## Required Environment Variables

```bash
# Firebase (both RTDB and Firestore)
FIREBASE_DATABASE_URL=https://project-id-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIRESTORE_DATABASE_NAME=kommo-webhook
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/serviceAccountKey.json

# Kommo CRM API
KOMMO_CLIENT_ID=oauth_client_id
KOMMO_CLIENT_SECRET=oauth_client_secret
KOMMO_SUBDOMAIN=account_subdomain
KOMMO_ACCESS_TOKEN=bearer_token
```

## Project-Specific Patterns

**Service Creation**: Use `service_factory.py` functions instead of direct instantiation:

```python
from .service_factory import create_kommo_service, create_firestore_service
kommo = create_kommo_service(settings)
```

**Handler Pattern**: All event processors extend `BaseHandler`:

```python
class MyHandler(BaseHandler):
    def can_handle(self, event_path: str, event_data: Any) -> bool:
        return isinstance(event_data, dict) and 'my_key' in event_data

    def handle(self, event_path: str, event_data: Any) -> None:
        # Process -> save_to_firestore() -> delete_realtime_data()
        # Optional: sync to Kommo if self.kommo_service available
```

**Threading**: Main thread with event queue + listener thread + `GracefulKiller` for signal handling

**Models**: Inherit from `BaseFirestoreModel` for automatic serialization:

```python
class MyModel(BaseFirestoreModel):
    def to_firestore_dict(self) -> Dict[str, Any]  # Auto-implemented
```

**Error Handling**: Services include connection testing and graceful degradation. App validates all configs before starting services.

**Logging**: Structured with `extra` dict:

```python
logger.info("Event processed", extra={"path": path, "handler": handler_name})
```

## Integration Points

**Firebase ↔ Kommo**: `IncomingLeadHandler` transforms Firebase events to Kommo leads via `sync_lead_to_kommo()`

**RTDB ↔ Firestore**: Handlers move data from RTDB (temporary) to Firestore (persistent) then clean up source

**Cross-Service**: All handlers receive all three services (Firebase, Firestore, Kommo) but Kommo is optional

## Quality Tools (pyproject.toml)

Black (line length 100), Ruff (import sorting + linting), MyPy (strict typing), pytest for testing.
