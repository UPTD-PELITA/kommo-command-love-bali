#!/usr/bin/env python3
"""Test script for the incoming lead handler functionality."""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try to load .env manually
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from kommo_lang_select.config import Settings
from kommo_lang_select.services import FirebaseAdminListener, FirestoreService
from kommo_lang_select.handlers import HandlerManager, IncomingLeadHandler
from kommo_lang_select.logging_setup import configure_logging


def test_incoming_lead_handler():
    """Test the incoming lead handler functionality."""
    
    # Configure logging for testing
    configure_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 Starting Incoming Lead Handler Test")
    
    try:
        # Load settings from environment
        settings = Settings.from_env()
        
        if not all([
            settings.firebase_database_url,
            settings.firebase_project_id,
            settings.google_service_account_file
        ]):
            logger.error("❌ Missing required Firebase configuration")
            logger.error("Please ensure these environment variables are set:")
            logger.error("- FIREBASE_DATABASE_URL")
            logger.error("- FIREBASE_PROJECT_ID") 
            logger.error("- GOOGLE_SERVICE_ACCOUNT_FILE")
            return False
        
        # Initialize services
        logger.info("🔧 Initializing Firebase services...")
        
        realtime_listener = FirebaseAdminListener(
            database_url=settings.firebase_database_url,
            path="/test_leads",  # Use a test path
            service_account_path=settings.google_service_account_file,
        )
        
        firestore_service = FirestoreService(
            project_id=settings.firebase_project_id,
            database_name=settings.firestore_database_name,
            service_account_path=settings.google_service_account_file,
        )
        
        # Test connections
        logger.info("🔗 Testing connections...")
        if not realtime_listener.test_connection():
            logger.error("❌ Realtime Database connection failed")
            return False
        
        if not firestore_service.test_connection():
            logger.error("❌ Firestore connection failed")
            return False
        
        logger.info("✅ All connections successful")
        
        # Initialize handler system
        logger.info("🎯 Setting up handler system...")
        handler_manager = HandlerManager()
        
        incoming_lead_handler = IncomingLeadHandler(
            firestore_service=firestore_service,
            realtime_listener=realtime_listener
        )
        
        handler_manager.register_handler(incoming_lead_handler)
        logger.info("✅ Handler system ready")
        
        # Test data
        test_lead_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "company": "Test Company",
            "source": "website_form",
            "message": "Interested in your services",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0 Test Browser",
                "referrer": "https://google.com"
            }
        }
        
        # Test 1: Write test data to Realtime Database
        logger.info("📝 Test 1: Writing test lead data to Realtime Database...")
        test_path = "/test_leads/test_lead_001"
        
        success = realtime_listener.write_data(test_lead_data, test_path)
        if not success:
            logger.error("❌ Failed to write test data")
            return False
        
        logger.info("✅ Test data written successfully")
        
        # Test 2: Manually trigger the handler
        logger.info("⚡ Test 2: Manually triggering handler...")
        
        try:
            handler_manager.process_event(test_path, test_lead_data)
            logger.info("✅ Handler executed successfully")
        except Exception as e:
            logger.error(f"❌ Handler execution failed: {e}")
            return False
        
        # Test 3: Verify data was saved to Firestore
        logger.info("🔍 Test 3: Verifying data in Firestore...")
        
        leads_collection = firestore_service.get_collection_reference('leads')
        leads_query = leads_collection.where('source_path', '==', test_path)
        leads_docs = list(leads_query.stream())
        
        if not leads_docs:
            logger.error("❌ No leads found in Firestore")
            return False
        
        lead_doc = leads_docs[0]
        lead_data = lead_doc.to_dict()
        
        logger.info(f"✅ Found lead in Firestore: {lead_doc.id}")
        logger.info(f"   - Processed: {lead_data.get('processed', False)}")
        logger.info(f"   - Source path: {lead_data.get('source_path')}")
        logger.info(f"   - Lead name: {lead_data.get('data', {}).get('name')}")
        
        # Test 4: Verify data was deleted from Realtime Database
        logger.info("🗑️  Test 4: Verifying data cleanup from Realtime Database...")
        
        remaining_data = realtime_listener.read_data(test_path)
        if remaining_data is not None:
            logger.warning(f"⚠️  Data still exists in Realtime DB: {remaining_data}")
        else:
            logger.info("✅ Data successfully cleaned up from Realtime Database")
        
        # Test 5: Get handler statistics
        logger.info("📊 Test 5: Getting handler statistics...")
        
        stats = incoming_lead_handler.get_lead_stats()
        logger.info(f"📈 Lead Statistics:")
        logger.info(f"   - Total leads: {stats.get('total_leads', 0)}")
        logger.info(f"   - Processed leads: {stats.get('processed_leads', 0)}")
        logger.info(f"   - Processing rate: {stats.get('processing_rate', 0):.1f}%")
        
        # Cleanup test data from Firestore
        logger.info("🧹 Cleaning up test data...")
        for doc in leads_docs:
            doc.reference.delete()
        
        logger.info("🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return False
    
    finally:
        # Cleanup
        try:
            if 'realtime_listener' in locals():
                realtime_listener.close()
            if 'firestore_service' in locals():
                firestore_service.close()
        except:
            pass


if __name__ == "__main__":
    success = test_incoming_lead_handler()
    sys.exit(0 if success else 1)