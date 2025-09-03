"""Test script for Kommo API service."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from kommo_lang_select.services import KommoAPIService, KommoAPIError
from kommo_lang_select.config import Settings


def test_kommo_api_service():
    """Test the Kommo API service with environment variables."""
    try:
        # Load settings from environment
        settings = Settings.from_env()
        
        # Initialize Kommo API service
        kommo_service = KommoAPIService(
            client_id=settings.kommo_client_id,
            client_secret=settings.kommo_client_secret,
            subdomain=settings.kommo_subdomain,
            access_token=settings.kommo_access_token,
        )
        
        print("Testing Kommo API connection...")
        
        # Test connection
        if kommo_service.test_connection():
            print("✓ Connection test successful")
        else:
            print("✗ Connection test failed")
            return
        
        # Test getting account info
        print("\nGetting account information...")
        account_info = kommo_service.get_account_info()
        print(f"Account ID: {account_info.get('id')}")
        print(f"Account Name: {account_info.get('name')}")
        print(f"Subdomain: {account_info.get('subdomain')}")
        
        # Test getting pipelines
        print("\nGetting pipelines...")
        pipelines = kommo_service.get_pipelines()
        if '_embedded' in pipelines and 'pipelines' in pipelines['_embedded']:
            pipeline_list = pipelines['_embedded']['pipelines']
            print(f"Found {len(pipeline_list)} pipelines:")
            for pipeline in pipeline_list[:3]:  # Show first 3
                print(f"  - {pipeline.get('name')} (ID: {pipeline.get('id')})")
        
        # Test getting leads (first page)
        print("\nGetting leads (first 5)...")
        leads = kommo_service.get_leads(limit=5)
        if '_embedded' in leads and 'leads' in leads['_embedded']:
            lead_list = leads['_embedded']['leads']
            print(f"Found {len(lead_list)} leads on this page:")
            for lead in lead_list:
                print(f"  - {lead.get('name')} (ID: {lead.get('id')})")
        else:
            print("No leads found")
        
        # Test getting custom fields
        print("\nGetting custom fields for leads...")
        custom_fields = kommo_service.get_custom_fields('leads')
        if '_embedded' in custom_fields and 'custom_fields' in custom_fields['_embedded']:
            field_list = custom_fields['_embedded']['custom_fields']
            print(f"Found {len(field_list)} custom fields:")
            for field in field_list[:3]:  # Show first 3
                print(f"  - {field.get('name')} (ID: {field.get('id')}, Type: {field.get('type')})")
        
        print("\n✓ All tests completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        if hasattr(e, 'status_code'):
            print(f"Status code: {e.status_code}")
        if hasattr(e, 'response_data'):
            print(f"Response data: {e.response_data}")
    
    finally:
        if 'kommo_service' in locals():
            kommo_service.close()


if __name__ == "__main__":
    test_kommo_api_service()