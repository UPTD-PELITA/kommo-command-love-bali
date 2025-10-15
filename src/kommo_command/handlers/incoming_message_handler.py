"""Handler for responding to incoming Firebase messages."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base_handler import BaseHandler
from ..models.session import SessionUpdateRequest


class IncomingMessageHandler(BaseHandler):
    """Handler that prompts users for passport numbers after each message."""

    MESSAGE_KEYS = ("message", "messages", "text", "body")
    PASSPORT_PROMPTS = {
        "EN": "Enter passport number",
        "ID": "Masukkan nomor paspor",
    }
    WAITING_FOR_PASSPORT_STATE = "waiting_input_no_passport"
    STEP_PREFIX = "[IncomingMessageHandler]"

    def can_handle(self, event_path: str, event_data: Any) -> bool:
        """Return True when the payload contains a user-facing message we can display."""
        if not event_data:
            return False

        if isinstance(event_data, str):
            return bool(event_data.strip())

        if isinstance(event_data, dict):
            for key in self.MESSAGE_KEYS:
                value = event_data.get(key)
                if isinstance(value, str) and value.strip():
                    return True
                if isinstance(value, list) and any(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    return True
            return False

        return False

    def handle(self, event_path: str, event_data: Any) -> None:
        """Log the message content, reply with a passport prompt, and update session state."""
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
        print(f"{self.STEP_PREFIX} Step 1: Received user message -> {message_text}")

        raw_session_id = self._extract_session_id(event_path, event_data)
        entity_id = self._extract_entity_id(event_data)
        session = self._fetch_session(raw_session_id, entity_id)
        session_id = raw_session_id or (getattr(session, "session_id", None) if session else None)

        language = self._determine_language(event_data, session)
        prompt = self._localize_passport_prompt(language)

        prompt_sent = self._send_language_prompt(session_id, prompt, language)
        if prompt_sent:
            print(
                f"{self.STEP_PREFIX} Step 2: Prompted user with '{prompt}' in language {language}"
            )
        else:
            print(
                f"{self.STEP_PREFIX} Step 2: Skipped sending prompt (missing session context)"
            )

        state_updated = self._update_session_state(session_id, entity_id)
        if state_updated:
            print(
                f"{self.STEP_PREFIX} Step 3: Session state set to {self.WAITING_FOR_PASSPORT_STATE}"
            )
        else:
            print(
                f"{self.STEP_PREFIX} Step 3: Skipped session state update (session not found)"
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

    def _extract_session_id(self, event_path: str, event_data: Any) -> Optional[str]:
        """Infer the session identifier from payload or event path."""
        if isinstance(event_data, dict):
            for key in ("session_id", "sessionId"):
                value = event_data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        parts = [part for part in event_path.split("/") if part]
        for index, part in enumerate(parts[:-1]):
            if part in {"sessions", "messages", "incoming_messages"} and index + 1 < len(parts):
                candidate = parts[index + 1]
                if candidate and candidate not in {"messages", "incoming", "outgoing"}:
                    return candidate
        return None

    def _extract_entity_id(self, event_data: Any) -> Optional[int]:
        """Extract the Kommo entity identifier when available."""
        if not isinstance(event_data, dict):
            return None

        for key in ("entity_id", "entityId", "lead_id", "leadId"):
            value = event_data.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.strip():
                try:
                    return int(value)
                except ValueError:
                    self.logger.debug(
                        "Unable to convert entity id to int",
                        extra={"key": key, "value": value},
                    )
        return None

    def _fetch_session(self, session_id: Optional[str], entity_id: Optional[int]):
        """Retrieve the latest session using session or entity identifiers."""
        if session_id:
            try:
                session = self.firestore_service.get_session(session_id)
                if session:
                    return session
            except Exception as exc:
                self.logger.error(
                    "Failed to fetch session by session_id",
                    extra={"session_id": session_id, "error": str(exc)},
                    exc_info=True,
                )

        if entity_id is not None:
            try:
                return self.firestore_service.get_latest_session_by_entity_id(entity_id)
            except Exception as exc:
                self.logger.error(
                    "Failed to fetch session by entity_id",
                    extra={"entity_id": entity_id, "error": str(exc)},
                    exc_info=True,
                )
        return None

    def _determine_language(self, event_data: Any, session: Any) -> str:
        """Resolve the language preference with sensible fallbacks."""
        if isinstance(event_data, dict):
            for key in ("language", "lang", "locale"):
                value = event_data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().upper()

        session_language = getattr(session, "language", None)
        if isinstance(session_language, str) and session_language.strip():
            return session_language.strip().upper()

        return "EN"

    def _localize_passport_prompt(self, language: str) -> str:
        """Return the localized passport prompt for the requested language."""
        normalized = language.upper()
        return self.PASSPORT_PROMPTS.get(normalized, self.PASSPORT_PROMPTS["EN"])

    def _send_language_prompt(self, session_id: Optional[str], prompt: str, language: str) -> bool:
        """Send the localized passport prompt back to Firebase."""
        if not session_id:
            self.logger.warning(
                "Cannot send passport prompt without a session identifier",
                extra={"language": language},
            )
            return False

        payload: Dict[str, Any] = {
            "message": prompt,
            "language": language,
            "state": self.WAITING_FOR_PASSPORT_STATE,
            "handler": self.__class__.__name__,
        }
        response_path = self._build_absolute_path("responses", session_id)

        try:
            self.realtime_listener.write_data(payload, path=response_path)
            self.logger.info(
                "Sent passport prompt to Firebase",
                extra={
                    "session_id": session_id,
                    "language": language,
                    "response_path": response_path,
                },
            )
            return True
        except Exception as exc:
            self.logger.error(
                "Failed to send passport prompt",
                extra={"session_id": session_id, "error": str(exc)},
                exc_info=True,
            )
            return False

    def _update_session_state(
        self,
        session_id: Optional[str],
        entity_id: Optional[int],
    ) -> bool:
        """Persist the waiting state in Firestore and mirror it to Realtime Database."""
        if not session_id:
            self.logger.warning(
                "Cannot update session state without a session identifier",
                extra={"entity_id": entity_id},
            )
            return False

        try:
            update_request = SessionUpdateRequest(
                metadata={"state": self.WAITING_FOR_PASSPORT_STATE}
            )
            updated_session = self.firestore_service.update_session(session_id, update_request)
            if updated_session is None:
                self.logger.warning(
                    "Session not found while attempting to update state",
                    extra={"session_id": session_id, "entity_id": entity_id},
                )
                return False

            state_path = self._build_absolute_path("sessions", session_id, "state")
            self.realtime_listener.write_data(
                self.WAITING_FOR_PASSPORT_STATE,
                path=state_path,
            )

            self.logger.info(
                "Updated session state to waiting for passport",
                extra={
                    "session_id": session_id,
                    "entity_id": entity_id,
                    "state_path": state_path,
                },
            )
            return True
        except Exception as exc:
            self.logger.error(
                "Failed to persist session state",
                extra={"session_id": session_id, "entity_id": entity_id, "error": str(exc)},
                exc_info=True,
            )
            return False

    def _build_absolute_path(self, *segments: str) -> str:
        """Compose an absolute Firebase path using the listener base path."""
        base = self.realtime_listener.path.strip("/")
        base_prefix = f"/{base}" if base else ""
        extra = "/".join(segment.strip("/") for segment in segments if segment)
        if base_prefix and extra:
            return f"{base_prefix}/{extra}"
        if base_prefix:
            return base_prefix or "/"
        if extra:
            return f"/{extra}"
        return "/"
