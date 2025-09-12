"""
Conversation-specific data models with comprehensive validation and documentation.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from ..models.request_models import RestaurantInfo


class MessageRole(str, Enum):
    """Enumeration of valid message roles."""
    USER = "user"
    ASSISTANT = "assistant"


class ConversationIntent(str, Enum):
    """Enumeration of conversation intents."""
    SEARCH_RESTAURANTS = "search_restaurants"
    GENERAL_CONVERSATION = "general_conversation"
    GREETING = "greeting"
    HELP = "help"
    CLARIFICATION = "clarification"
    INFORMATION = "information"
    FEEDBACK = "feedback"


class ConversationRequest(BaseModel):
    """
    Request model for conversational interaction.
    
    Validates user input and manages conversation context.
    """
    user_input: str = Field(
        ..., 
        min_length=1,
        max_length=5000,
        description="The user's message to the chatbot"
    )
    session_id: Optional[str] = Field(
        None, 
        description="Existing session ID to maintain conversation context"
    )
    history: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Previous conversation messages for context"
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID for persisting conversation data"
    )

    @field_validator('user_input')
    @classmethod
    def validate_user_input(cls, v):
        """Validate and sanitize user input."""
        if not v or not v.strip():
            raise ValueError('User input cannot be empty')
        return v.strip()

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """Validate session ID format if provided."""
        if v is not None:
            try:
                # Check if it's a valid UUID format
                uuid.UUID(v)
            except ValueError:
                raise ValueError('Session ID must be a valid UUID')
        return v

    @field_validator('history')
    @classmethod
    def validate_history(cls, v):
        """Validate conversation history format."""
        if v is None:
            return []
        
        for i, msg in enumerate(v):
            if not isinstance(msg, dict):
                raise ValueError(f'History item {i} must be a dictionary')
            if 'role' not in msg or 'content' not in msg:
                raise ValueError(f'History item {i} must have role and content fields')
            if msg['role'] not in ['user', 'assistant']:
                raise ValueError(f'History item {i} has invalid role: {msg["role"]}')
        
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "Find me Italian restaurants in San Francisco",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi! How can I help you find restaurants?"}
                ],
                "user_id": "user_123"
            }
        }


class ConversationResponse(BaseModel):
    """
    Response model for conversational interaction.
    
    Contains AI response with restaurant suggestions and metadata.
    """
    session_id: str = Field(..., description="Session identifier")
    intent: str = Field(..., description="Detected conversation intent")
    response: str = Field(..., min_length=1, description="AI response text")
    suggestions: List[RestaurantInfo] = Field(
        default_factory=list,
        description="Restaurant suggestions (if any)"
    )
    processing_time_seconds: float = Field(
        ..., 
        ge=0,
        description="Time taken to process the request"
    )

    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v):
        """Validate and normalize intent values."""
        if not v:
            return "general_conversation"
        
        # Normalize common intent variations
        intent_lower = v.lower().strip()
        
        # Map variations to standard intents
        intent_mapping = {
            'search': 'search_restaurants',
            'find': 'search_restaurants',
            'restaurant': 'search_restaurants',
            'restaurants': 'search_restaurants',
            'lookup': 'search_restaurants',
            'hi': 'greeting',
            'hello': 'greeting',
            'hey': 'greeting',
            'clarify': 'clarification',
            'explain': 'clarification',
            'info': 'information',
            'question': 'information',
        }
        
        # Check for direct mapping
        if intent_lower in intent_mapping:
            return intent_mapping[intent_lower]
        
        # Check for partial matches
        for key, mapped_intent in intent_mapping.items():
            if key in intent_lower:
                return mapped_intent
        
        # Return original value if no mapping found
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "intent": "search_restaurants",
                "response": "I found 3 great Italian restaurants in San Francisco for you!",
                "suggestions": [],
                "processing_time_seconds": 2.35
            }
        }


class ConversationMeta(BaseModel):
    """
    Conversation metadata model.
    
    Contains summary information about a conversation.
    """
    id: str = Field(..., description="Unique conversation identifier")
    title: str = Field(..., min_length=1, max_length=100, description="Conversation title")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(..., description="When the conversation was last updated")
    last_message_preview: str = Field(
        default="",
        max_length=500,
        description="Preview of the latest conversation exchange"
    )
    message_count: int = Field(default=0, ge=0, description="Total number of messages")
    restaurant_suggestion_names: List[str] = Field(
        default_factory=list,
        description="Names of restaurants suggested in this conversation"
    )
    total_restaurant_suggestions: int = Field(
        default=0, 
        ge=0, 
        description="Total count of restaurant suggestions"
    )
    restaurant_photo_urls: List[str] = Field(
        default_factory=list,
        description="Photo URLs of restaurants suggested in this conversation"
    )

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate and clean conversation title."""
        if not v or not v.strip():
            return "New Search"
        return v.strip()

    @model_validator(mode='after')
    def validate_timestamps(self):
        """Ensure created_at is not after updated_at."""
        if self.created_at and self.updated_at and self.created_at > self.updated_at:
            raise ValueError('created_at cannot be after updated_at')
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Italian restaurants in San Francisco",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
                "last_message_preview": "You: Italian restaurants in SF\nAI: I found 3 great options...",
                "message_count": 4,
                "restaurant_suggestion_names": ["Tony's Little Star Pizza", "North Beach Restaurant", "Perbacco"],
                "total_restaurant_suggestions": 3,
                "restaurant_photo_urls": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]
            }
        }


