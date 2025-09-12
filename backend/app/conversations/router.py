"""
API router for conversation endpoints.

This module contains all FastAPI endpoints related to conversation management.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

from .models import (
    ConversationRequest,
    ConversationResponse,
    ConversationMeta,
    ConversationMessage,
    ConversationFull,
    ConversationMessageCreate,
    ConversationTitleUpdate,
)
from .service import (
    ConversationService,
    ConversationServiceError,
    StorageUnavailableError,
    ConversationNotFoundError,
    InvalidRequestError,
)

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter(prefix="", tags=["Conversations"])

# Service instance - will be initialized in main.py
conversation_service: Optional[ConversationService] = None


def set_conversation_service(service: ConversationService) -> None:
    """Set the conversation service instance."""
    global conversation_service
    conversation_service = service


def get_conversation_service() -> ConversationService:
    """Get the conversation service instance."""
    if conversation_service is None:
        raise HTTPException(status_code=503, detail="Conversation service is not available")
    return conversation_service


# --- Health and Status Endpoints ---

@router.get("/conversations/health")
async def conversation_health():
    """
    Health check endpoint for conversation service.
    Shows storage status and basic statistics.
    """
    try:
        service = get_conversation_service()
        
        # Get storage type and status
        storage_info = {
            "available": service.storage is not None,
            "type": "unknown"
        }
        
        if service.storage:
            if hasattr(service.storage, 'get_stats'):
                # Mock store has stats
                storage_info.update(service.storage.get_stats())
            elif 'firestore' in str(type(service.storage)).lower():
                storage_info["type"] = "firestore"
                storage_info["status"] = "active"
            else:
                storage_info["type"] = "unknown"
                storage_info["status"] = "active"
        
        return {
            "service": "conversation",
            "status": "healthy" if service.storage else "degraded",
            "storage": storage_info,
            "max_concurrent_requests": service.max_concurrent_requests
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "service": "conversation", 
            "status": "unhealthy",
            "error": str(e)
        }


# --- Chat Endpoint ---

@router.post("/chat", response_model=ConversationResponse, tags=["Chat"])
async def chat(request: ConversationRequest):
    """
    Main endpoint for conversational interaction with the chatbot.
    
    Processes user input through AI agents with comprehensive error handling
    and optionally persists conversation data for authenticated users.
    """
    try:
        service = get_conversation_service()
        return await service.process_chat_request(request)
    except InvalidRequestError as e:
        logger.warning(f"Invalid chat request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConversationServiceError as e:
        logger.error(f"Chat service error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat request")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")


# --- Conversation Metadata Endpoints ---

@router.get("/conversations", response_model=List[ConversationMeta])
async def list_conversations(user_id: str = Query(..., description="User ID to list conversations for")):
    """
    List all conversations for a user, ordered by most recently updated.
    """
    try:
        service = get_conversation_service()
        return service.list_conversations(user_id)
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


@router.patch("/conversations/{conversation_id}/title", response_model=ConversationMeta)
async def update_conversation_title(
    conversation_id: str,
    title_update: ConversationTitleUpdate,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    """
    Update the title of an existing conversation.
    """
    try:
        service = get_conversation_service()
        updated_conversation = service.update_conversation_title(user_id, conversation_id, title_update.title)
        return updated_conversation
    except ConversationNotFoundError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except InvalidRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageUnavailableError:
        raise HTTPException(status_code=503, detail="Conversation storage is not available")
    except Exception as e:
        logger.error(f"Failed to update conversation title: {e}")
        raise HTTPException(status_code=500, detail="Failed to update conversation title")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    """
    Delete a specific conversation.
    """
    try:
        service = get_conversation_service()
        removed = service.delete_conversation(user_id, conversation_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "deleted", "id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")


# --- Full Conversation Endpoints ---

@router.get("/conversations/{conversation_id}/full", response_model=ConversationFull)
async def get_conversation_full(
    conversation_id: str,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    """
    Retrieve a complete conversation including all messages.
    """
    try:
        service = get_conversation_service()
        conversation = service.get_conversation_full(user_id, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve full conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")


@router.get("/conversations/{conversation_id}/messages", response_model=List[ConversationMessage])
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Query(..., description="User ID to scope the conversation"),
    limit: Optional[int] = Query(None, description="Optional limit on number of messages"),
):
    """
    Retrieve messages for a specific conversation.
    """
    try:
        service = get_conversation_service()
        return service.get_conversation_messages(user_id, conversation_id, limit)
    except Exception as e:
        logger.error(f"Failed to retrieve conversation messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationMessage)
async def add_conversation_message(
    conversation_id: str,
    message: ConversationMessageCreate,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    """
    Add a message to an existing conversation.
    """
    try:
        service = get_conversation_service()
        return service.add_message(user_id, conversation_id, message)
    except Exception as e:
        logger.error(f"Failed to add message to conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to add message")
