from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import logging
import uuid

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
                message_count: number
              Subcollection: messages
                Document: <message_id> (auto-generated)
                  Fields:
                    role: string ('user' | 'assistant')
                    content: string
                    timestamp: Firestore Timestamp (stored as datetime)
                    restaurant_suggestions: array (optional)
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
    
    def _msgs_col(self, user_id: str, conv_id: str) -> "CollectionReference":
        """Gets a reference to the messages subcollection for a conversation."""
        return (
            self.client.collection("users")
            .document(user_id)
            .collection("conversations")
            .document(conv_id)
            .collection("messages")
        )

    def list(self, user_id: str) -> List[Dict]:
        """
        Lists all conversations for a user, ordered by most recently updated.
        Includes a preview generated from the latest messages.

        Args:
            user_id: The ID of the user.

        Returns:
            A list of conversation metadata dictionaries with previews.
        """
        docs = (
            self._convs_col(user_id)
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        
        conversations = []
        for doc in docs:
            conv_data = _to_api(doc)
            
            # Generate preview from latest messages
            try:
                latest_messages = (
                    self._msgs_col(user_id, conv_data["id"])
                    .order_by("timestamp", direction=firestore.Query.DESCENDING)
                    .limit(2)  # Get last user and assistant message
                    .stream()
                )
                
                preview_parts = []
                for msg_doc in latest_messages:
                    msg_data = msg_doc.to_dict() or {}
                    role = msg_data.get("role", "")
                    content = msg_data.get("content", "")
                    
                    if role == "user":
                        user_preview = content[:30] + "..." if len(content) > 30 else content
                        preview_parts.insert(0, f"You: {user_preview}")
                    elif role == "assistant":
                        ai_preview = content[:50] + "..." if len(content) > 50 else content
                        preview_parts.append(f"AI: {ai_preview}")
                
                conv_data["last_message_preview"] = "\n".join(preview_parts) if preview_parts else ""
                
            except Exception as e:
                logger.warning(f"Failed to generate preview for conversation {conv_data['id']}: {e}")
                conv_data["last_message_preview"] = ""
            
            conversations.append(conv_data)
        
        return conversations

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
            "message_count": meta.get("message_count") or existing.get("message_count", 0),
        }
        doc_ref.set(payload, merge=True)
        
        # Return with generated preview for compatibility
        result = _to_api(payload)
        result["last_message_preview"] = meta.get("last_message_preview", "")
        return result

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
    
    # --- Message Management Methods ---
    
    def add_message(self, user_id: str, conversation_id: str, message: Dict) -> Dict:
        """
        Adds a message to a conversation.

        Args:
            user_id: The ID of the user.
            conversation_id: The ID of the conversation.
            message: A dictionary containing message data (role, content, timestamp, etc.).

        Returns:
            The added message as a dictionary with generated ID.
        """
        msgs_col = self._msgs_col(user_id, conversation_id)
        
        # Prepare message data
        now_dt = datetime.now(timezone.utc)
        message_data = {
            "role": message.get("role", "user"),
            "content": message.get("content", ""),
            "timestamp": _ensure_dt(message.get("timestamp", now_dt)),
            "restaurant_suggestions": message.get("restaurant_suggestions", [])
        }
        
        # Add message to subcollection
        doc_ref = msgs_col.add(message_data)[1]
        message_data["id"] = doc_ref.id
        
        # Update conversation metadata
        conv_ref = self._conv_ref(user_id, conversation_id)
        conv_ref.update({
            "updated_at": now_dt,
            "message_count": firestore.Increment(1)
        })
        
        return _message_to_api(message_data)
    
    def get_messages(self, user_id: str, conversation_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Retrieves messages for a conversation.

        Args:
            user_id: The ID of the user.
            conversation_id: The ID of the conversation.
            limit: Optional limit on number of messages to retrieve.

        Returns:
            A list of message dictionaries ordered by timestamp.
        """
        query = (
            self._msgs_col(user_id, conversation_id)
            .order_by("timestamp", direction=firestore.Query.ASCENDING)
        )
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        messages = []
        for doc in docs:
            msg_data = doc.to_dict() or {}
            msg_data["id"] = doc.id
            messages.append(_message_to_api(msg_data))
        
        return messages
    
    def get_conversation_full(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """
        Retrieves a complete conversation including metadata and all messages.

        Args:
            user_id: The ID of the user.
            conversation_id: The ID of the conversation.

        Returns:
            A dictionary containing conversation metadata and messages, or None if not found.
        """
        # Get conversation metadata
        conv_ref = self._conv_ref(user_id, conversation_id)
        conv_snap = conv_ref.get()
        if not conv_snap.exists:
            return None
        
        conv_data = _to_api(conv_snap)
        
        # Get all messages
        messages = self.get_messages(user_id, conversation_id)
        
        conv_data["messages"] = messages
        return conv_data
    
    def save_conversation_batch(self, user_id: str, conversation_id: str, 
                               messages: List[Dict], metadata: Optional[Dict] = None) -> Dict:
        """
        Saves multiple messages to a conversation in a batch operation.

        Args:
            user_id: The ID of the user.
            conversation_id: The ID of the conversation.
            messages: List of message dictionaries to save.
            metadata: Optional conversation metadata to update.

        Returns:
            Updated conversation metadata.
        """
        batch = self.client.batch()
        msgs_col = self._msgs_col(user_id, conversation_id)
        
        # Add each message
        for message in messages:
            msg_data = {
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
                "timestamp": _ensure_dt(message.get("timestamp", datetime.now(timezone.utc))),
                "restaurant_suggestions": message.get("restaurant_suggestions", [])
            }
            doc_ref = msgs_col.document()  # Auto-generate ID
            batch.set(doc_ref, msg_data)
        
        # Update conversation metadata
        conv_ref = self._conv_ref(user_id, conversation_id)
        update_data = {
            "updated_at": datetime.now(timezone.utc),
            "message_count": firestore.Increment(len(messages))
        }
        
        if metadata:
            if "title" in metadata:
                update_data["title"] = metadata["title"]
        
        batch.update(conv_ref, update_data)
        
        # Commit the batch
        batch.commit()
        
        # Return updated conversation metadata
        conv_snap = conv_ref.get()
        return _to_api(conv_snap) if conv_snap.exists else {}


def _message_to_api(msg_data: Dict) -> Dict:
    """
    Converts a message dictionary to an API-safe dictionary.

    Args:
        msg_data: The message data dictionary.

    Returns:
        A dictionary with serializable values for message data.
    """
    return {
        "id": msg_data.get("id", ""),
        "role": msg_data.get("role", "user"),
        "content": msg_data.get("content", ""),
        "timestamp": _ensure_iso(msg_data.get("timestamp")),
        "restaurant_suggestions": msg_data.get("restaurant_suggestions", [])
    }


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
        "message_count": data.get("message_count", 0),
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

