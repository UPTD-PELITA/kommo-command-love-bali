from __future__ import annotations

import logging
import signal
import sys
import threading
import time

from dotenv import load_dotenv

from .config import Settings
from .config_validator import print_config_help, validate_firebase_config
from .services import FirebaseAdminListener, FirestoreService, KommoAPIService
from .service_factory import create_kommo_service, create_firestore_service, create_firebase_listener
from .handlers import HandlerManager, IncomingLeadHandler, IncomingMessageHandler
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
    logger.info("Starting Firebase services", extra={
        "database_url": settings.firebase_database_url,
        "path": settings.firebase_path,
        "project_id": settings.firebase_project_id,
        "firestore_db": settings.firestore_database_name,
    })

    if not settings.firebase_database_url:
        logger.error("FIREBASE_DATABASE_URL is required and was not provided")
        logger.error("Please set the FIREBASE_DATABASE_URL environment variable or create a .env file")
        logger.error("Example: FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com")
        sys.exit(2)

    if not settings.firebase_project_id:
        logger.error("FIREBASE_PROJECT_ID is required and was not provided")
        logger.error("Please set the FIREBASE_PROJECT_ID environment variable or create a .env file")
        logger.error("Example: FIREBASE_PROJECT_ID=your-project-id")
        sys.exit(2)

    if not settings.google_service_account_file:
        logger.error("GOOGLE_SERVICE_ACCOUNT_FILE is required for Firebase Admin SDK")
        logger.error("Please set the GOOGLE_SERVICE_ACCOUNT_FILE environment variable")
        logger.error("Example: GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/serviceAccountKey.json")
        sys.exit(2)

    # Validate Kommo configuration
    try:
        if not settings.kommo_client_id:
            logger.error("KOMMO_CLIENT_ID is required")
            sys.exit(2)
        if not settings.kommo_client_secret:
            logger.error("KOMMO_CLIENT_SECRET is required")
            sys.exit(2)
        if not settings.kommo_subdomain:
            logger.error("KOMMO_SUBDOMAIN is required")
            sys.exit(2)
        if not settings.kommo_access_token:
            logger.error("KOMMO_ACCESS_TOKEN is required")
            sys.exit(2)
    except ValueError as e:
        logger.error(f"Kommo configuration error: {e}")
        sys.exit(2)

    # Log configuration for debugging
    logger.info("Configuration loaded", extra={
        "auth_mode": settings.auth_mode(),
        "firebase_path": settings.firebase_path,
        "has_service_account": bool(settings.google_service_account_file),
        "firestore_database": settings.firestore_database_name,
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

    # Initialize services
    realtime_listener = None
    firestore_service = None
    kommo_service = None
    handler_manager = None
    
    try:
        # Initialize Kommo API service
        logger.info("Initializing Kommo API service...")
        kommo_service = create_kommo_service(settings)
        
        # Test the Kommo connection
        logger.info("Testing Kommo API connection...")
        if not kommo_service.test_connection():
            logger.error("Kommo API connection test failed. Please check your configuration.")
            sys.exit(1)
        logger.info("✅ Kommo API connection successful")
        
        # Initialize Realtime Database listener
        logger.info("Initializing Firebase Realtime Database listener...")
        realtime_listener = create_firebase_listener(settings)
        
        # Test the Realtime Database connection
        logger.info("Testing Firebase Realtime Database connection...")
        if not realtime_listener.test_connection():
            logger.error("Firebase Realtime Database connection test failed. Please check your configuration.")
            sys.exit(1)
        logger.info("✅ Realtime Database connection successful")
        
        # Initialize Firestore service
        logger.info("Initializing Firestore service...")
        firestore_service = create_firestore_service(settings)
        
        # Test the Firestore connection
        logger.info("Testing Firestore connection...")
        if not firestore_service.test_connection():
            logger.error("Firestore connection test failed. Please check your configuration.")
            sys.exit(1)
        logger.info("✅ Firestore connection successful")
        
        # Initialize handler manager and register handlers
        logger.info("Initializing event handler system...")
        handler_manager = HandlerManager()
        
        # Register incoming message handler (logs message payloads)
        incoming_message_handler = IncomingMessageHandler(
            firestore_service=firestore_service,
            realtime_listener=realtime_listener,
            kommo_service=kommo_service,
        )
        handler_manager.register_handler(incoming_message_handler)

        # Register incoming lead handler
        incoming_lead_handler = IncomingLeadHandler(
            firestore_service=firestore_service,
            realtime_listener=realtime_listener,
            kommo_service=kommo_service
        )
        handler_manager.register_handler(incoming_lead_handler)
        
        logger.info("✅ Event handler system initialized")
        logger.info(f"Registered handlers: {[h['name'] for h in handler_manager.get_handler_info()]}")
            
    except Exception as e:
        logger.error(f"Failed to initialize Firebase services: {e}")
        sys.exit(1)

    killer = GracefulKiller()

    try:
        # Signal the services to stop when we receive a shutdown signal
        def signal_services_stop():
            if kommo_service:
                kommo_service.close()
            if realtime_listener:
                realtime_listener.close()
            if firestore_service:
                firestore_service.close()
            if handler_manager:
                handler_manager.clear_handlers()
        
        # Start listening for events in a separate thread so we can handle signals
        event_queue = []
        event_lock = threading.Lock()
        listener_error = [None]  # Use list to allow modification from nested function
        
        def listener_thread():
            try:
                for event in realtime_listener.events():
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
                # Log the raw event for debugging
                logger.info(
                    "Firebase Event Received",
                    extra={
                        "event": event.event,
                        "path": event.path,
                        "data": event.data,
                    },
                )
                
                # Process the event through the handler system
                try:
                    handler_manager.process_event(event.path, event.data)
                except Exception as e:
                    logger.error(f"Error processing event through handlers: {e}", exc_info=True)
                
                # Keep the existing language selection logic as backup/additional processing
                if event.path.endswith('/language') and event.data:
                    logger.info(f"Language selection detected: {event.data}")
                    # Here you could update a session in Firestore based on the event
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
        
        if killer.kill_now.is_set():
            logger.info("Shutdown signal received. Stopping services...")
            signal_services_stop()
            # Wait a bit for the thread to finish
            thread.join(timeout=2.0)
    except Exception:
        logger.exception("Fatal error in listener loop")
        sys.exit(1)
    finally:
        if kommo_service:
            kommo_service.close()
        if realtime_listener:
            realtime_listener.close()
        if firestore_service:
            firestore_service.close()
        logger.info("Services stopped.")
