"""Handler for logging incoming Firebase messages."""

from __future__ import annotations

import re
from typing import Any

from .base_handler import BaseHandler
from ..models.session import SessionModel, SessionUpdateRequest
from ..messages import MessageKey, get_message
from ..types import BotID, AppState, AppLanguage, Command
from ..services import LoveBaliAPIError


class IncomingMessageHandler(BaseHandler):
    """Handler that logs incoming messages from Firebase to the console."""

    CUSTOM_MESSAGE_FIELD_ID = 1069656
    DEFAULT_ENTITY_TYPE = "2"
    PASSPORT_ALLOWED_PATTERN = re.compile(r"^[A-Z0-9]{6,12}$")

    def can_handle(self, event_path: str, event_data: Any) -> bool:
        """
        Check if this handler can process the given event.
        
        This handler processes events that:
        1. Have non-empty data
        2. Come from paths that indicate lead data (configurable)
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
            
        Returns:
            True if this handler can process the event
        """
        # Check if data is not empty/null
        if not event_data:
            self.logger.debug(f"Skipping event with empty data at path: {event_path}")
            return False
        
        # Check if data is a dictionary (structured data)
        if not isinstance(event_data, dict):
            self.logger.debug(f"Skipping event with non-dict data at path: {event_path}")
            return False
        
        # You can add more specific path matching logic here
        # For example, only handle events from certain paths like '/leads/', '/incoming/', etc.
        # For now, we'll handle any structured data
        
        self.logger.debug(f"Handler can process event at path: {event_path}")
        return True

    def handle(self, event_path: str, event_data: Any) -> None:
        """
        Handle the incoming message when user click Love Bali Menu.
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
        """
        try:
            
            self.logger.info(f"Processing incoming message for Love Bali Command: {event_path}")

            if event_data is None:
                self.logger.info(
                    "Skipping incoming message with no data",
                    extra={"event_path": event_path},
                )
                return

            if not isinstance(event_data, dict):
                self.logger.warning(
                    "Skipping incoming message with non-dict payload",
                    extra={"event_path": event_path, "payload_type": type(event_data).__name__},
                )
                return

            # Get entity id from lead data
            entity_id = event_data.get('entity_id')
            user_messages = event_data.get('messages', '').strip() if event_data.get('messages') else ''
            user_lang = event_data.get('language', AppLanguage.ENGLISH.value)
            app_state = event_data.get('state', AppState.INITIAL.value)


            # Convert entity_id to int if it's a string
            if entity_id and isinstance(entity_id, str):
                try:
                    entity_id = int(entity_id)
                except ValueError:
                    self.logger.warning(f"Invalid entity_id format: {entity_id}, skipping session lookup")
                    entity_id = None
            
            # Define session variable
            session: SessionModel | None = None
            if entity_id:
                try:
                    session = self.firestore_service.get_active_session_for_entity(entity_id)
                except Exception as exc:
                    self.logger.error(
                        f"Failed to retrieve session for entity_id {entity_id}: {exc}",
                        extra={"entity_id": entity_id}
                    )

                if not session:
                    self.logger.info(f"No session found for entity_id: {entity_id}")
                
                self.logger.debug(f"Start checking app_state {app_state} for entity_id: {entity_id}")

                # Process event based on app_state
                self.logger.debug(f"Checking app_state: {app_state} with : {AppState.INITIAL.value}")
                if app_state == AppState.INITIAL.value: 
                    self.logger.info(f"Processing app_state: {app_state} for entity_id: {entity_id}")    
                    custom_message = get_message(MessageKey.PASSPORT_PROMPT, language=user_lang)
                    self.send_message(entity_id=entity_id, message=custom_message)

                self.logger.debug(f"Checking app_state: {app_state} with : {AppState.AWAITING_PASSPORT_NUMBER.value}")
                if app_state == AppState.AWAITING_PASSPORT_NUMBER.value:
                    self.logger.info(f"Awaiting passport number from entity_id: {entity_id}")

                    normalized_passport = self.normalize_passport_number(user_messages)

                    if not normalized_passport or not self.is_valid_passport_number(normalized_passport, normalized=True):
                        self.logger.warning(
                            f"Invalid passport number format received: {user_messages}",
                            extra={"entity_id": entity_id},
                        )
                        invalid_message = get_message(MessageKey.PASSPORT_INVALID, language=user_lang)
                        self.send_message(entity_id=entity_id, message=invalid_message)
                    else:
                        if not self.love_bali_service:
                            self.logger.warning(
                                "Love Bali service unavailable; skipping passport scan",
                                extra={"entity_id": entity_id},
                            )
                        else:
                            isError = False
                            isFound = False
                            error_message = ""
                            message_params = {
                                "code_voucher": "-",
                                "guest_name": "-",
                                "arrival_date": "-",
                                "expired_date": "-",
                            }
                            response_message: str | None = None
                            try:
                                scan_result = self.love_bali_service.single_scan_passport(normalized_passport)
                                self.logger.info(
                                    f"Love Bali passport scan completed with result: {scan_result}",
                                    extra={
                                        "entity_id": entity_id,
                                        "passport_number": normalized_passport,
                                        "scan_result": scan_result,
                                    },
                                )
                                data = scan_result.get('data') or {}
                                message_params.update(
                                    {
                                        "code_voucher": str(data.get('code_voucher') or "-"),
                                        "guest_name": str(data.get('guest_name') or "-"),
                                        "arrival_date": str(data.get('arrival_date') or "-"),
                                        "expired_date": str(data.get('expired_date') or "-"),
                                    }
                                )
                                success_template = get_message(MessageKey.PASSPORT_FOUND, language=user_lang)
                                try:
                                    response_message = success_template.format(**message_params)
                                    isFound = True
                                except (KeyError, ValueError):
                                    response_message = success_template

                            except LoveBaliAPIError as exc:
                                self.logger.error(
                                    "Love Bali passport scan failed",
                                    extra={
                                        "entity_id": entity_id,
                                        "passport_number": normalized_passport,
                                        "error": str(exc),
                                    },
                                    exc_info=True,
                                )
                                isError = True
                                if(exc.status_code == 401 or exc.status_code == 404):
                                    error_message = get_message(MessageKey.PASSPORT_NOT_FOUND, language=user_lang)
                            except Exception as exc:
                                self.logger.error(
                                    "Unexpected error during Love Bali passport scan",
                                    extra={
                                        "entity_id": entity_id,
                                        "passport_number": normalized_passport,
                                        "error": str(exc),
                                    },
                                    exc_info=True,
                                )
                                isError = True
                                error_message = get_message(MessageKey.PASSPORT_ERROR, language=user_lang)
                            
                            if isError:
                                if not error_message:
                                    error_message = get_message(MessageKey.PASSPORT_ERROR, language=user_lang)
                                response_message = error_message
    
                            if response_message:
                                self.send_message(entity_id=entity_id, message=response_message)
                            
                            self.logger.debug(f"isFound: {isFound} for sesion: {session}")
                            if session and isFound:
                                self.logger.debug(f"Updating session to MAIN_MENU for entity_id: {entity_id}")
                                # Create update request for session
                                update_request = SessionUpdateRequest(command=Command.MAIN_MENU)
                                
                                # Update session in Firestore
                                updated_session = self.firestore_service.update_session(
                                    session_id=session.session_id,
                                    update_request=update_request
                                )
                                if updated_session:
                                    self.show_main_menu(entity_id=entity_id, language=user_lang)
                                


                #delete data after processed
                try:
                    delete_event = self.delete_realtime_data(event_path)
                    if delete_event:
                        self.logger.info(f"Successfully deleted realtime data at path {event_path}")
                except Exception as e:
                    self.logger.error(
                        f"Error deleting realtime data at path {event_path}: {e}",
                        extra={
                            'source_path': event_path,
                            'error': str(e)
                        },
                        exc_info=True
                    )
            
            else:
                self.logger.info("No valid entity_id provided; skipping session lookup")

        except Exception as e:
            self.logger.error(
                f"Error processing incoming lead from path {event_path}: {e}",
                extra={
                    'source_path': event_path,
                    'error': str(e)
                },
                exc_info=True
            )
            raise    


    def send_message(self, entity_id: int, message: str) -> None:
        """Send a message to the Kommo lead via custom field update and salesbot launch."""
        if not self.kommo_service:
            self.logger.warning(
                "Kommo service unavailable; skipping send_message",
                extra={"entity_id": entity_id},
            )
            return

        custom_fields = [
            {
                "field_id": self.CUSTOM_MESSAGE_FIELD_ID,
                "field_name": "Custom Message",
                "field_code": None,
                "field_type": "textarea",
                "values": [{"value": message}],
            }
        ]

        try:
            self.kommo_service.update_lead_custom_fields(entity_id, custom_fields)
            self.logger.debug(
                "Updated custom message field",
                extra={"entity_id": entity_id},
            )
        except Exception as exc:
            self.logger.error(
                "Failed to update custom message field",
                extra={"entity_id": entity_id, "error": str(exc)},
                exc_info=True,
            )

        
        try:
            entity_type = self.kommo_service.get_entity_type_code('lead')
            salesbot_result = self.kommo_service.launch_salesbot(
                bot_id=BotID.REPLY_CUSTOM_BOT_ID.value,
                entity_id=entity_id,
                entity_type=entity_type,
            )
            self.logger.info(
                f"Successfully launched salesbot {BotID.REPLY_CUSTOM_BOT_ID.value} for lead {entity_id}",
                extra={
                    'entity_id': entity_id,
                    'bot_id': BotID.REPLY_CUSTOM_BOT_ID.value,
                    'salesbot_result': salesbot_result,
                },
            )
        except Exception as exc:
            self.logger.error(
                f"Failed to launch salesbot {BotID.REPLY_CUSTOM_BOT_ID.value} for lead {entity_id}: {exc}",
                extra={"entity_id": entity_id, "bot_id": BotID.REPLY_CUSTOM_BOT_ID.value},
                exc_info=True,
            )
    
    def show_main_menu(self, entity_id: int, language: str) -> None:
        """Show the main menu to the user based on their language preference."""
        if not self.kommo_service:
            self.logger.warning(
                "Kommo service unavailable; skipping show_main_menu",
                extra={"entity_id": entity_id},
            )
            return

        main_menu_bot_id = BotID.MAIN_MENU_EN_BOT_ID.value if language == AppLanguage.ENGLISH.value else BotID.MAIN_MENU_ID_BOT_ID.value

        try:
            self.logger.debug(f"Launching main menu bot {main_menu_bot_id} for entity_id: {entity_id}")
            entity_type = self.kommo_service.get_entity_type_code('lead')
            self.kommo_service.launch_salesbot(
                bot_id=main_menu_bot_id,
                entity_id=entity_id,
                entity_type=entity_type,
            )
            self.logger.info(
                f"Successfully launched main menu bot {main_menu_bot_id} for entity_id: {entity_id}",
                extra={"entity_id": entity_id, "bot_id": main_menu_bot_id},
            )
        except Exception as exc:
            self.logger.error(
                f"Failed to launch main menu bot {main_menu_bot_id} for entity_id {entity_id}: {exc}",
                extra={"entity_id": entity_id, "bot_id": main_menu_bot_id},
                exc_info=True,
            )

    def is_valid_passport_number(self, user_message: str, *, normalized: bool = False) -> bool:
        """Validate that the provided user message matches an acceptable passport pattern."""
        candidate = user_message if normalized else self.normalize_passport_number(user_message)
        if not candidate:
            return False

        return bool(self.PASSPORT_ALLOWED_PATTERN.match(candidate))

    def normalize_passport_number(self, user_message: str) -> str | None:
        """Normalize passport input by stripping whitespace and separators."""
        if not user_message:
            return None

        normalized = user_message.strip().upper().replace(" ", "").replace("-", "")
        return normalized or None