class ConversationMessage(BaseModel):
    """
    A single message in a conversation.
    
    Represents either a user input or assistant response.
    """
    id: Optional[str] = Field(None, description="Message ID (auto-generated)")
    role: MessageRole = Field(..., description="Message sender role")
    content: str = Field(
        ..., 
        min_length=1,
        max_length=10000,
        description="Message content"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the message was created"
    )
    restaurant_suggestions: Optional[List[RestaurantInfo]] = Field(
        None,
        description="Restaurant suggestions included with this message"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate and sanitize message content."""
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v.strip()

    @field_validator('restaurant_suggestions')
    @classmethod
    def validate_suggestions(cls, v):
        """Validate restaurant suggestions list."""
        if v is None:
            return []
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_123",
                "role": "user",
                "content": "Find me sushi restaurants nearby",
                "timestamp": "2024-01-15T10:30:00Z",
                "restaurant_suggestions": []
            }
        }


class ConversationFull(BaseModel):
    """
    Complete conversation including metadata and all messages.
    
    Used for retrieving full conversation history.
    """
    id: str = Field(..., description="Conversation identifier")
    title: str = Field(..., description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(ge=0, description="Total message count")
    messages: List[ConversationMessage] = Field(
        default_factory=list,
        description="All conversation messages"
    )

    @model_validator(mode='after')
    def validate_message_count(self):
        """Ensure message_count matches actual messages length."""
        if len(self.messages) != self.message_count:
            # Auto-correct the count to match actual messages
            self.message_count = len(self.messages)
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Restaurant search conversation",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
                "message_count": 2,
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "content": "Find Italian restaurants",
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                ]
            }
        }


class ConversationMessageCreate(BaseModel):
    """
    Request model for adding a message to a conversation.
    
    Used when manually adding messages to existing conversations.
    """
    role: MessageRole = Field(..., description="Message sender role")
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Message content"
    )
    restaurant_suggestions: Optional[List[RestaurantInfo]] = Field(
        None,
        description="Optional restaurant suggestions"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Message timestamp (auto-generated if not provided)"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate and sanitize message content."""
        return v.strip() if v else ""

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What about Mexican restaurants?",
                "restaurant_suggestions": None,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ConversationTitleUpdate(BaseModel):
    """Request model for updating conversation title."""
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New conversation title"
    )

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate and clean the new title."""
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Best Pizza Places in NYC"
            }
        }
