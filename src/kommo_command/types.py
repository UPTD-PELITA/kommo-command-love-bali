from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from enum import Enum


@dataclass
class LogEvent:
    level: str
    message: str
    extra: dict[str, Any] | None = None


class Command(Enum):
    """Enum for bot command states."""
    MAIN_MENU = "Main Menu"
    LANG_SELECT = "Lang Select"
    LOVE_BALI = "Love Bali"
    SIGAPURA = "SigaPura"
    CHAT_OPERATOR = "Chat Operator"

class BotID(Enum):
    """Enum for bot IDs."""
    LANG_SELECT_BOT_ID = 66624  # Language Selection Bot
    REPLY_CUSTOM_BOT_ID = 64729    # Love Bali Bot
    

# List of command strings for easy checking against user messages
COMMAND_LIST = [cmd.value for cmd in Command]
