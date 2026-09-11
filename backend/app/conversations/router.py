"""Authenticated conversation endpoints with application-scoped dependencies."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..auth import current_user_id
from .models import (ConversationRequest, ConversationResponse, ConversationMeta,
                     ConversationMessage, ConversationFull, ConversationMessageCreate,
                     ConversationTitleUpdate, ConversationPage)
from .service import ConversationService

router = APIRouter(tags=["Conversations"])


def get_conversation_service(request: Request) -> ConversationService:
    service = getattr(request.app.state, "conversation_service", None)
    if service is None:
        raise HTTPException(503, "Conversation service is unavailable")
    return service


@router.get("/conversations/health")
async def conversation_health(service: ConversationService = Depends(get_conversation_service)):
    await service._call(service.storage.check_health)
    return {"status": "healthy", "storage": service.storage.kind}


@router.post("/chat", response_model=ConversationResponse, tags=["Chat"])
async def chat(request: ConversationRequest, user_id: str = Depends(current_user_id),
               service: ConversationService = Depends(get_conversation_service)):
    return await service.process_chat_request(request, user_id)


@router.get("/conversations", response_model=ConversationPage)
async def list_conversations(
    user_id: str = Depends(current_user_id),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1024),
    service: ConversationService = Depends(get_conversation_service),
):
    return await service.list_conversations(user_id, limit, cursor)


@router.patch("/conversations/{conversation_id}/title", response_model=ConversationMeta)
async def update_title(conversation_id: UUID, title: ConversationTitleUpdate,
                       user_id: str = Depends(current_user_id),
                       service: ConversationService = Depends(get_conversation_service)):
    return await service.update_conversation_title(user_id, str(conversation_id), title.title)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: UUID, user_id: str = Depends(current_user_id),
                              service: ConversationService = Depends(get_conversation_service)):
    await service.delete_conversation(user_id, str(conversation_id))
    return {"status": "deleted", "id": str(conversation_id)}


@router.get("/conversations/{conversation_id}/full", response_model=ConversationFull)
async def get_full(conversation_id: UUID, user_id: str = Depends(current_user_id),
                   service: ConversationService = Depends(get_conversation_service)):
    return await service.get_conversation_full(user_id, str(conversation_id))


@router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessage])
async def get_messages(conversation_id: UUID, user_id: str = Depends(current_user_id),
                       limit: int | None = Query(None, ge=1, le=500),
                       service: ConversationService = Depends(get_conversation_service)):
    return await service.get_conversation_messages(user_id, str(conversation_id), limit)


@router.post("/conversations/{conversation_id}/messages", response_model=ConversationMessage)
async def add_message(conversation_id: UUID, message: ConversationMessageCreate,
                      user_id: str = Depends(current_user_id),
                      service: ConversationService = Depends(get_conversation_service)):
    return await service.add_message(user_id, str(conversation_id), message)
