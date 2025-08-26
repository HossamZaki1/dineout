from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import logging

# For type-checking, we can import the full types.
# This will be skipped at runtime, so no ImportError will be raised.
if TYPE_CHECKING:
    from google.cloud import firestore
    from google.cloud.firestore_v1.document import DocumentSnapshot
    from google.cloud.firestore_v1.collection import CollectionReference
    from google.cloud.firestore_v1.document import DocumentReference

# For runtime, we handle the case where the library might not be installed.
try:
    from google.cloud import firestore
except ImportError:
    firestore = None  # type: ignore

logger = logging.getLogger(__name__)


class FirestoreConversationStore:
    """
    Firestore-backed store for conversation metadata.

    This class manages conversation metadata in a Firestore database,
    organizing conversations by user ID.

    Schema:
      Collection: users
        Document: <user_id>
          Subcollection: conversations
            Document: <conversation_id>
              Fields:
                id: string
                title: string
                created_at: Firestore Timestamp (stored as datetime)
                updated_at: Firestore Timestamp (stored as datetime)
                last_message_preview: string
    """

    def __init__(self, client: Optional["firestore.Client"] = None):
        """
        Initializes the FirestoreConversationStore.

        Args:
            client: An optional Firestore client instance. If not provided,
                    a new client will be created.
        """
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is not installed")
        self.client = client or firestore.Client()

    def _conv_ref(self, user_id: str, conv_id: str) -> "DocumentReference":
        """Gets a reference to a specific conversation document."""
        return (
            self.client.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conv_id)
        )

    def _convs_col(self, user_id: str) -> "CollectionReference":
        """Gets a reference to the conversations subcollection for a user."""
        return (
            self.client.collection("users")
            .document(user_id)
            .collection("conversations")
        )

    def list(self, user_id: str) -> List[Dict]:
        """
        Lists all conversations for a user, ordered by most recently updated.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of conversation metadata dictionaries.
        """
        docs = (
            self._convs_col(user_id)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [_to_api(d) for d in docs]

    def upsert(self, user_id: str, meta: Dict) -> Dict:
        """
        Creates or updates a conversation's metadata.

        Args:
            user_id: The ID of the user.
            meta: A dictionary containing conversation metadata. Must include 'id'.

        Returns:
            The created or updated conversation metadata as a dictionary.
        """
        conv_id = meta.get("id")
        if not conv_id:
            raise ValueError("Conversation 'id' is required")

        doc_ref = self._conv_ref(user_id, conv_id)
        snap = doc_ref.get()
        existing = snap.to_dict() if snap.exists else {}

        now_dt = datetime.now(timezone.utc)
        payload = {
            "id": conv_id,
            "title": meta.get("title") or existing.get("title", "New Search"),
            "created_at": _ensure_dt(
                meta.get("created_at") or existing.get("created_at", now_dt)
            ),
            "updated_at": _ensure_dt(meta.get("updated_at", now_dt)),
            "last_message_preview": meta.get("last_message_preview")
            or existing.get("last_message_preview", ""),
        }
        doc_ref.set(payload, merge=True)
        return _to_api(payload)

    def delete(self, user_id: str, conversation_id: str) -> bool:
        """
        Deletes a specific conversation.

        Args:
            user_id: The ID of the user.
            conversation_id: The ID of the conversation to delete.

        Returns:
            True if the conversation was deleted, False if it did not exist.
        """
        doc_ref = self._conv_ref(user_id, conversation_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True

    def clear(self, user_id: str) -> None:
        """
        Deletes all conversations for a user.

        Args:
            user_id: The ID of the user whose conversations will be cleared.
        """
        batch = self.client.batch()
        for doc in self._convs_col(user_id).stream():
            batch.delete(doc.reference)
        batch.commit()


def _to_api(d: Union["DocumentSnapshot", Dict]) -> Dict:
    """
    Converts a Firestore document or a dict to an API-safe dictionary.

    Args:
        d: The Firestore DocumentSnapshot or a dictionary.

    Returns:
        A dictionary with serializable values.
    """
    data = {}
    doc_id = ""
    if hasattr(d, "to_dict") and hasattr(d, "id"):
        data = d.to_dict() or {}
        doc_id = d.id
    elif isinstance(d, dict):
        data = d
        doc_id = d.get("id", "")

    return {
        "id": data.get("id", doc_id),
        "title": data.get("title", "New Search"),
        "created_at": _ensure_iso(data.get("created_at")),
        "updated_at": _ensure_iso(data.get("updated_at")),
        "last_message_preview": data.get("last_message_preview", ""),
    }


def _ensure_iso(value: Any) -> str:
    """
    Coerces a value to an ISO 8601 string.

    Handles datetime objects, Firestore Timestamps, and existing ISO strings.
    """
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
        except ValueError:
            pass  # Fallback for non-ISO strings
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "to_datetime"):  # Firestore Timestamp
        return value.to_datetime().isoformat()
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return str(value)


def _ensure_dt(value: Any) -> datetime:
    """
    Coerces a value to a datetime object for Firestore storage.

    Handles datetime objects, Firestore Timestamps, and ISO strings.
    """
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_datetime"):  # Firestore Timestamp
        return value.to_datetime()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)

