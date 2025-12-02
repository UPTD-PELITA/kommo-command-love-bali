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

- **Environment**: This project runs inside a dev container; use the container's preconfigured Python environment for all commands.
  - Always use the Pylance MCP tools for any Python file analysis or debugging (syntax checks, environment inspection, refactoring, running snippets) instead of shell-based Python invocations.
- **Service Creation**: Use factory functions from `service_factory.py` instead of direct instantiation
- **Handler Implementation**: Extend `BaseHandler`, implement `can_handle()` and `handle()` methods
- **Error Handling**: Services include connection testing and graceful degradation
- **Logging**: Use structured logging with `extra` dict: `logger.info("Event processed", extra={"path": path})`
- **Models**: Inherit from `BaseFirestoreModel` for automatic serialization
- **Threading**: Main thread + listener thread + GracefulKiller for signal handling

## Key Commands

```bash
# Setup (inside dev container)
pip install -e .

# Run (inside dev container)
python -m kommo_command

# Quality tools (inside dev container)
pip install -e ".[dev]"  # Black, Ruff, MyPy, pytest
```

## Best Practices

- Use type hints and Pydantic models
- Follow dependency injection pattern
- Implement comprehensive error handling
- Write structured, testable code
- Use environment variables for configuration
- Test connections before processing events
