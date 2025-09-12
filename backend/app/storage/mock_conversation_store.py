"""
Mock conversation store for development and testing.

This provides an in-memory implementation of the conversation storage interface
for use when Firestore is not available or for testing purposes.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class MockConversationStore:
    """
    In-memory conversation store for development and testing.
    
    Provides the same interface as FirestoreConversationStore but stores
    everything in memory. Data is lost when the application restarts.
    """
    
    def __init__(self):
        """Initialize the mock store with empty data structures."""
        # Store conversations: {user_id: {conversation_id: conversation_data}}
        self._conversations: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        # Store messages: {user_id: {conversation_id: [messages]}}
        self._messages: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))
        logger.info("✅ Initialized MockConversationStore for development")
    
    def list(self, user_id: str) -> List[Dict]:
        """
        Lists all conversations for a user, ordered by most recently updated.
        Generates previews from actual messages.
        """
        conversations = list(self._conversations[user_id].values())
        
        # Generate previews for each conversation
        for conv in conversations:
            conv_id = conv["id"]
            messages = self._messages[user_id].get(conv_id, [])
            
            # Generate preview from latest messages
            preview_parts = []
            recent_messages = sorted(messages, key=lambda m: m.get("timestamp", ""), reverse=True)[:2]
            
            for msg in reversed(recent_messages):  # Show chronologically
                role = msg.get("role", "")
                content = msg.get("content", "")
                
                if role == "user":
                    user_preview = content[:30] + "..." if len(content) > 30 else content
                    preview_parts.insert(0, f"You: {user_preview}")
                elif role == "assistant":
                    ai_preview = content[:50] + "..." if len(content) > 50 else content
                    preview_parts.append(f"AI: {ai_preview}")
            
            conv["last_message_preview"] = "\n".join(preview_parts) if preview_parts else ""
            conv["message_count"] = len(messages)
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations
    
    def upsert(self, user_id: str, meta: Dict) -> Dict:
        """Creates or updates a conversation's metadata."""
        conv_id = meta.get("id")
        if not conv_id:
            raise ValueError("Conversation 'id' is required")
        
        existing = self._conversations[user_id].get(conv_id, {})
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Prepare conversation data
        conversation_data = {
            "id": conv_id,
            "title": meta.get("title") or existing.get("title", "New Search"),
            "created_at": meta.get("created_at") or existing.get("created_at", now_iso),
            "updated_at": meta.get("updated_at", now_iso),
            "message_count": meta.get("message_count") or existing.get("message_count", 0),
        }
        
        self._conversations[user_id][conv_id] = conversation_data
        
        # Return with preview for compatibility
        result = conversation_data.copy()
        result["last_message_preview"] = meta.get("last_message_preview", "")
        return result
    
    def delete(self, user_id: str, conversation_id: str) -> bool:
        """Deletes a specific conversation."""
        if conversation_id not in self._conversations[user_id]:
            return False
        
        # Delete conversation metadata
        del self._conversations[user_id][conversation_id]
        
        # Delete associated messages
        if conversation_id in self._messages[user_id]:
            del self._messages[user_id][conversation_id]
        
        return True
    
    def clear(self, user_id: str) -> None:
        """Deletes all conversations for a user."""
        self._conversations[user_id].clear()
        self._messages[user_id].clear()
    
    def add_message(self, user_id: str, conversation_id: str, message: Dict) -> Dict:
        """Adds a message to a conversation."""
        # Prepare message data
        message_data = {
            "id": str(uuid.uuid4()),
            "role": message.get("role", "user"),
            "content": message.get("content", ""),
            "timestamp": message.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "restaurant_suggestions": message.get("restaurant_suggestions", [])
        }
        
        # Add to messages
        self._messages[user_id][conversation_id].append(message_data)
        
        # Update conversation metadata
        if conversation_id in self._conversations[user_id]:
            self._conversations[user_id][conversation_id]["updated_at"] = message_data["timestamp"]
            self._conversations[user_id][conversation_id]["message_count"] = len(self._messages[user_id][conversation_id])
        
        return self._message_to_api(message_data)
    
    def get_messages(self, user_id: str, conversation_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieves messages for a conversation."""
        messages = self._messages[user_id].get(conversation_id, [])
        
        # Sort by timestamp
        messages.sort(key=lambda m: m.get("timestamp", ""))
        
        if limit:
            messages = messages[-limit:]  # Get most recent messages
        
        return [self._message_to_api(msg) for msg in messages]
    
    def get_conversation_full(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Retrieves a complete conversation including metadata and all messages."""
        if conversation_id not in self._conversations[user_id]:
            return None
        
        conv_data = self._conversations[user_id][conversation_id].copy()
        messages = self.get_messages(user_id, conversation_id)
        conv_data["messages"] = messages
        
        return conv_data
    
    def save_conversation_batch(self, user_id: str, conversation_id: str, 
                               messages: List[Dict], metadata: Optional[Dict] = None) -> Dict:
        """Saves multiple messages to a conversation in a batch operation."""
        # Add each message
        for message in messages:
            self.add_message(user_id, conversation_id, message)
        
        # Update metadata if provided
        if metadata and conversation_id in self._conversations[user_id]:
            if "title" in metadata:
                self._conversations[user_id][conversation_id]["title"] = metadata["title"]
        
        return self._conversations[user_id].get(conversation_id, {})
    
    def _message_to_api(self, msg_data: Dict) -> Dict:
        """Converts a message dictionary to API format."""
        return {
            "id": msg_data.get("id", ""),
            "role": msg_data.get("role", "user"),
            "content": msg_data.get("content", ""),
            "timestamp": msg_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "restaurant_suggestions": msg_data.get("restaurant_suggestions", [])
        }
    
    def get_stats(self) -> Dict:
        """Get storage statistics (development helper)."""
        total_conversations = sum(len(convs) for convs in self._conversations.values())
        total_messages = sum(
            sum(len(msgs) for msgs in user_msgs.values()) 
            for user_msgs in self._messages.values()
        )
        
        return {
            "type": "mock",
            "total_users": len(self._conversations),
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "status": "active"
        }
