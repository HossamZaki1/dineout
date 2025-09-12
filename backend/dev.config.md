# Development Configuration Guide

## Storage Options

The backend now supports automatic storage fallback:

1. **Production**: Uses Firestore with Google Cloud credentials
2. **Development**: Automatically falls back to in-memory MockConversationStore

## Configuration Options

### Environment Variables

Create a `.env` file in the backend directory with:

```bash
# API Configuration
API_URL=http://localhost:8080
HOST=0.0.0.0
PORT=8080

# Storage Configuration
STORAGE_TYPE=auto  # auto, mock, or firestore

# For Firestore (production)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id

# AI Configuration
GOOGLE_API_KEY=your-api-key

# Development
DEBUG=true
LOG_LEVEL=INFO
```

### Storage Behavior

- **No credentials**: Automatically uses MockConversationStore
- **With credentials**: Uses FirestoreConversationStore
- **Manual override**: Set `STORAGE_TYPE=mock` to force mock storage

## Health Check

Visit `/conversations/health` to see current storage status:

```json
{
  "service": "conversation",
  "status": "healthy",
  "storage": {
    "type": "mock",
    "total_users": 0,
    "total_conversations": 0,
    "total_messages": 0,
    "status": "active"
  }
}
```

## Development Benefits

- ✅ No setup required - works out of the box
- ✅ Full conversation features available locally
- ✅ Data persists during development session
- ✅ Easy debugging with in-memory storage
- ✅ Automatic fallback - no manual configuration needed
