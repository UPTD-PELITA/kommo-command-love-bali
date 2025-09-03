#!/usr/bin/env python3
"""
Test script to verify the salesbot fix works with the exact parameters from the working example.
"""

import os
import json
from dotenv import load_dotenv

from src.kommo_lang_select.services.kommo_api_service import KommoAPIService
from src.kommo_lang_select.config import Settings

def test_salesbot_fix():
    """Test the fixed salesbot functionality with real parameters."""
    # Load environment variables from .env file
    load_dotenv()
    
    try:
        # Load configuration from environment variables
        settings = Settings.from_env()
        
        service = KommoAPIService(
            client_id=settings.kommo_client_id,
            client_secret=settings.kommo_client_secret, 
            subdomain=settings.kommo_subdomain,
            access_token=settings.kommo_access_token
        )
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("💡 Make sure you have a .env file with the required Kommo API variables")
        return
    
    print("✅ KommoAPIService initialized successfully")
    print(f"📡 Using subdomain: {settings.kommo_subdomain}")
    
    # Test with the exact parameters from your working example
    try:
        print("\n🚀 Testing salesbot launch with the exact working parameters...")
        result = service.launch_salesbot(
            bot_id=66624,
            entity_id=17332060,
            entity_type='2'
        )
        
        print("✅ SUCCESS! Salesbot launched successfully!")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error launching salesbot: {e}")
        if hasattr(e, 'status_code'):
            print(f"📊 HTTP Status Code: {e.status_code}")
        if hasattr(e, 'response_data'):
            print(f"📊 Response Data: {json.dumps(e.response_data, indent=2)}")
    
    finally:
        service.close()
        print("\n🔒 API session closed")

def test_multiple_salesbots():
    """Test launching multiple salesbots at once."""
    load_dotenv()
    
    try:
        settings = Settings.from_env()
        service = KommoAPIService(
            client_id=settings.kommo_client_id,
            client_secret=settings.kommo_client_secret, 
            subdomain=settings.kommo_subdomain,
            access_token=settings.kommo_access_token
        )
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return
    
    print("\n🚀 Testing multiple salesbot launches...")
    
    try:
        # Test multiple bots (with hypothetical IDs)
        bot_requests = [
            {'bot_id': 66624, 'entity_id': 17332060, 'entity_type': '2'},
            # Add more requests here if you have more valid IDs
        ]
        
        result = service.launch_multiple_salesbots(bot_requests)
        print("✅ SUCCESS! Multiple salesbots launched successfully!")
        print(f"📊 Result: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error launching multiple salesbots: {e}")
        if hasattr(e, 'status_code'):
            print(f"📊 HTTP Status Code: {e.status_code}")
    
    finally:
        service.close()

if __name__ == "__main__":
    test_salesbot_fix()
    # test_multiple_salesbots()