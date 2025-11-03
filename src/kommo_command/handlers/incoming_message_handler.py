"""Handler for logging incoming Firebase messages."""

from __future__ import annotations

from typing import Any

from .base_handler import BaseHandler
from ..types import BotID


class IncomingMessageHandler(BaseHandler):
    """Handler that logs incoming messages from Firebase to the console."""

    MESSAGE_KEYS = ("message", "messages", "text", "body")
    CUSTOM_MESSAGE_FIELD_ID = 1069656
    PASSPORT_PROMPT = "Please enter your passport number"
    DEFAULT_ENTITY_TYPE = "2"

    def can_handle(self, event_path: str, event_data: Any) -> bool:
        """
        Determine whether this handler should process the event.

        Args:
            event_path: Firebase event path
            event_data: Firebase event data

        Returns:
            True when the payload contains a user-facing message we can display.
        """

        self.logger.debug("Check if can handle incoming message")
        
        if not event_data:
            return False

        if isinstance(event_data, str):
            return False

        if isinstance(event_data, dict):
            entity_id = event_data.get("entity_id")
            if entity_id is None:
                return False
            if isinstance(entity_id, str) and not entity_id.strip():
                return False

            for key in self.MESSAGE_KEYS:
                value = event_data.get(key)
                if isinstance(value, str) and value.strip():
                    return True
                if isinstance(value, list):
                    if any(isinstance(item, str) and item.strip() for item in value):
                        return True
            return False

        return False

    def handle(self, event_path: str, event_data: Any) -> None:
        """Process an incoming message and trigger Kommo updates."""
        message_text = self._extract_message(event_data)
        if not message_text:
            self.logger.debug(
                "Incoming event ignored: no message content detected",
                extra={
                    "path": event_path,
                    "data_type": type(event_data).__name__,
                },
            )
            return

        self.logger.info(
            "Incoming message received",
            extra={
                "path": event_path,
                "payload_message": message_text,
            },
        )
        print(f"[IncomingMessageHandler] {message_text}")

        entity_id = self._extract_entity_id(event_data)
        if entity_id is None:
            self.logger.warning(
                "Incoming message missing valid entity_id",
                extra={
                    "path": event_path,
                    "payload_message": message_text,
                },
            )
            return

        entity_type = self._resolve_entity_type(event_data)
        session = self._get_session_for_entity(entity_id)

        if session:
            custom_field_value = self.PASSPORT_PROMPT
            session_id = getattr(session, "session_id", None)
        else:
            custom_field_value = message_text
            session_id = None

        custom_fields = [
            {
                "field_id": self.CUSTOM_MESSAGE_FIELD_ID,
                "field_name": "Custom Message",
                "field_code": None,
                "field_type": "textarea",
                "values": [{"value": custom_field_value}],
            }
        ]

        if not self.kommo_service:
            self.logger.warning(
                "Kommo service unavailable; skipping lead update",
                extra={"entity_id": entity_id, "path": event_path},
            )
            return

        try:
            update_result = self.kommo_service.update_lead_custom_fields(entity_id, custom_fields)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "Failed to update lead custom fields",
                extra={
                    "entity_id": entity_id,
                    "session_found": bool(session),
                    "session_id": session_id,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return

        self.logger.info(
            "Updated lead custom fields from incoming message",
            extra={
                "entity_id": entity_id,
                "session_found": bool(session),
                "session_id": session_id,
                "custom_field_value": custom_field_value,
                "update_result": update_result,
            },
        )

        try:
            salesbot_result = self.kommo_service.launch_salesbot(
                bot_id=BotID.REPLY_CUSTOM_BOT_ID.value,
                entity_id=entity_id,
                entity_type=entity_type,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "Failed to launch salesbot",
                extra={
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "session_found": bool(session),
                    "session_id": session_id,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return

        self.logger.info(
            "Salesbot launched for lead after incoming message",
            extra={
                "entity_id": entity_id,
                "entity_type": entity_type,
                "session_found": bool(session),
                "session_id": session_id,
                "salesbot_result": salesbot_result,
            },
        )

    def _extract_message(self, event_data: Any) -> str | None:
        """Extract the first non-empty message string from the event payload."""
        if isinstance(event_data, str):
            cleaned = event_data.strip()
            return cleaned or None

        if isinstance(event_data, dict):
            for key in self.MESSAGE_KEYS:
                value = event_data.get(key)
                if isinstance(value, str):
                    cleaned = value.strip()
                    if cleaned:
                        return cleaned
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and item.strip():
                            return item.strip()

        return None

    def _extract_entity_id(self, event_data: Any) -> int | None:
        """Extract and normalize the entity identifier from the payload."""
        if not isinstance(event_data, dict):
            return None

        entity_id = event_data.get("entity_id")
        if entity_id is None:
            return None

        try:
            return int(entity_id)
        except (TypeError, ValueError):
            self.logger.warning(
                "Invalid entity_id format in incoming message",
                extra={"entity_id": entity_id},
            )
            return None

    def _resolve_entity_type(self, event_data: Any) -> str:
        """Resolve Kommo entity type code for launching the salesbot."""
        if isinstance(event_data, dict):
            raw_type = event_data.get("entity_type")
            if isinstance(raw_type, int):
                raw_type = str(raw_type)

            if isinstance(raw_type, str):
                cleaned = raw_type.strip()
                if cleaned in {"1", "2"}:
                    return cleaned
                if self.kommo_service:
                    try:
                        return self.kommo_service.get_entity_type_code(cleaned)
                    except Exception:
                        self.logger.debug(
                            "Unable to resolve entity_type from payload; falling back to default",
                            extra={"entity_type": cleaned},
                        )

        return self.DEFAULT_ENTITY_TYPE

    def _get_session_for_entity(self, entity_id: int):
        """Retrieve the latest session for a given entity, if any."""
        try:
            return self.firestore_service.get_latest_session_by_entity_id(entity_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "Failed to retrieve session for entity",
                extra={"entity_id": entity_id, "error": str(exc)},
                exc_info=True,
            )
            return None
