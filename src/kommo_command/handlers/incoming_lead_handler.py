"""Handler for processing incoming lead events from Firebase."""

from __future__ import annotations

import logging
from typing import Any, Dict

from kommo_command.models.session import SessionCreateRequest

from .base_handler import BaseHandler
from ..models import LeadModel
from ..types import COMMAND_LIST, BotID, Command

logger = logging.getLogger(__name__)


class IncomingLeadHandler(BaseHandler):
    """Handler for processing incoming lead events."""
    
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
    
    def detect_language(self, message: str) -> str | None:
        """
        Detect language from message based on specific patterns.
        
        Args:
            message: The message text to analyze
            
        Returns:
            Language code ('ID' for Indonesian, 'EN' for English) or None if not detected
        """
        if message == "🇮🇩 Bahasa":
            return "ID"
        elif message == "🇬🇧 English":
            return "EN"
        else:
            return None
    
    def is_command(self, user_message: str) -> bool:
        return user_message in COMMAND_LIST

    def handle(self, event_path: str, event_data: Any) -> None:
        """
        Handle the incoming lead event.
        
        This method:
        1. Creates a LeadModel from the event data
        2. Saves the lead to the 'leads' collection in Firestore
        3. Deletes the original data from Realtime Database
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
        """
        try:
            self.logger.info(f"Processing incoming lead from path: {event_path}")
            
            # Create lead model from event data
            lead = LeadModel.from_firebase_event(
                event_path=event_path,
                event_data=event_data,
                metadata={
                    'handler': 'IncomingLeadHandler',
                    'processed_at': None  # Will be set when marked as processed
                }
            )

            # Get entity id from lead data
            entity_id = event_data.get('entity_id')
            messages = event_data.get('messages', '').strip() if event_data.get('messages') else ''
            
            # Convert entity_id to int if it's a string
            if entity_id and isinstance(entity_id, str):
                try:
                    entity_id = int(entity_id)
                except ValueError:
                    self.logger.warning(f"Invalid entity_id format: {entity_id}, skipping session lookup")
                    entity_id = None
            
            # If entity id is present, get session from firestore with entity id
            session = None
            if entity_id:
                try:
                    session = self.firestore_service.get_latest_session_by_entity_id(entity_id)
                    if session:
                        self.logger.info(
                            f"Found existing session for entity {entity_id}: {session.session_id}",
                            extra={
                                'entity_id': entity_id,
                                'session_id': session.session_id,
                                'session_language': session.language
                            }
                        )
                        # Add session info to lead metadata
                        lead.metadata['session_id'] = session.session_id
                        lead.metadata['session_language'] = session.language
                    else:
                        # Launch salesbot if no session found
                        if self.kommo_service:
                            try:
                                # Launch salesbot with bot_id 66624 for the lead
                                entity_type = self.kommo_service.get_entity_type_code('lead')  # '2' for lead
                                salesbot_result = self.kommo_service.launch_salesbot(
                                    bot_id=BotID.LANG_SELECT_BOT_ID.value,
                                    entity_id=entity_id,
                                    entity_type=entity_type
                                )
                                
                                self.logger.info(
                                    f"Successfully launched salesbot 66624 for lead {entity_id}",
                                    extra={
                                        'entity_id': entity_id,
                                        'bot_id': BotID.LANG_SELECT_BOT_ID.value,
                                        'salesbot_result': salesbot_result
                                    }
                                )
                                
                                # Create a new session record for this lead
                                session_request = SessionCreateRequest(
                                                    entity_id=entity_id,
                                                    language=None,  # Language will be detected later
                                                    command=Command.MAIN_MENU,  # Default to main menu
                                                    expires_in_hours=24,
                                                )
                                
                                # Save the new session to Firestore
                                session_success = self.firestore_service.create_session(session_request)

                                if session_success:
                                    self.logger.info(
                                        f"Created new session {session_success.session_id} for lead {entity_id}",
                                        extra={
                                            'entity_id': entity_id,
                                            'session_id': session_success.session_id,
                                            'lead_id': lead.lead_id
                                        }
                                    )
                                    
                                    # Add session info to lead metadata
                                    lead.metadata['new_session_created'] = True
                                    lead.metadata['new_session_id'] = session_success.session_id
                                else:
                                    self.logger.error(
                                        f"Failed to create session for lead {entity_id}",
                                        extra={'entity_id': entity_id, 'lead_id': lead.lead_id}
                                    )
                                
                            except Exception as e:
                                self.logger.error(
                                    f"Something wrong happened: {e}",
                                    extra={
                                        'entity_id': entity_id,
                                        'bot_id': BotID.LANG_SELECT_BOT_ID.value,
                                        'error': str(e)
                                    }
                                )
                                # Add failed launch info to lead metadata
                                lead.metadata['salesbot_launched'] = False
                                lead.metadata['salesbot_error'] = str(e)
                        else:
                            if not self.kommo_service:
                                self.logger.warning("Kommo service not available, cannot launch salesbot")
                            if not entity_id:
                                self.logger.warning("No entity_id provided, cannot launch salesbot")

                        self.logger.debug(f"No active session found for entity {entity_id}")
                except Exception as e:
                    self.logger.warning(
                        f"Error retrieving session for entity {entity_id}: {e}",
                        extra={'entity_id': entity_id, 'error': str(e)}
                    )

            self.logger.info(f"Process Message: {messages}")
            # If message is not empty or whitespace and session exists, check for language detection
            if messages and session:
                # If session has no language set or language is empty, attempt to detect language from messages
                if not session.language or session.language.strip() == "":
                    try:
                        if messages in ["🇮🇩 Bahasa", "🇬🇧 English"]:
                            detected_language = self.detect_language(messages)
                            if detected_language:
                                session.set_language(detected_language)
                                self.save_to_firestore(
                                    collection='sessions',
                                    document_id=session.session_id,
                                    data=session.to_firestore_dict()
                                )
                                self.logger.info(
                                    f"Detected and set language '{detected_language}' for session {session.session_id}",
                                    extra={
                                        'entity_id': entity_id,
                                        'session_id': session.session_id,
                                        'detected_language': detected_language
                                    }
                                )
                                # Add detected language to lead metadata
                                lead.metadata['detected_language'] = detected_language
                            else:
                                self.logger.warning(
                                    f"Failed to detect language from message for session {session.session_id}",
                                    extra={
                                        'entity_id': entity_id,
                                        'session_id': session.session_id,
                                        'message_preview': messages[:50] + '...' if len(messages) > 50 else messages
                                    }
                                )
                    except Exception as e:
                        self.logger.error(
                            f"Error detecting language from message for session {session.session_id}: {e}",
                            extra={
                                'entity_id': entity_id,
                                'session_id': session.session_id,
                                'error': str(e)
                            },
                            exc_info=True
                        )
                
                # If session already has a language and messages is not empty, check if message is a command
                elif session.language and self.is_command(messages):
                    self.logger.info(
                        f"Message is a recognized command '{messages}' for session {session.session_id}",
                        extra={
                            'entity_id': entity_id,
                            'session_id': session.session_id,
                            'current_language': session.language
                        }
                    )

                    if self.kommo_service and entity_id is not None:
                        custom_fields = [
                            {
                                "field_id": 1069656,
                                "field_name": "Custom Message",
                                "field_code": None,
                                "field_type": "textarea",
                                "values": [{ "value": messages }]
                            }
                        ]
                        results_update_custom_fields = self.kommo_service.update_lead_custom_fields(entity_id, custom_fields)
                        self.logger.info(
                            f"Updated lead {entity_id} custom fields with command message",
                            extra={
                                'entity_id': entity_id,
                                'session_id': session.session_id,
                                'command_message': messages,
                                'update_results': results_update_custom_fields
                            }
                        )

                        if results_update_custom_fields:
                            entity_type = self.kommo_service.get_entity_type_code('lead')  # '2' for lead
                            salesbot_result = self.kommo_service.launch_salesbot(
                                            bot_id=BotID.REPLY_CUSTOM_BOT_ID.value,
                                            entity_id=entity_id,
                                            entity_type=entity_type
                                        )
                            self.logger.info(
                                            f"Successfully launched salesbot {BotID.REPLY_CUSTOM_BOT_ID.value} for lead {entity_id}",
                                            extra={
                                                'entity_id': entity_id,
                                                'bot_id': BotID.REPLY_CUSTOM_BOT_ID.value,
                                                'salesbot_result': salesbot_result
                                            }
                                        )
                    else:
                        if not self.kommo_service:
                            self.logger.warning("Kommo service not available, cannot update custom fields")
                        if entity_id is None:
                            self.logger.warning(
                                f"Cannot update custom fields for lead because entity_id is None",
                                extra={
                                    'session_id': session.session_id,
                                    'command_message': messages
                                }
                            )
            
            
            # Save to Firestore leads collection
            lead.mark_as_processed()  # Mark as processed before saving
            success = self.save_to_firestore(
                collection='leads',
                document_id=lead.lead_id,
                data=lead.to_firestore_dict()
            )
            
            if success:
                # Delete from Realtime Database
                delete_success = self.delete_realtime_data(event_path)
                
                if delete_success:
                    self.logger.info(
                        f"Successfully processed lead {lead.lead_id} and cleaned up source data",
                        extra={
                            'lead_id': lead.lead_id,
                            'source_path': event_path,
                            'data_size': len(str(event_data))
                        }
                    )
                else:
                    self.logger.warning(
                        f"Lead {lead.lead_id} saved to Firestore but failed to delete from Realtime DB",
                        extra={
                            'lead_id': lead.lead_id,
                            'source_path': event_path
                        }
                    )
            else:
                self.logger.error(
                    f"Failed to save lead to Firestore from path: {event_path}",
                    extra={
                        'source_path': event_path,
                        'data_preview': str(event_data)[:200] + '...' if len(str(event_data)) > 200 else str(event_data)
                    }
                )
                
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
    

    def get_lead_stats(self) -> Dict[str, Any]:
        """
        Get statistics about processed leads.
        
        Returns:
            Dictionary with lead statistics
        """
        try:
            leads_collection = self.firestore_service.get_collection_reference('leads')
            
            # Count total leads
            total_leads = len(list(leads_collection.stream()))
            
            # Count processed leads
            processed_query = leads_collection.where('processed', '==', True)
            processed_leads = len(list(processed_query.stream()))
            
            # Count unprocessed leads
            unprocessed_leads = total_leads - processed_leads
            
            stats = {
                'total_leads': total_leads,
                'processed_leads': processed_leads,
                'unprocessed_leads': unprocessed_leads,
                'processing_rate': (processed_leads / total_leads * 100) if total_leads > 0 else 0
            }
            
            self.logger.info("Lead statistics retrieved", extra=stats)
            return stats
            
        except Exception as e:
            self.logger.error(f"Error retrieving lead statistics: {e}")
            return {
                'total_leads': 0,
                'processed_leads': 0,
                'unprocessed_leads': 0,
                'processing_rate': 0,
                'error': str(e)
            }