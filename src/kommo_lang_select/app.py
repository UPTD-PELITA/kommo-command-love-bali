from __future__ import annotations

import logging
import signal
import sys
import threading
import time

from dotenv import load_dotenv

from .config import Settings
from .config_validator import print_config_help, validate_firebase_config
from .firebase_admin_listener import FirebaseAdminListener
from .logging_setup import configure_logging


class GracefulKiller:
    def __init__(self) -> None:
        self.kill_now = threading.Event()
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *_: object) -> None:
        self.kill_now.set()


def run(settings: Settings | None = None) -> None:
    # Load .env if present
    load_dotenv()
    settings = settings or Settings.from_env()
    configure_logging(level=settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Firebase Realtime DB listener", extra={
        "database_url": settings.firebase_database_url,
        "path": settings.firebase_path,
    })

    if not settings.firebase_database_url:
        logger.error("FIREBASE_DATABASE_URL is required and was not provided")
        logger.error("Please set the FIREBASE_DATABASE_URL environment variable or create a .env file")
        logger.error("Example: FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com")
        sys.exit(2)

    if not settings.google_service_account_file:
        logger.error("GOOGLE_SERVICE_ACCOUNT_FILE is required for Firebase Admin SDK")
        logger.error("Please set the GOOGLE_SERVICE_ACCOUNT_FILE environment variable")
        logger.error("Example: GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/serviceAccountKey.json")
        sys.exit(2)

    # Log configuration for debugging
    logger.info("Configuration loaded", extra={
        "auth_mode": settings.auth_mode(),
        "firebase_path": settings.firebase_path,
        "has_service_account": bool(settings.google_service_account_file),
    })

    # Validate configuration and show helpful messages
    config_issues = validate_firebase_config(
        settings.firebase_database_url, 
        settings.google_service_account_file
    )
    
    if config_issues:
        logger.warning("Configuration issues detected")
        print_config_help(settings.firebase_database_url, settings.google_service_account_file)
        print()  # Add some spacing

    try:
        listener = FirebaseAdminListener(
            database_url=settings.firebase_database_url,
            path=settings.firebase_path,
            service_account_path=settings.google_service_account_file,
        )
        
        # Test the connection before starting the listener
        logger.info("Testing Firebase connection...")
        if not listener.test_connection():
            logger.error("Firebase connection test failed. Please check your configuration.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Failed to initialize Firebase listener: {e}")
        sys.exit(1)

    killer = GracefulKiller()

    try:
        # Signal the listener to stop when we receive a shutdown signal
        def signal_listener_stop():
            listener.close()
        
        # Start listening for events in a separate thread so we can handle signals
        event_queue = []
        event_lock = threading.Lock()
        listener_error = [None]  # Use list to allow modification from nested function
        
        def listener_thread():
            try:
                for event in listener.events():
                    with event_lock:
                        event_queue.append(event)
                    if killer.kill_now.is_set():
                        break
            except Exception as e:
                listener_error[0] = e
                logger.exception("Fatal error in listener thread")
        
        # Start the listener thread
        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()
        
        # Main loop that can respond to signals
        while not killer.kill_now.is_set() and thread.is_alive():
            # Check for any listener errors
            if listener_error[0]:
                raise listener_error[0]
            
            # Process any queued events
            events_to_process = []
            with event_lock:
                events_to_process = event_queue[:]
                event_queue.clear()
            
            for event in events_to_process:
                # For now, simply log the event. In the future, route to processing.
                logger.info(
                    "Event",
                    extra={
                        "event": event.event,
                        "path": event.path,
                        "data": event.data,
                    },
                )
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
        
        if killer.kill_now.is_set():
            logger.info("Shutdown signal received. Stopping listener...")
            signal_listener_stop()
            # Wait a bit for the thread to finish
            thread.join(timeout=2.0)
    except Exception:
        logger.exception("Fatal error in listener loop")
        sys.exit(1)
    finally:
        listener.close()
        logger.info("Listener stopped.")
