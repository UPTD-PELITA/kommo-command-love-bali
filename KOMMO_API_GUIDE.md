# Kommo API Service Documentation

This documentation describes the Kommo API service integration that allows your application to interact with the Kommo CRM system via REST API.

## Environment Variables

Add the following environment variables to your `.env` file:

```bash
# Kommo API Configuration
KOMMO_CLIENT_ID=your_client_id_here
KOMMO_CLIENT_SECRET=your_client_secret_here
KOMMO_SUBDOMAIN=your_subdomain_here
KOMMO_ACCESS_TOKEN=your_access_token_here
```

### How to obtain these values:

1. **KOMMO_CLIENT_ID** and **KOMMO_CLIENT_SECRET**:

   - Go to your Kommo account settings
   - Navigate to Integrations → API
   - Create a new integration or use an existing one
   - Copy the Client ID and Client Secret

2. **KOMMO_SUBDOMAIN**:

   - This is your account subdomain (e.g., if your Kommo URL is `https://example.kommo.com`, then `example` is your subdomain)

3. **KOMMO_ACCESS_TOKEN**:
   - Use the OAuth 2.0 flow to obtain an access token
   - Alternatively, for testing, you can generate a temporary token in your Kommo settings

## Usage

### Basic Service Initialization

```python
from kommo_command.services import KommoAPIService
from kommo_command.config import Settings

# Load settings from environment
settings = Settings.from_env()

# Create service instance
kommo_service = KommoAPIService(
    client_id=settings.kommo_client_id,
    client_secret=settings.kommo_client_secret,
    subdomain=settings.kommo_subdomain,
    access_token=settings.kommo_access_token,
)

# Test connection
if kommo_service.test_connection():
    print("Connected successfully!")
else:
    print("Connection failed!")

# Don't forget to close the service when done
kommo_service.close()
```

### Using Context Manager (Recommended)

```python
with KommoAPIService(
    client_id=settings.kommo_client_id,
    client_secret=settings.kommo_client_secret,
    subdomain=settings.kommo_subdomain,
    access_token=settings.kommo_access_token,
) as kommo:
    # Service will be automatically closed when exiting the context
    account_info = kommo.get_account_info()
    print(f"Account: {account_info['name']}")
```

## API Methods

### General Methods

- `get(endpoint, params=None, headers=None)` - Make GET request
- `post(endpoint, data=None, params=None, headers=None)` - Make POST request
- `patch(endpoint, data=None, params=None, headers=None)` - Make PATCH request
- `delete(endpoint, params=None, headers=None)` - Make DELETE request
- `test_connection()` - Test API connection

### Lead Operations

```python
# Get leads
leads = kommo.get_leads(page=1, limit=50)

# Get specific lead
lead = kommo.get_lead(lead_id=12345, with_fields=['contacts'])

# Create lead
new_lead_data = [{
    "name": "New Lead",
    "status_id": 142,
    "responsible_user_id": 504141,
    "custom_fields_values": [
        {
            "field_code": "EMAIL",
            "values": [{"value": "lead@example.com"}]
        }
    ]
}]
response = kommo.create_lead(new_lead_data)

# Update lead
update_data = [{"name": "Updated Lead Name"}]
response = kommo.update_lead(lead_id=12345, lead_data=update_data)
```

### Contact Operations

```python
# Get contacts
contacts = kommo.get_contacts(page=1, limit=50)

# Get specific contact
contact = kommo.get_contact(contact_id=12345)

# Create contact
new_contact_data = [{
    "name": "John Doe",
    "custom_fields_values": [
        {
            "field_code": "EMAIL",
            "values": [{"value": "john@example.com"}]
        }
    ]
}]
response = kommo.create_contact(new_contact_data)
```

### Company Operations

```python
# Get companies
companies = kommo.get_companies(page=1, limit=50)
```

### System Information

```python
# Get account information
account = kommo.get_account_info()

# Get pipelines and statuses
pipelines = kommo.get_pipelines()

# Get custom fields
custom_fields = kommo.get_custom_fields('leads')  # or 'contacts', 'companies'
```

## Error Handling

The service includes comprehensive error handling:

```python
from kommo_command.services import KommoAPIError, KommoRateLimitError, KommoAuthenticationError

try:
    leads = kommo.get_leads()
except KommoAuthenticationError as e:
    print("Authentication failed - check your access token")
except KommoRateLimitError as e:
    print("Rate limit exceeded - please retry later")
except KommoAPIError as e:
    print(f"API error: {e}")
    print(f"Status code: {e.status_code}")
    print(f"Response: {e.response_data}")
```

## Integration with Handlers

The Kommo service is automatically integrated with the incoming lead handler. When a lead is processed from Firebase, it can optionally be synced to Kommo:

```python
# In IncomingLeadHandler.handle()
if self.kommo_service:
    try:
        self.sync_lead_to_kommo(lead, event_data)
    except Exception as e:
        self.logger.error(f"Failed to sync lead to Kommo: {e}")
        # Processing continues even if Kommo sync fails
```

## Rate Limiting

The service automatically handles rate limiting:

- Retries requests when rate limit is exceeded
- Respects `Retry-After` headers
- Configurable maximum retries (default: 3)

## Configuration Options

```python
kommo_service = KommoAPIService(
    client_id="...",
    client_secret="...",
    subdomain="...",
    access_token="...",
    timeout=30,        # Request timeout in seconds
    max_retries=3,     # Maximum retry attempts
)
```

## Testing

Run the test script to verify your configuration:

```bash
python test_kommo_api.py
```

Or run the example usage script:

```bash
python example_kommo_usage.py
```

## Common Custom Field Codes

When working with custom fields, you can use these common field codes:

- `EMAIL` - Email field
- `PHONE` - Phone field
- `WEB` - Website field
- `IM` - Instant messenger field

For other custom fields, you can either use:

- `field_id` - The numeric ID of the field
- `field_code` - The field code (if set)
- `field_name` - The field name (less reliable)

## Troubleshooting

1. **Authentication Errors**:

   - Check your access token validity
   - Ensure your client ID and secret are correct
   - Verify your subdomain is correct

2. **Rate Limiting**:

   - The service automatically handles rate limits
   - Consider adding delays between bulk operations

3. **Connection Issues**:

   - Check your internet connection
   - Verify the Kommo API is accessible
   - Check for firewall restrictions

4. **Data Format Issues**:
   - Ensure your data follows Kommo's API format
   - Check field IDs and types
   - Verify required fields are included
