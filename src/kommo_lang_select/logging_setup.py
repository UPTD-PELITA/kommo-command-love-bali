from __future__ import annotations

import logging
import os


def configure_logging(level: str | int = "INFO") -> None:
    if isinstance(level, str):
        level_value = getattr(logging, str(level).upper(), logging.INFO)
    else:
        level_value = level

    root_logger = logging.getLogger()
    root_logger.setLevel(level_value)

    # Basic, structured-ish console logging
    handler = logging.StreamHandler()
    fmt = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    if os.getenv("LOG_JSON", "0") in {"1", "true", "True"}:
        # Very simple JSON-like formatting without extra deps
        fmt = (
            "{\"time\": \"%(asctime)s\", \"level\": \"%(levelname)s\", "
            "\"logger\": \"%(name)s\", \"message\": \"%(message)s\"}"
        )
    handler.setFormatter(logging.Formatter(fmt))

    # Remove existing handlers to avoid duplicates (useful in tests/reloads)
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)
