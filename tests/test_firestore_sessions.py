"""Test script for Firestore sessions functionality."""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kommo_command.config import Settings
from kommo_command.services import FirestoreService
from kommo_command.models import SessionCreateRequest, SessionUpdateRequest
from kommo_command.types import Command
from kommo_command.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def main():
    """Test Firestore sessions functionality."""
    # Load .env file
    load_dotenv()
    
    # Setup logging
    configure_logging("INFO")
    
    logger.info("🔥 Testing Firestore Sessions Setup")
    logger.info("=" * 50)
    
    try:
        # Load configuration
        settings = Settings.from_env()
        logger.info(f"Project ID: {settings.firebase_project_id}")
        logger.info(f"Database: {settings.firestore_database_name}")
        logger.info(f"Auth mode: {settings.auth_mode()}")
        
        # Initialize Firestore service
        firestore_service = FirestoreService(
            project_id=settings.firebase_project_id,
            database_name=settings.firestore_database_name,
            service_account_path=settings.google_service_account_file
        )
        
        # Test connection
        logger.info("\n🧪 Testing Firestore connection...")
        if firestore_service.test_connection():
            logger.info("✅ Firestore connection successful!")
        else:
            logger.error("❌ Firestore connection failed!")
            return
        
        # Test session creation
        logger.info("\n📝 Testing session creation...")
        session_request = SessionCreateRequest(
            entity_id="test_entity_123",
            language="en",
            command=Command.LANG_SELECT,
            expires_in_hours=24,
            metadata={"source": "test_script", "ip": "127.0.0.1"}
        )
        
        session = firestore_service.create_session(session_request)
        logger.info(f"✅ Created session: {session.session_id}")
        logger.info(f"   Entity ID: {session.entity_id}")
        logger.info(f"   Language: {session.language}")
        logger.info(f"   Command: {session.command}")
        logger.info(f"   Created: {session.created_at}")
        logger.info(f"   Expires: {session.expires_at}")
        
        # Test session retrieval
        logger.info("\n📖 Testing session retrieval...")
        retrieved_session = firestore_service.get_session(session.session_id)
        if retrieved_session:
            logger.info(f"✅ Retrieved session: {retrieved_session.session_id}")
            logger.info(f"   Active: {retrieved_session.is_active}")
            logger.info(f"   Expired: {retrieved_session.is_expired()}")
        else:
            logger.error("❌ Failed to retrieve session!")
        
        # Test session update
        logger.info("\n✏️ Testing session update...")
        update_request = SessionUpdateRequest(
            language="fr",
            command=Command.MAIN_MENU,
            metadata={"updated_by": "test_script", "last_action": "language_change"}
        )
        
        updated_session = firestore_service.update_session(session.session_id, update_request)
        if updated_session:
            logger.info(f"✅ Updated session: {updated_session.session_id}")
            logger.info(f"   New language: {updated_session.language}")
            logger.info(f"   New command: {updated_session.command}")
            logger.info(f"   Updated at: {updated_session.updated_at}")
        else:
            logger.error("❌ Failed to update session!")
        
        # Test getting sessions by entity
        logger.info("\n👤 Testing get sessions by entity...")
        entity_sessions = firestore_service.get_sessions_by_user("test_entity_123")
        logger.info(f"✅ Found {len(entity_sessions)} sessions for entity test_entity_123")
        
        # Create another session for the same entity
        logger.info("\n📝 Creating another session for the same entity...")
        session_request2 = SessionCreateRequest(
            entity_id="test_entity_123",
            language="de",
            command=Command.LOVE_BALI,
            expires_in_hours=12,
            metadata={"source": "test_script_2", "device": "mobile"}
        )
        
        session2 = firestore_service.create_session(session_request2)
        logger.info(f"✅ Created second session: {session2.session_id}")
        
        # Get all sessions for the entity again
        entity_sessions = firestore_service.get_sessions_by_user("test_entity_123")
        logger.info(f"✅ Now found {len(entity_sessions)} sessions for entity test_entity_123")
        
        # Test cleanup
        logger.info("\n🧹 Testing session cleanup...")
        cleaned_count = firestore_service.cleanup_expired_sessions()
        logger.info(f"✅ Cleaned up {cleaned_count} expired sessions")
        
        # Test session deletion
        logger.info("\n🗑️ Testing session deletion...")
        if firestore_service.delete_session(session.session_id):
            logger.info(f"✅ Deleted session: {session.session_id}")
        else:
            logger.error("❌ Failed to delete session!")
        
        if firestore_service.delete_session(session2.session_id):
            logger.info(f"✅ Deleted session: {session2.session_id}")
        else:
            logger.error("❌ Failed to delete second session!")
        
        # Verify deletion
        logger.info("\n🔍 Verifying session deletion...")
        deleted_session = firestore_service.get_session(session.session_id)
        if deleted_session is None:
            logger.info("✅ Session successfully deleted (not found)")
        else:
            logger.error("❌ Session still exists after deletion!")
        
        logger.info("\n🎉 All tests completed successfully!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        raise
    
    finally:
        # Clean up
        if 'firestore_service' in locals():
            firestore_service.close()


if __name__ == "__main__":
    main()