"""
Conversation business logic service with enhanced error handling and efficiency.

This service layer handles all conversation-related business logic,
acting as an intermediary between the API layer and storage layer.
Provides comprehensive error handling, validation, and optimization.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from contextlib import asynccontextmanager

from ..storage.firestore_conversation_store import FirestoreConversationStore
from ..storage.mock_conversation_store import MockConversationStore
from ..agents.multi_agent_system import MultiAgentSystem
from .models import (
    ConversationRequest,
    ConversationResponse,
    ConversationMeta,
    ConversationMessage,
    ConversationFull,
    ConversationMessageCreate,
    ConversationTitleUpdate,
    MessageRole,
)
from .utils import (
    derive_conversation_title,
    sanitize_message_content,
    generate_session_id,
    validate_user_id,
    format_chat_history_for_agents,
    generate_preview_text,
    extract_restaurant_keywords,
    calculate_conversation_priority,
)

logger = logging.getLogger(__name__)


class ConversationServiceError(Exception):
    """Base exception for conversation service errors."""
    pass


class StorageUnavailableError(ConversationServiceError):
    """Raised when storage backend is unavailable."""
    pass


class ConversationNotFoundError(ConversationServiceError):
    """Raised when a requested conversation doesn't exist."""
    pass


class InvalidRequestError(ConversationServiceError):
    """Raised when request validation fails."""
    pass


