from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LogEvent:
    level: str
    message: str
    extra: dict[str, Any] | None = None
