#!/usr/bin/env python3
"""Simple Firebase Admin SDK usage example."""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kommo_lang_select.firebase_admin_listener import FirebaseAdminListener
from kommo_lang_select.config import Settings


def main():
    """Demonstrate Firebase Admin SDK usage."""
    print("🔥 Firebase Admin SDK Example")
    print("=" * 50)
    
    # Load settings
    settings = Settings.from_env()
    
    # Test both databases
    databases = [
        ("Default Database", "https://orang-berbakat-default-rtdb.firebaseio.com/"),
        ("Kommo Webhook Database", "https://kommo-webhook.firebaseio.com/")
    ]
    
    for db_name, db_url in databases:
        print(f"\n📍 Testing {db_name}")
        print(f"🔗 URL: {db_url}")
        
        try:
            # Create Firebase listener
            with FirebaseAdminListener(
                database_url=db_url,
                path="/",
                service_account_path=settings.google_service_account_file
            ) as listener:
                
                # Test connection
                if not listener.test_connection():
                    print(f"❌ Connection test failed for {db_name}")
                    continue
                
                print(f"✅ {db_name} connection successful!")
                
                # Read existing data
                print("📖 Reading current data...")
                data = listener.read_data()
                
                if data is None:
                    print("📄 Database is empty")
                elif isinstance(data, dict):
                    print(f"📄 Database has {len(data)} top-level keys: {list(data.keys())}")
                else:
                    print(f"📄 Database contains: {type(data).__name__}")
                
                # Write some test data
                print("✏️ Writing test data...")
                test_data = {
                    "test_message": "Hello from Python!",
                    "timestamp": "2025-09-02",
                    "status": "connected"
                }
                
                if listener.write_data(test_data, "/python_test"):
                    print("✅ Write successful!")
                    
                    # Read it back
                    written_data = listener.read_data("/python_test")
                    print(f"📖 Read back: {written_data}")
                    
                    # Clean up
                    listener.write_data(None, "/python_test")  # Delete the test data
                    print("🧹 Test data cleaned up")
                else:
                    print("❌ Write failed")
                
                print(f"🎉 {db_name} test completed successfully!")
        
        except Exception as e:
            print(f"❌ Error testing {db_name}: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Firebase Admin SDK is working!")
    print("💡 Use FirebaseAdminListener instead of FirebaseRealtimeListener")
    print("💡 Your service account works with Firebase Admin SDK")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    main()