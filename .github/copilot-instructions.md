---
applyTo: "**"
---

# AI Coding Agent Instructions for kommo-command

## Project Overview

Event-driven Python bot integrating Firebase Realtime Database, Firestore, and Kommo CRM. Processes language selection events and manages lead synchronization.

## Core Architecture

- **Event Processing**: Firebase RTDB listener → HandlerManager → Extensible handlers → Firestore/Kommo operations
- **Services**: FirebaseAdminListener, FirestoreService, KommoAPIService
- **Handler Pattern**: All handlers extend BaseHandler with `can_handle()` and `handle()` methods
- **Data Flow**: RTDB (temporary) → Handler processing → Firestore (persistent) → Kommo (CRM)

## Development Guidelines

- **Environment**: Always use MCP to get Python executable information for .venv before executing terminal commands
- **Service Creation**: Use factory functions from `service_factory.py` instead of direct instantiation
- **Handler Implementation**: Extend `BaseHandler`, implement `can_handle()` and `handle()` methods
- **Error Handling**: Services include connection testing and graceful degradation
- **Logging**: Use structured logging with `extra` dict: `logger.info("Event processed", extra={"path": path})`
- **Models**: Inherit from `BaseFirestoreModel` for automatic serialization
- **Threading**: Main thread + listener thread + GracefulKiller for signal handling

## Key Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# Run
python -m kommo_command

# Quality tools
pip install -e ".[dev]"  # Black, Ruff, MyPy, pytest
```

## Best Practices

- Use type hints and Pydantic models
- Follow dependency injection pattern
- Implement comprehensive error handling
- Write structured, testable code
- Use environment variables for configuration
- Test connections before processing events
