"""Base handler class for Firebase event processing."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..services import (
    FirebaseAdminListener,
    FirestoreService,
    KommoAPIService,
    LoveBaliAPIService,
)

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Base handler class for processing Firebase events."""
    
    def __init__(
        self,
        firestore_service: FirestoreService,
        realtime_listener: FirebaseAdminListener,
        kommo_service: KommoAPIService | None = None,
        love_bali_service: LoveBaliAPIService | None = None,
    ) -> None:
        """
        Initialize the base handler.
        
        Args:
            firestore_service: Firestore service instance
            realtime_listener: Firebase Realtime Database listener instance
            kommo_service: Kommo API service instance (optional)
        """
        self.firestore_service = firestore_service
        self.realtime_listener = realtime_listener
        self.kommo_service = kommo_service
        self.love_bali_service = love_bali_service
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_handle(self, event_path: str, event_data: Any) -> bool:
        """
        Check if this handler can process the given event.
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
            
        Returns:
            True if this handler can process the event
        """
        pass
    
    @abstractmethod
    def handle(self, event_path: str, event_data: Any) -> None:
        """
        Handle the Firebase event.
        
        Args:
            event_path: Firebase event path
            event_data: Firebase event data
        """
        pass
    
    def delete_realtime_data(self, path: str) -> bool:
        """
        Delete data from Firebase Realtime Database.
        
        Args:
            path: Path to delete (relative to the listener's base path)
            
        Returns:
            True if successful
        """
        try:
            # Construct the absolute path by combining the listener's base path with the event path
            # Event paths from Firebase Admin SDK are relative to the listening path
            listener_base_path = self.realtime_listener.path.rstrip('/')
            
            # If the event path starts with '/', it's already relative to the base path
            if path.startswith('/'):
                # Remove leading slash and combine with base path
                relative_path = path[1:]  # Remove leading '/'
                absolute_path = f"{listener_base_path}/{relative_path}" if relative_path else listener_base_path
            else:
                # Path doesn't start with '/', combine directly
                absolute_path = f"{listener_base_path}/{path}"
            
            self.logger.debug(f"Deleting from absolute path: {absolute_path} (event path: {path}, base: {listener_base_path})")
            
            success = self.realtime_listener.delete_data(absolute_path)
            if success:
                self.logger.info(f"Successfully deleted data at path: {path}")
            else:
                self.logger.error(f"Failed to delete data at path: {path}")
            return success
        except Exception as e:
            self.logger.error(f"Error deleting data at path {path}: {e}")
            return False
    
    def save_to_firestore(self, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """
        Save data to Firestore.
        
        Args:
            collection: Firestore collection name
            document_id: Document ID
            data: Data to save
            
        Returns:
            True if successful
        """
        try:
            collection_ref = self.firestore_service.get_collection_reference(collection)
            doc_ref = collection_ref.document(document_id)
            doc_ref.set(data)
            self.logger.info(f"Successfully saved data to {collection}/{document_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving data to {collection}/{document_id}: {e}")
            return False