class ConversationService:
    """
    Enhanced service layer for conversation management.
    
    Provides robust business logic for:
    - Processing chat requests with validation and error handling
    - Managing conversation metadata with intelligent title generation
    - Storing and retrieving messages with efficient queries
    - Coordinating with AI agents and handling failures gracefully
    - Background task management for optimization
    """
    
    def __init__(self, storage: Optional[FirestoreConversationStore] = None, 
                 multi_agent_system: Optional[MultiAgentSystem] = None,
                 max_concurrent_requests: int = 10):
        """
        Initialize the conversation service with enhanced configuration.
        
        Args:
            storage: Optional storage backend, creates default if None
            multi_agent_system: Optional AI system, creates default if None
            max_concurrent_requests: Maximum concurrent chat processing requests
        """
        self.storage = storage
        self.multi_agent_system = multi_agent_system or MultiAgentSystem()
        self.max_concurrent_requests = max_concurrent_requests
        self._request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Initialize storage with automatic fallback
        if storage is None:
            try:
                self.storage = FirestoreConversationStore()
                logger.info("✅ Initialized FirestoreConversationStore successfully")
            except Exception as e:
                logger.warning(f"⚠️ Firestore unavailable: {e}")
                logger.info("🔄 Falling back to MockConversationStore for development")
                try:
                    self.storage = MockConversationStore()
                    logger.info("✅ MockConversationStore initialized successfully")
                except Exception as mock_error:
                    logger.error(f"❌ Failed to initialize mock storage: {mock_error}")
                    self.storage = None
    
    def _validate_storage(self) -> None:
        """Validate that storage is available."""
        if not self.storage:
            raise StorageUnavailableError("Conversation storage is not available")
    
    def _validate_user_id(self, user_id: Optional[str]) -> None:
        """Validate user ID format."""
        if user_id and not validate_user_id(user_id):
            raise InvalidRequestError(f"Invalid user ID format: {user_id}")
    
    @asynccontextmanager
    async def _rate_limited_request(self):
        """Context manager for rate-limited request processing."""
        async with self._request_semaphore:
            yield
    
    async def process_chat_request(self, request: ConversationRequest) -> ConversationResponse:
        """
        Process a chat request through the AI system with enhanced error handling and persistence.
        
        Args:
            request: The validated conversation request
            
        Returns:
            The conversation response with session ID and processing metadata
            
        Raises:
            InvalidRequestError: If request validation fails
            ConversationServiceError: If processing fails
        """
        # Validate request
        self._validate_user_id(request.user_id)
        
        session_id = request.session_id or generate_session_id()
        logger.info(f"🚀 Processing chat request for session: {session_id}")
        
        async with self._rate_limited_request():
            try:
                # Format history for AI agents
                formatted_history = format_chat_history_for_agents(request.history or [])
                
                # Process through AI agents with timeout protection
                start_time = datetime.now(timezone.utc)
                result = await asyncio.wait_for(
                    self.multi_agent_system.handle_conversation(
                        user_input=request.user_input,
                        session_id=session_id,
                        history=formatted_history
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"✅ Chat processed in {processing_time:.2f}s for session {session_id}")
                
                # Persist conversation if user authenticated and storage available
                if request.user_id and self.storage:
                    # Run persistence in background to not block response
                    asyncio.create_task(
                        self._persist_conversation_safe(request, session_id, result)
                    )
                
                return ConversationResponse(**result)
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Chat request timeout for session {session_id}")
                raise ConversationServiceError("Request processing timeout")
            except Exception as e:
                logger.error(f"❌ Error processing chat request for session {session_id}: {e}")
                raise ConversationServiceError(f"Failed to process chat request: {str(e)}")
    
    async def _persist_conversation_safe(self, request: ConversationRequest, 
                                       session_id: str, result: Dict[str, Any]) -> None:
        """Safely persist conversation with error handling."""
        try:
            await self._persist_conversation(request, session_id, result)
        except Exception as e:
            logger.warning(f"⚠️ Failed to persist conversation {session_id}: {e}")
    
    async def _persist_conversation(self, request: ConversationRequest, 
                                   session_id: str, result: Dict[str, Any]) -> None:
        """
        Persist the conversation to storage.
        
        Args:
            request: Original request
            session_id: Session identifier
            result: AI response result
        """
        try:
            user_id = request.user_id
            now = datetime.now(timezone.utc)
            
            # Derive conversation title
            title = derive_conversation_title(request.history or [], request.user_input)
            
            # Ensure conversation metadata exists
            self.storage.upsert(user_id, {
                "id": session_id,
                "title": title,
                "created_at": None,  # Will be preserved if exists
                "updated_at": now.isoformat(),
            })
            
            # Save user message
            user_message = {
                "role": "user",
                "content": sanitize_message_content(request.user_input),
                "timestamp": now.isoformat(),
                "restaurant_suggestions": []
            }
            self.storage.add_message(user_id, session_id, user_message)
            
            # Save assistant message
            assistant_message = {
                "role": "assistant",
                "content": sanitize_message_content(result.get("response", "")),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "restaurant_suggestions": [
                    r.dict() for r in (result.get("suggestions", []))
                ]
            }
            self.storage.add_message(user_id, session_id, assistant_message)
            
        except Exception as e:
            logger.warning(f"Failed to persist conversation: {e}")
    
    def list_conversations(self, user_id: str) -> List[ConversationMeta]:
        """
        List conversations for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of conversation metadata
            
        Raises:
            Exception: If storage is unavailable or operation fails
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            items = self.storage.list(user_id)
            return [
                ConversationMeta(
                    id=item["id"],
                    title=item.get("title", "New Search"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    updated_at=datetime.fromisoformat(item["updated_at"]),
                    last_message_preview=item.get("last_message_preview", ""),
                    restaurant_suggestion_names=item.get("restaurant_suggestion_names", []),
                    total_restaurant_suggestions=item.get("total_restaurant_suggestions", 0),
                    restaurant_photo_urls=item.get("restaurant_photo_urls", []),
                )
                for item in items
            ]
        except Exception as e:
            logger.error(f"Failed to list conversations for user {user_id}: {e}")
            raise
    
    def get_conversation_full(self, user_id: str, conversation_id: str) -> Optional[ConversationFull]:
        """
        Get a complete conversation with all messages.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            
        Returns:
            Complete conversation or None if not found
            
        Raises:
            Exception: If storage is unavailable
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            conv_data = self.storage.get_conversation_full(user_id, conversation_id)
            if not conv_data:
                return None
            
            messages = [
                ConversationMessage(
                    id=msg.get("id"),
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else datetime.now(timezone.utc),
                    restaurant_suggestions=msg.get("restaurant_suggestions", [])
                )
                for msg in conv_data.get("messages", [])
            ]
            
            return ConversationFull(
                id=conv_data["id"],
                title=conv_data.get("title", "New Search"),
                created_at=datetime.fromisoformat(conv_data["created_at"]),
                updated_at=datetime.fromisoformat(conv_data["updated_at"]),
                message_count=conv_data.get("message_count", 0),
                messages=messages
            )
            
        except Exception as e:
            logger.error(f"Failed to get full conversation {conversation_id}: {e}")
            raise
    
    def get_conversation_messages(self, user_id: str, conversation_id: str, 
                                 limit: Optional[int] = None) -> List[ConversationMessage]:
        """
        Get messages for a conversation.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            limit: Optional limit on number of messages
            
        Returns:
            List of conversation messages
            
        Raises:
            Exception: If storage is unavailable
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            messages_data = self.storage.get_messages(user_id, conversation_id, limit)
            return [
                ConversationMessage(
                    id=msg.get("id"),
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else datetime.now(timezone.utc),
                    restaurant_suggestions=msg.get("restaurant_suggestions", [])
                )
                for msg in messages_data
            ]
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            raise
    
    def add_message(self, user_id: str, conversation_id: str, 
                   message: ConversationMessageCreate) -> ConversationMessage:
        """
        Add a message to an existing conversation.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            message: Message to add
            
        Returns:
            The added message with generated ID
            
        Raises:
            Exception: If storage is unavailable
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            timestamp = message.timestamp or datetime.now(timezone.utc)
            
            message_data = {
                "role": message.role,
                "content": sanitize_message_content(message.content),
                "timestamp": timestamp.isoformat(),
                "restaurant_suggestions": [
                    r.dict() for r in (message.restaurant_suggestions or [])
                ]
            }
            
            saved_message = self.storage.add_message(user_id, conversation_id, message_data)
            
            return ConversationMessage(
                id=saved_message.get("id"),
                role=saved_message.get("role", "user"),
                content=saved_message.get("content", ""),
                timestamp=datetime.fromisoformat(saved_message["timestamp"]) if saved_message.get("timestamp") else datetime.now(timezone.utc),
                restaurant_suggestions=saved_message.get("restaurant_suggestions", [])
            )
            
        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            raise
    
    def update_conversation_title(self, user_id: str, conversation_id: str, new_title: str) -> ConversationMeta:
        """
        Update the title of an existing conversation.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            new_title: New title for the conversation
            
        Returns:
            Updated conversation metadata
            
        Raises:
            Exception: If storage is unavailable or conversation not found
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            # Update just the title and updated_at timestamp
            update_data = {
                "id": conversation_id,
                "title": new_title.strip() or "New Search",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            stored = self.storage.upsert(user_id, update_data)
            return ConversationMeta(
                id=stored["id"],
                title=stored.get("title", "New Search"),
                created_at=datetime.fromisoformat(stored["created_at"]),
                updated_at=datetime.fromisoformat(stored["updated_at"]),
                last_message_preview=stored.get("last_message_preview", ""),
            )
        except Exception as e:
            logger.error(f"Failed to update conversation title {conversation_id}: {e}")
            raise

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            Exception: If storage is unavailable
        """
        if not self.storage:
            raise Exception("Conversation storage is not available")
        
        try:
            return self.storage.delete(user_id, conversation_id)
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise
