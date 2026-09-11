"""Storage selection is explicit; production never falls back to memory."""
import os
from google.auth.exceptions import DefaultCredentialsError
from .firestore_conversation_store import FirestoreConversationStore
from .mock_conversation_store import MockConversationStore


def create_store():
    backend = os.getenv("STORAGE_BACKEND", "firestore").lower()
    if backend == "memory":
        if os.getenv("K_SERVICE"):
            raise RuntimeError("Cloud Run requires STORAGE_BACKEND=firestore")
        return MockConversationStore()
    if backend != "firestore":
        raise ValueError("STORAGE_BACKEND must be firestore or memory")
    try:
        return FirestoreConversationStore()
    except DefaultCredentialsError:
        if os.getenv("K_SERVICE"):
            raise RuntimeError(
                "Firestore credentials are unavailable. Attach a runtime service account "
                "to Cloud Run and grant it access to the Firestore project."
            ) from None
        raise RuntimeError(
            "Firestore needs Application Default Credentials. Install the Google Cloud CLI "
            "and run 'gcloud auth application-default login', then restart the backend. "
            "Firebase CLI login does not configure these credentials. For temporary local "
            "storage instead, set STORAGE_BACKEND=memory in backend/.env; that history "
            "is cleared when the backend restarts."
        ) from None
