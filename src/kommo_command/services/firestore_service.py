"""Firestore service for managing sessions and database operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore
from google.cloud.firestore import FieldFilter

from ..models import SessionModel, SessionCreateRequest, SessionUpdateRequest

logger = logging.getLogger(__name__)


class FirestoreService:
    """Service class for Firestore database operations."""
    
    def __init__(
        self,
        project_id: str,
        database_name: str,
        service_account_path: Optional[str] = None,
        app_name: Optional[str] = None,
    ) -> None:
        """
        Initialize Firestore service.
        
        Args:
            project_id: Firebase project ID
            database_name: Firestore database name (from environment config)
            service_account_path: Path to service account JSON file
            app_name: Firebase app name (optional)
        """
        self.project_id = project_id
        self.database_name = database_name
        self.service_account_path = service_account_path
        self.app_name = app_name or f"firestore_service_{id(self)}"
        self._app: Optional[firebase_admin.App] = None
        self._db: Optional[firestore.Client] = None
        
        self._initialize_app()
    
    def _initialize_app(self) -> None:
        """Initialize Firebase Admin SDK app for Firestore."""
        try:
            # Check if app already exists and delete it
            try:
                existing_app = firebase_admin.get_app(self.app_name)
                firebase_admin.delete_app(existing_app)
                logger.debug(f"Deleted existing Firebase app: {self.app_name}")
            except ValueError:
                pass  # App doesn't exist, which is fine
            
            # Initialize credentials first
            if self.service_account_path:
                cred = credentials.Certificate(self.service_account_path)
                # For Google Cloud client, we need to use the service account file directly
                from google.oauth2 import service_account
                gc_credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path
                )
            else:
                # Use Application Default Credentials
                cred = credentials.ApplicationDefault()
                gc_credentials = None  # Let it use ADC
            
            self._app = firebase_admin.initialize_app(
                cred,
                {
                    'projectId': self.project_id,
                },
                name=self.app_name
            )
            
            # Initialize Firestore client using Google Cloud library directly
            # This allows us to specify a named database
            if self.database_name and self.database_name != "(default)":
                # Use named database with Google Cloud Firestore client
                logger.info(f"Initializing Firestore client for named database: {self.database_name}")
                self._db = firestore.Client(
                    project=self.project_id,
                    database=self.database_name,
                    credentials=gc_credentials
                )
            else:
                # Use default database
                logger.info("Initializing Firestore client for default database")
                self._db = firestore.Client(
                    project=self.project_id,
                    credentials=gc_credentials
                )
            
            logger.info(f"Initialized Firestore client for database: {self.database_name}")
            
            logger.info(f"Initialized Firestore service for project: {self.project_id}")
            logger.info(f"Database: {self.database_name}")
            logger.info(f"App: {self.app_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore service: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test the Firestore connection."""
        if self._db is None:
            logger.error("Firestore client is not initialized")
            return False
        
        try:
            # Try to write and read a test document
            test_doc_ref = self._db.collection('_connection_test').document('test')
            test_data = {
                'timestamp': datetime.now(timezone.utc),
                'message': 'Connection test successful'
            }
            
            # Write test data
            test_doc_ref.set(test_data)
            logger.info("Firestore write test successful")
            
            # Read test data
            doc = test_doc_ref.get()
            if doc.exists:
                logger.info("Firestore read test successful")
            
            # Clean up test data
            test_doc_ref.delete()
            logger.info("Test data cleaned up")
            
            logger.info("Firestore connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Firestore connection test failed: {e}")
            return False
    
    # Session management methods
    
    def create_session(self, session_request: SessionCreateRequest) -> SessionModel:
        """
        Create a new session in Firestore.
        
        Args:
            session_request: Session creation request data
            
        Returns:
            Created SessionModel
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            session = session_request.to_session_model()
            
            # Save to Firestore
            session_ref = self._db.collection('sessions').document(session.session_id)
            session_ref.set(session.to_firestore_dict())
            
            logger.info(f"Created session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            SessionModel if found, None otherwise
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            session_ref = self._db.collection('sessions').document(session_id)
            doc = session_ref.get()
            
            if not doc.exists:
                logger.debug(f"Session not found: {session_id}")
                return None
            
            data = doc.to_dict()
            if data is None:
                logger.debug(f"Session data is None for: {session_id}")
                return None
            
            session = SessionModel.from_firestore_dict(data)
            logger.debug(f"Retrieved session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise
    
    def update_session(self, session_id: str, update_request: SessionUpdateRequest) -> Optional[SessionModel]:
        """
        Update an existing session.
        
        Args:
            session_id: Session ID to update
            update_request: Update request data
            
        Returns:
            Updated SessionModel if successful, None if session not found
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            session_ref = self._db.collection('sessions').document(session_id)
            doc = session_ref.get()
            
            if not doc.exists:
                logger.debug(f"Session not found for update: {session_id}")
                return None
            
            # Get current session
            data = doc.to_dict()
            if data is None:
                logger.debug(f"Session data is None for update: {session_id}")
                return None
            session = SessionModel.from_firestore_dict(data)
            
            # Apply updates
            update_data = {}
            if update_request.language is not None:
                session.language = update_request.language
                update_data['language'] = update_request.language
            
            if update_request.metadata is not None:
                session.metadata.update(update_request.metadata)
                update_data['metadata'] = session.metadata
            
            if update_request.is_active is not None:
                session.is_active = update_request.is_active
                update_data['is_active'] = update_request.is_active
            
            if update_request.expires_in_hours is not None:
                from datetime import timedelta
                session.expires_at = datetime.now(timezone.utc) + timedelta(hours=update_request.expires_in_hours)
                update_data['expires_at'] = session.expires_at
            
            # Update timestamp
            session.update_timestamp()
            update_data['updated_at'] = session.updated_at
            
            # Save to Firestore
            session_ref.update(update_data)
            
            logger.info(f"Updated session: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            session_ref = self._db.collection('sessions').document(session_id)
            doc = session_ref.get()
            
            if not doc.exists:
                logger.debug(f"Session not found for deletion: {session_id}")
                return False
            
            session_ref.delete()
            logger.info(f"Deleted session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise
            
    def get_sessions_by_user(self, user_id: str, active_only: bool = True) -> List[SessionModel]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID to search for
            active_only: If True, only return active sessions
            
        Returns:
            List of SessionModel objects
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            query = self._db.collection('sessions').where(filter=FieldFilter('user_id', '==', user_id))
            
            if active_only:
                query = query.where(filter=FieldFilter('is_active', '==', True))
            
            docs = query.stream()
            sessions = []
            
            for doc in docs:
                data = doc.to_dict()
                if data is None:
                    logger.debug(f"Session data is None for doc in user {user_id}")
                    continue
                session = SessionModel.from_firestore_dict(data)
                # Check if session is expired
                if not session.is_expired():
                    sessions.append(session)
                elif session.is_active:
                    # Auto-deactivate expired sessions
                    self.update_session(session.session_id, SessionUpdateRequest(is_active=False))
            
            logger.debug(f"Retrieved {len(sessions)} sessions for user: {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {e}")
            raise
            
    def get_sessions_by_entity_id(self, entity_id: int, active_only: bool = True) -> List[SessionModel]:
        """
        Get all sessions for an entity.
        
        Args:
            entity_id: Entity ID to search for
            active_only: If True, only return active sessions
            
        Returns:
            List of SessionModel objects
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            query = self._db.collection('sessions').where(filter=FieldFilter('entity_id', '==', entity_id))
            
            if active_only:
                query = query.where(filter=FieldFilter('is_active', '==', True))
            
            docs = query.stream()
            sessions = []
            
            for doc in docs:
                data = doc.to_dict()
                if data is None:
                    logger.debug(f"Session data is None for doc in entity {entity_id}")
                    continue
                session = SessionModel.from_firestore_dict(data)
                # Check if session is expired
                if not session.is_expired():
                    sessions.append(session)
                elif session.is_active:
                    # Auto-deactivate expired sessions
                    self.update_session(session.session_id, SessionUpdateRequest(is_active=False))
            
            logger.debug(f"Retrieved {len(sessions)} sessions for entity: {entity_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get sessions for entity {entity_id}: {e}")
            raise
    
    def get_latest_session_by_entity_id(self, entity_id: int, active_only: bool = True) -> Optional[SessionModel]:
        """
        Get the latest session for an entity.
        
        Args:
            entity_id: Entity ID to search for
            active_only: If True, only return active sessions
            
        Returns:
            Latest SessionModel if found, None otherwise
        """
        try:
            sessions = self.get_sessions_by_entity_id(entity_id, active_only)
            if not sessions:
                return None
            
            # Sort by updated_at descending to get the latest session
            latest_session = max(sessions, key=lambda s: s.updated_at)
            logger.debug(f"Retrieved latest session for entity {entity_id}: {latest_session.session_id}")
            return latest_session
            
        except Exception as e:
            logger.error(f"Failed to get latest session for entity {entity_id}: {e}")
            raise
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        
        try:
            current_time = datetime.now(timezone.utc)
            
            # Query for expired sessions - this may require a composite index
            try:
                # Use separate where clauses instead of And filter for better compatibility
                query = self._db.collection('sessions').where(filter=FieldFilter('expires_at', '<=', current_time)).where(filter=FieldFilter('is_active', '==', True))
                
                docs = query.stream()
                cleaned_count = 0
                
                batch = self._db.batch()
                for doc in docs:
                    batch.update(doc.reference, {'is_active': False, 'updated_at': current_time})
                    cleaned_count += 1
                
                if cleaned_count > 0:
                    batch.commit()
                    logger.info(f"Cleaned up {cleaned_count} expired sessions")
                
                return cleaned_count
                
            except Exception as index_error:
                if "requires an index" in str(index_error):
                    logger.warning(f"Composite index required for cleanup query. Please create the index in Firebase Console.")
                    logger.warning(f"For now, we'll skip the cleanup operation.")
                    return 0
                else:
                    raise index_error
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise
    
    def get_collection_reference(self, collection_name: str):
        """Get a reference to a Firestore collection."""
        if self._db is None:
            raise RuntimeError("Firestore client is not initialized")
        return self._db.collection(collection_name)
    
    def close(self) -> None:
        """Close the Firestore service and clean up resources."""
        if self._app:
            try:
                firebase_admin.delete_app(self._app)
                logger.info(f"Deleted Firebase app: {self.app_name}")
            except Exception as e:
                logger.debug(f"Error deleting Firebase app: {e}")
            finally:
                self._app = None
                self._db = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()