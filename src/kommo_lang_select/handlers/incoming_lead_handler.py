"""Handler for processing incoming lead events from Firebase."""

from __future__ import annotations

import logging
from typing import Any, Dict

from .base_handler import BaseHandler
from ..models import LeadModel, SessionModel

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
            message = event_data.get('message')
            
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
                                    bot_id=66624,
                                    entity_id=entity_id,
                                    entity_type=entity_type
                                )
                                
                                self.logger.info(
                                    f"Successfully launched salesbot 66624 for lead {entity_id}",
                                    extra={
                                        'entity_id': entity_id,
                                        'bot_id': 66624,
                                        'salesbot_result': salesbot_result
                                    }
                                )
                                
                                # Add salesbot launch info to lead metadata
                                lead.metadata['salesbot_launched'] = True
                                lead.metadata['salesbot_id'] = 66624
                                lead.metadata['salesbot_result'] = salesbot_result
                                
                            except Exception as e:
                                self.logger.error(
                                    f"Failed to launch salesbot 66624 for lead {entity_id}: {e}",
                                    extra={
                                        'entity_id': entity_id,
                                        'bot_id': 66624,
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
            
            # Save to Firestore leads collection
            success = self.save_to_firestore(
                collection='leads',
                document_id=lead.lead_id,
                data=lead.to_firestore_dict()
            )
            
            if success:
                # Mark as processed
                lead.mark_as_processed()
                
                # Update the document with processed status
                self.save_to_firestore(
                    collection='leads',
                    document_id=lead.lead_id,
                    data=lead.to_firestore_dict()
                )
                
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