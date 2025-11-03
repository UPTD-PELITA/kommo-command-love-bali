# kommo-command for Love Bali

##Author
- Kadek Ganeis Jayarani Sapanca https://www.instagram.com/ganeissapancaa/
- I Made Hendra Wijaya https://imadehendrawijaya.com
s

Base project for creating bots that handle Kommo commands, triggered by Firebase Realtime Database changes. Provides session management via Firestore and integrates with Kommo CRM via REST API.

## Features

- **Real-time Event Listening**: Connects to Firebase Realtime Database via Firebase Admin SDK
- **Session Management**: Complete session lifecycle management using Firestore database
- **Kommo CRM Integration**: Full REST API integration with Kommo CRM system
- **Dual Database Support**: Uses both Firebase Realtime Database (for events) and Firestore (for sessions)
- **Authentication**: Service account-based authentication for Firebase services
- **Type Safety**: Fully typed configuration and models using Pydantic
- **Auto-reconnection**: Automatic reconnection with error handling
- **Comprehensive Logging**: Structured logging with configurable levels
- **Event Processing**: Extensible handler system for processing various event types

## Architecture

### Firebase Realtime Database

- Listens for real-time events and changes
- Handles webhooks and live data updates
- Processes language selection events

### Firestore Database (`kommo-webhook`)

- Stores user session data
- Manages session lifecycle (create, read, update, delete)
- Handles session expiration and cleanup
- Supports metadata storage for session context

### Kommo CRM Integration

- REST API integration with Kommo CRM
- Lead synchronization from Firebase events to Kommo
- Contact and company management
- Custom field handling and data transformation
- Automatic error handling and retry logic

## Project Layout

```
src/kommo_command/
├── app.py                      # Main application entry point
├── config.py                   # Environment configuration
├── service_factory.py          # Service factory functions
├── logging_setup.py           # Logging configuration
├── models/                     # Data models
│   ├── session.py             # Session models
│   ├── lead.py                # Lead models
│   └── base.py                # Base model classes
├── services/                   # Service layer
│   ├── firebase_admin_listener.py  # Realtime Database listener
│   ├── firestore_service.py   # Firestore session management
│   └── kommo_api_service.py    # Kommo CRM API integration
└── handlers/                   # Event handlers
    ├── base_handler.py         # Base handler class
    ├── handler_manager.py      # Handler management
    └── incoming_lead_handler.py # Lead processing handler

examples/
├── test_firestore_sessions.py  # Comprehensive test script
├── test_kommo_api.py           # Kommo API test script
├── example_kommo_usage.py      # Kommo usage examples
└── example_sessions.py         # Basic usage example
```

## Requirements

- Python 3.9+
- Firebase project with both Realtime Database and Firestore enabled
- Service account with appropriate permissions

## Setup

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2. Firebase Setup

1. **Create/Configure Firebase Project**:

   - Enable Firebase Realtime Database
   - Enable Firestore Database
   - Create a named database called `kommo-webhook`

2. **Service Account**:
   - Go to Project Settings → Service Accounts
   - Generate new private key (downloads JSON file)
   - Ensure service account has:
     - `Firebase Realtime Database Editor` role
     - `Cloud Datastore Editor` role

### 3. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Firebase Realtime Database
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
FIREBASE_PATH=/

# Firestore Configuration
FIREBASE_PROJECT_ID=your-project-id
FIRESTORE_DATABASE_NAME=kommo-webhook

# Authentication
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/serviceAccountKey.json

# Kommo CRM API Configuration
KOMMO_CLIENT_ID=your_kommo_client_id
KOMMO_CLIENT_SECRET=your_kommo_client_secret
KOMMO_SUBDOMAIN=your_kommo_subdomain
KOMMO_ACCESS_TOKEN=your_kommo_access_token

# Logging
LOG_LEVEL=INFO
```

## Usage

### Running the Application

```bash
# Load environment variables
export $(grep -v '^#' .env | xargs) 2>/dev/null || true

# Run the application
python -m kommo_command
# Or use the console script
kommo-command
```

### Session Management Examples

```python
from kommo_command import FirestoreService, SessionCreateRequest

# Initialize service
firestore = FirestoreService(
    project_id="your-project-id",
    database_name="kommo-webhook",
    service_account_path="/path/to/serviceAccountKey.json"
)

# Create a session
session_request = SessionCreateRequest(
    user_id="user123",
    language="en",
    expires_in_hours=24
)
session = firestore.create_session(session_request)

# Update session language
from kommo_command import SessionUpdateRequest
update = SessionUpdateRequest(language="fr")
updated_session = firestore.update_session(session.session_id, update)
```

### Testing the Setup

Run the comprehensive test scripts:

```bash
# Test Firebase and Firestore
python test_firestore_sessions.py

# Test Kommo API integration
python test_kommo_api.py

# Try Kommo usage examples
python example_kommo_usage.py
```

Or try the basic session example:

```bash
python example_sessions.py
```

## Session Model

Sessions are stored in Firestore with the following structure:

```python
{
    "session_id": "uuid4-generated",
    "user_id": "optional-user-id",
    "language": "en|fr|de|es|...",
    "created_at": "2025-09-02T10:30:00Z",
    "updated_at": "2025-09-02T10:30:00Z",
    "expires_at": "2025-09-03T10:30:00Z",
    "metadata": {"custom": "data"},
    "is_active": true
}
```

### Key Features

- **Automatic Timestamps**: `created_at` and `updated_at` managed automatically
- **Expiration**: Optional session expiration with cleanup utilities
- **Language Tracking**: Built-in language selection support
- **Metadata**: Flexible storage for additional session context
- **Type Safety**: Full Pydantic validation and type hints

## Logging Output

The application provides comprehensive logging:

```
INFO | Starting Firebase services
INFO | ✅ Realtime Database connection successful
INFO | ✅ Firestore connection successful
INFO | 🔥 Firebase Event Detected:
INFO |    Event Type: child_added
INFO |    Path: /languages/user123
INFO |    Data: {"language": "fr"}
INFO | Language selection detected: fr
```

## Documentation

- **[Firestore Setup Guide](FIRESTORE_SETUP.md)** - Detailed setup instructions for Firestore
- **[Kommo API Guide](KOMMO_API_GUIDE.md)** - Complete Kommo CRM integration documentation
- **[API Reference](src/kommo_command/models/)** - Session and lead models with validation
- **[Configuration](src/kommo_command/config.py)** - Environment variables and settings

## Security Notes

- Store service account files securely outside of version control
- Use environment variables for sensitive configuration
- Implement proper Firestore security rules for production
- Regularly rotate service account keys
- Monitor Firebase usage and set up billing alerts

## Troubleshooting

### Common Issues

1. **"Database not found"**: Ensure you've created the `kommo-webhook` database in Firestore
2. **Permission denied**: Verify service account has required roles
3. **Connection timeout**: Check network connectivity and Firebase project status
4. **Import errors**: Ensure all dependencies are installed with `pip install -e .`

### Debug Steps

1. Run test script: `python test_firestore_sessions.py`
2. Check Firebase Console for error logs
3. Verify environment variables: `env | grep FIREBASE`
4. Test service account manually in Firebase Console

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.
