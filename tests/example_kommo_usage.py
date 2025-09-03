"""Example usage of the Kommo API service."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from kommo_command.services import KommoAPIService
from kommo_command.config import Settings


def example_kommo_operations():
    """Example of various Kommo API operations."""
    
    # Load settings from environment
    settings = Settings.from_env()
    
    # Create Kommo service
    with KommoAPIService(
        client_id=settings.kommo_client_id,
        client_secret=settings.kommo_client_secret,
        subdomain=settings.kommo_subdomain,
        access_token=settings.kommo_access_token,
    ) as kommo:
        
        print("🔗 Testing Kommo API connection...")
        if not kommo.test_connection():
            print("❌ Connection failed!")
            return
        print("✅ Connection successful!")
        
        # Get account info
        print("\n📊 Account Information:")
        account = kommo.get_account_info()
        print(f"   Account: {account.get('name')}")
        print(f"   Subdomain: {account.get('subdomain')}")
        print(f"   Country: {account.get('country')}")
        
        # Get pipelines
        print("\n🔄 Pipelines:")
        pipelines = kommo.get_pipelines()
        if '_embedded' in pipelines:
            for pipeline in pipelines['_embedded']['pipelines']:
                print(f"   • {pipeline.get('name')} (ID: {pipeline.get('id')})")
                
                # Show statuses for this pipeline
                if 'statuses' in pipeline['_embedded']:
                    for status in pipeline['_embedded']['statuses']:
                        print(f"     - {status.get('name')} (ID: {status.get('id')})")
        
        # Get recent leads
        print("\n👥 Recent Leads (last 5):")
        leads = kommo.get_leads(limit=5)
        if '_embedded' in leads and 'leads' in leads['_embedded']:
            for lead in leads['_embedded']['leads']:
                print(f"   • {lead.get('name')} (ID: {lead.get('id')})")
                print(f"     Status: {lead.get('status_id')}")
                print(f"     Created: {lead.get('created_at')}")
        
        # Get custom fields for leads
        print("\n🏷️  Custom Fields for Leads:")
        custom_fields = kommo.get_custom_fields('leads')
        if '_embedded' in custom_fields and 'custom_fields' in custom_fields['_embedded']:
            for field in custom_fields['_embedded']['custom_fields'][:5]:  # Show first 5
                print(f"   • {field.get('name')} (ID: {field.get('id')}, Type: {field.get('type')})")
        
        # Example: Create a new lead
        print("\n➕ Creating a test lead...")
        new_lead_data = [{
            "name": "Test Lead from API",
            "status_id": 142,  # You'll need to use a valid status ID from your pipelines
            "responsible_user_id": 504141,  # You'll need to use a valid user ID
            "custom_fields_values": [
                {
                    "field_code": "EMAIL",
                    "values": [{"value": "test@example.com"}]
                },
                {
                    "field_code": "PHONE",
                    "values": [{"value": "+1234567890"}]
                }
            ]
        }]
        
        try:
            new_lead_response = kommo.create_lead(new_lead_data)
            if '_embedded' in new_lead_response and 'leads' in new_lead_response['_embedded']:
                created_lead = new_lead_response['_embedded']['leads'][0]
                lead_id = created_lead['id']
                print(f"✅ Created test lead with ID: {lead_id}")
                
                # Update the lead
                print(f"🔄 Updating lead {lead_id}...")
                update_data = [{
                    "name": "Updated Test Lead from API",
                    "custom_fields_values": [
                        {
                            "field_name": "Notes",
                            "values": [{"value": "This lead was created and updated via API"}]
                        }
                    ]
                }]
                
                update_response = kommo.update_lead(lead_id, update_data)
                print(f"✅ Updated lead {lead_id}")
                
        except Exception as e:
            print(f"❌ Error creating/updating lead: {e}")


if __name__ == "__main__":
    try:
        example_kommo_operations()
    except Exception as e:
        print(f"❌ Example failed: {e}")
        if hasattr(e, 'status_code'):
            print(f"Status code: {e.status_code}")
        if hasattr(e, 'response_data'):
            print(f"Response data: {e.response_data}")