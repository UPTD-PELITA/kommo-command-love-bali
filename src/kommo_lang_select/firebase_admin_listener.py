from __future__ import annotations

import logging
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)


@dataclass
class FirebaseEvent:
    event: str
    path: str
    data: object


class FirebaseAdminListener:
    """Firebase Realtime Database listener using Firebase Admin SDK."""
    
    def __init__(
        self,
        database_url: str,
        path: str = "/",
        service_account_path: str | None = None,
        app_name: str | None = None,
    ) -> None:
        self.database_url = database_url.rstrip("/")
        self.path = path if path.startswith("/") else f"/{path}"
        self.service_account_path = service_account_path
        self.app_name = app_name or f"firebase_listener_{id(self)}"
        self._app = None
        self._closed = threading.Event()
        self._listeners = []
        self._initialize_app()
        
    def _initialize_app(self) -> None:
        """Initialize Firebase Admin SDK app."""
        if not self.service_account_path:
            raise ValueError("Service account path is required for Firebase Admin SDK")
            
        try:
            # Check if app already exists
            try:
                existing_app = firebase_admin.get_app(self.app_name)
                firebase_admin.delete_app(existing_app)
                logger.debug(f"Deleted existing Firebase app: {self.app_name}")
            except ValueError:
                pass  # App doesn't exist, which is fine
            
            # Initialize new app
            cred = credentials.Certificate(self.service_account_path)
            self._app = firebase_admin.initialize_app(cred, {
                'databaseURL': self.database_url
            }, name=self.app_name)
            
            logger.info(f"Initialized Firebase app: {self.app_name}")
            logger.info(f"Database URL: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase app: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the Firebase connection."""
        try:
            ref = db.reference(self.path, app=self._app)
            
            # Try to read data
            logger.info(f"Testing connection to path: {self.path}")
            data = ref.get()
            
            # Try to write test data
            test_ref = ref.child('_connection_test')
            test_ref.set({
                'timestamp': time.time(),
                'message': 'Connection test successful'
            })
            logger.info("Write test successful")
            
            # Clean up test data
            test_ref.delete()
            logger.info("Test data cleaned up")
            
            logger.info("Firebase Admin SDK connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Firebase connection test failed: {e}")
            return False

    def read_data(self, path: str | None = None) -> Any:
        """Read data from Firebase at the specified path."""
        target_path = path or self.path
        try:
            ref = db.reference(target_path, app=self._app)
            data = ref.get()
            logger.info(f"Successfully read data from path: {target_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to read data from path {target_path}: {e}")
            raise

    def write_data(self, data: Any, path: str | None = None) -> bool:
        """Write data to Firebase at the specified path."""
        target_path = path or self.path
        try:
            ref = db.reference(target_path, app=self._app)
            ref.set(data)
            logger.info(f"Successfully wrote data to path: {target_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write data to path {target_path}: {e}")
            return False

    def push_data(self, data: Any, path: str | None = None) -> str | None:
        """Push data to Firebase (creates a new child with auto-generated key)."""
        target_path = path or self.path
        try:
            ref = db.reference(target_path, app=self._app)
            new_ref = ref.push(data)
            key = new_ref.key
            logger.info(f"Successfully pushed data to path: {target_path}, key: {key}")
            return key
        except Exception as e:
            logger.error(f"Failed to push data to path {target_path}: {e}")
            return None

    def listen_for_changes(self, callback: callable) -> None:
        """Listen for changes in Firebase data."""
        def listener_callback(event):
            """Internal callback wrapper."""
            if self._closed.is_set():
                return
                
            firebase_event = FirebaseEvent(
                event=event.event_type,
                path=event.path,
                data=event.data
            )
            
            # Log event data to console
            print(f"\n🔥 Firebase Event Detected:")
            print(f"   Event Type: {firebase_event.event}")
            print(f"   Path: {firebase_event.path}")
            print(f"   Data: {firebase_event.data}")
            print("-" * 50)
            
            logger.info(f"Firebase event: {firebase_event.event} at {firebase_event.path}")
            logger.debug(f"Event data: {firebase_event.data}")
            
            try:
                callback(firebase_event)
            except Exception as e:
                logger.error(f"Error in user callback: {e}")

        try:
            ref = db.reference(self.path, app=self._app)
            
            # Add listener for value changes
            listener = ref.listen(listener_callback)
            self._listeners.append(listener)
            
            logger.info(f"Started listening for changes at path: {self.path}")
            
        except Exception as e:
            logger.error(f"Failed to start listener: {e}")
            raise

    def events(self) -> Generator[FirebaseEvent, None, None]:
        """Generator that yields Firebase events (for compatibility with existing code)."""
        events_queue = []
        events_lock = threading.Lock()
        
        def callback(event):
            with events_lock:
                events_queue.append(event)
        
        # Start listening
        self.listen_for_changes(callback)
        
        # Yield events as they come
        try:
            while not self._closed.is_set():
                with events_lock:
                    if events_queue:
                        event = events_queue.pop(0)
                        
                        # Log event data to console
                        print(f"\n🔥 Firebase Event (Generator):")
                        print(f"   Event Type: {event.event}")
                        print(f"   Path: {event.path}")
                        print(f"   Data: {event.data}")
                        print("-" * 50)
                        
                        yield event
                
                # Short sleep to prevent busy waiting
                time.sleep(0.1)
        finally:
            self.close()

    def close(self) -> None:
        """Close the listener and clean up resources."""
        self._closed.set()
        
        # Remove all listeners
        for listener in self._listeners:
            try:
                listener.close()
            except Exception as e:
                logger.debug(f"Error closing listener: {e}")
        
        self._listeners.clear()
        
        # Delete Firebase app
        if self._app:
            try:
                firebase_admin.delete_app(self._app)
                logger.info(f"Deleted Firebase app: {self.app_name}")
            except Exception as e:
                logger.debug(f"Error deleting Firebase app: {e}")
            finally:
                self._app = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()