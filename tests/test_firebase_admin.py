#!/usr/bin/env python3
"""Firebase Admin SDK connection test."""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import firebase_admin
    from firebase_admin import credentials, db
    print("✅ Firebase Admin SDK imported successfully")
except ImportError:
    print("❌ Firebase Admin SDK not installed")
    print("💡 Install with: pip install firebase-admin")
    sys.exit(1)


def test_firebase_admin_sdk():
    """Test Firebase connection using Admin SDK."""
    print("🔥 Firebase Admin SDK Test")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    
    if not service_account_path or not os.path.exists(service_account_path):
        print(f"❌ Service account file not found: {service_account_path}")
        return False
    
    print(f"🔑 Service Account: {service_account_path}")
    
    try:
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        
        # Test different database URLs
        databases_to_test = [
            "https://orang-berbakat-default-rtdb.firebaseio.com/",
            "https://kommo-webhook.firebaseio.com/"
        ]
        
        for db_url in databases_to_test:
            print(f"\n🎯 Testing database: {db_url}")
            
            try:
                # Initialize app with specific database
                app_name = db_url.split('.')[0].split('//')[-1]
                
                # Check if app already exists
                try:
                    firebase_admin.get_app(app_name)
                    firebase_admin.delete_app(firebase_admin.get_app(app_name))
                except ValueError:
                    pass  # App doesn't exist, which is fine
                
                app = firebase_admin.initialize_app(cred, {
                    'databaseURL': db_url
                }, name=app_name)
                
                # Get database reference
                ref = db.reference('/', app=app)
                
                # Try to read from database
                print("📖 Attempting to read from database...")
                data = ref.get()
                
                print(f"✅ SUCCESS! Connected to {db_url}")
                print(f"📊 Data type: {type(data)}")
                
                if data is None:
                    print("📄 Database is empty (which is fine)")
                elif isinstance(data, dict):
                    print(f"📄 Database has {len(data)} top-level keys")
                else:
                    print(f"📄 Database contains: {str(data)[:100]}...")
                
                # Try a simple write test
                print("✏️ Attempting to write test data...")
                test_ref = ref.child('_connection_test')
                import time
                test_ref.set({
                    'timestamp': time.time(),
                    'message': 'Connection test successful'
                })
                print("✅ Write test successful!")
                
                # Clean up test data
                test_ref.delete()
                print("🧹 Test data cleaned up")
                
                # Clean up app
                firebase_admin.delete_app(app)
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to connect to {db_url}")
                print(f"🔍 Error: {str(e)}")
                
                # Clean up if app was created
                try:
                    firebase_admin.delete_app(firebase_admin.get_app(app_name))
                except:
                    pass
                
                continue
        
        print("\n❌ All database connections failed")
        return False
        
    except Exception as e:
        print(f"❌ Firebase Admin SDK initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = test_firebase_admin_sdk()
    
    if success:
        print("\n🎉 Firebase Admin SDK connection successful!")
        print("💡 You can use Firebase Admin SDK instead of REST API")
    else:
        print("\n❌ Firebase Admin SDK connection failed")
        print("💡 Check IAM permissions and database configuration")
    
    sys.exit(0 if success else 1)