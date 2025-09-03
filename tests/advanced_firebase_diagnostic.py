#!/usr/bin/env python3
"""Advanced Firebase connection diagnostic tool."""

import sys
import json
import requests
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kommo_command.config import Settings
# from kommo_command.firebase_auth import TokenManager  # TODO: Implement or remove


def check_service_account_info():
    """Check service account details."""
    print("🔍 Service Account Analysis")
    print("=" * 50)
    
    settings = Settings.from_env()
    
    try:
        with open(settings.google_service_account_file, 'r') as f:
            sa_data = json.load(f)
        
        print(f"📧 Client Email: {sa_data.get('client_email')}")
        print(f"🆔 Project ID: {sa_data.get('project_id')}")
        print(f"🔑 Private Key ID: {sa_data.get('private_key_id', 'N/A')[:8]}...")
        print(f"📅 Type: {sa_data.get('type')}")
        print()
        
        return sa_data
    except Exception as e:
        print(f"❌ Error reading service account: {e}")
        return None


def test_multiple_database_urls(token):
    """Test different possible database URL formats."""
    print("🎯 Testing Multiple Database URL Formats")
    print("=" * 50)
    
    # Different possible URL formats for your project
    urls_to_test = [
        "https://orang-berbakat-default-rtdb.firebaseio.com",
        "https://orang-berbakat.firebaseio.com", 
        "https://kommo-webhook.firebaseio.com",
        "https://kommo-webhook-default-rtdb.firebaseio.com",
        "https://orang-berbakat-default-rtdb.asia-southeast1.firebasedatabase.app",
        "https://kommo-webhook.asia-southeast1.firebasedatabase.app"
    ]
    
    successful_urls = []
    
    for url in urls_to_test:
        print(f"Testing: {url}")
        
        try:
            firebase_url = f"{url}/.json"
            params = {
                "print": "pretty",
                "shallow": "true", 
                "access_token": token
            }
            
            resp = requests.get(firebase_url, params=params, timeout=10)
            
            if resp.status_code == 200:
                print(f"  ✅ SUCCESS - {resp.status_code}")
                successful_urls.append(url)
            elif resp.status_code == 401:
                print(f"  ❌ UNAUTHORIZED - {resp.status_code}")
            elif resp.status_code == 404:
                print(f"  ❌ NOT FOUND - {resp.status_code}")
            elif resp.status_code == 403:
                print(f"  ❌ FORBIDDEN - {resp.status_code}")
            else:
                print(f"  ❓ UNKNOWN - {resp.status_code}")
                
        except Exception as e:
            print(f"  ❌ ERROR - {e}")
        
        print()
    
    return successful_urls


def check_firebase_project_info(token):
    """Check Firebase project information."""
    print("🏗️ Firebase Project Information")
    print("=" * 50)
    
    # Try to get project info from Firebase Management API
    project_id = "orang-berbakat"
    
    try:
        # Try Firebase Management API
        mgmt_url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        resp = requests.get(mgmt_url, headers=headers, timeout=10)
        print(f"📊 Management API Status: {resp.status_code}")
        
        if resp.status_code == 200:
            project_info = resp.json()
            print(f"📋 Project Display Name: {project_info.get('displayName', 'N/A')}")
            print(f"🆔 Project ID: {project_info.get('projectId', 'N/A')}")
            print(f"📍 State: {project_info.get('state', 'N/A')}")
        else:
            print(f"📄 Response: {resp.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error checking project info: {e}")
    
    print()


def main():
    """Main diagnostic function."""
    print("🚀 Advanced Firebase Diagnostics")
    print("=" * 60)
    print()
    
    # Load settings
    settings = Settings.from_env()
    
    # Check service account
    sa_data = check_service_account_info()
    if not sa_data:
        return False
    
    # Generate token
    # token_manager = TokenManager(settings.google_service_account_file, settings.google_access_token)
    # token = token_manager.get_token()
    token = None  # TODO: Implement token generation
    
    if not token:
        print("❌ Token generation not implemented")
        print("💡 Skipping token-based checks")
        return False
    
    print("✅ OAuth token generated successfully")
    print(f"🎫 Token length: {len(token)} characters")
    print()
    
    # Check project info
    # check_firebase_project_info(token)
    
    # Test multiple URLs
    # successful_urls = test_multiple_database_urls(token)
    successful_urls = []
    
    if successful_urls:
        print("🎉 SUCCESS! Working database URLs found:")
        for url in successful_urls:
            print(f"  ✅ {url}")
        print()
        print("💡 Update your .env file with one of these URLs")
        return True
    else:
        print("❌ No working database URLs found")
        print()
        print("💡 Possible solutions:")
        print("  1. Check if Firebase Realtime Database is enabled in Firebase Console")
        print("  2. Verify service account has 'Firebase Realtime Database Admin' role")
        print("  3. Check Firebase security rules allow authenticated access")
        print("  4. Ensure you're using the correct project")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    success = main()
    sys.exit(0 if success else 1)