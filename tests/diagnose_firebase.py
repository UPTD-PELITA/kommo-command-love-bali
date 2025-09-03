#!/usr/bin/env python3
"""Firebase connection diagnostic tool."""

import sys
import json
import requests
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kommo_lang_select.config import Settings
from kommo_lang_select.firebase_auth import TokenManager


def test_firebase_connection():
    """Test Firebase connection with detailed diagnostics."""
    print("🔍 Firebase Connection Diagnostics")
    print("=" * 50)
    
    # Load settings
    settings = Settings.from_env()
    print(f"📍 Firebase URL: {settings.firebase_database_url}")
    print(f"🔑 Service Account: {settings.google_service_account_file}")
    print()
    
    # Test token generation
    token_manager = TokenManager(settings.google_service_account_file, settings.google_access_token)
    token = token_manager.get_token()
    
    if not token:
        print("❌ Failed to generate OAuth token")
        return False
    
    print("✅ OAuth token generated successfully")
    print(f"🎫 Token length: {len(token)} characters")
    print()
    
    # Test token validity
    session = requests.Session()
    try:
        token_info_resp = session.get(
            f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}",
            timeout=10
        )
        if token_info_resp.status_code == 200:
            token_info = token_info_resp.json()
            print("✅ Token validation successful")
            print(f"📋 Scope: {token_info.get('scope', 'unknown')}")
            print(f"👤 Audience: {token_info.get('audience', 'unknown')}")
            print(f"⏰ Expires in: {token_info.get('expires_in', 'unknown')} seconds")
        else:
            print(f"❌ Token validation failed: {token_info_resp.status_code}")
            print(f"📄 Response: {token_info_resp.text}")
            return False
    except Exception as e:
        print(f"❌ Token validation error: {e}")
        return False
    
    print()
    
    # Test Firebase connection
    firebase_url = f"{settings.firebase_database_url.rstrip('/')}/.json"
    print(f"🎯 Testing Firebase connection to: {firebase_url}")
    
    params = {
        "print": "pretty",
        "shallow": "true",
        "access_token": token
    }
    
    try:
        resp = session.get(firebase_url, params=params, timeout=10)
        print(f"📊 HTTP Status: {resp.status_code}")
        print(f"📋 Response Headers: {dict(resp.headers)}")
        print(f"📄 Response Body: {resp.text[:500]}")
        
        if resp.status_code == 200:
            print("✅ Firebase connection successful!")
            return True
        elif resp.status_code == 401:
            print("❌ Authentication failed (401)")
            print("💡 Possible causes:")
            print("  - Firebase Realtime Database not enabled")
            print("  - Service account lacks permissions")
            print("  - Project doesn't exist or is disabled")
            print("  - Security rules deny access")
        elif resp.status_code == 403:
            print("❌ Access forbidden (403)")
            print("💡 Service account needs Firebase permissions")
        elif resp.status_code == 404:
            print("❌ Database not found (404)")
            print("💡 Firebase Realtime Database may not be enabled")
        else:
            print(f"❌ Unexpected error: {resp.status_code}")
        
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    success = test_firebase_connection()
    sys.exit(0 if success else 1)