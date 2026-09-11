"""Conversation orchestration; synchronous storage runs on worker threads."""
import asyncio
import logging
import time
from datetime import datetime, timezone

from ..agents.multi_agent_system import MultiAgentSystem
from ..storage.base import (ConversationStore, ConversationNotFoundError, RateLimitError,
                            StorageValidationError)
from .models import (ConversationRequest, ConversationResponse, ConversationMeta,
                     ConversationMessage, ConversationFull, ConversationMessageCreate,
                     ConversationPage)
from .utils import derive_conversation_title, generate_session_id, format_chat_history_for_agents

logger = logging.getLogger(__name__)


class ConversationServiceError(Exception):
    pass


class StorageUnavailableError(ConversationServiceError):
    pass


class InvalidRequestError(ConversationServiceError):
    pass


class UpstreamUnavailableError(ConversationServiceError):
    pass


class ConversationService:
    def __init__(self, storage: ConversationStore, multi_agent_system: MultiAgentSystem,
                 max_concurrent_requests: int = 10):
        self.storage = storage
        self.multi_agent_system = multi_agent_system
        self.max_concurrent_requests = max_concurrent_requests
        self._request_semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _call(self, method, *args):
        try:
            return await asyncio.to_thread(method, *args)
        except (ConversationNotFoundError, RateLimitError):
            raise
        except StorageValidationError as exc:
            raise InvalidRequestError(str(exc)) from exc
        except Exception as exc:
            logger.exception("Conversation storage operation failed")
            raise StorageUnavailableError("Conversation storage is temporarily unavailable") from exc

    async def consume_quota(self, bucket: str, limit: int):
        await self._call(self.storage.consume_quota, bucket, limit, int(time.time() // 60))

    async def process_chat_request(self, request: ConversationRequest, user_id: str) -> ConversationResponse:
        await self.consume_quota(f"chat:{user_id}", 10)
        session_id = request.session_id or generate_session_id()
        async with self._request_semaphore:
            try:
                result = await asyncio.wait_for(
                    self.multi_agent_system.handle_conversation(
                        user_input=request.user_input, session_id=session_id,
                        history=format_chat_history_for_agents(request.history or [])),
                    timeout=30,
                )
                # Validate before writing: malformed provider output must not
                # leave messages that cannot be read back through the API.
                response = ConversationResponse(**result)
            except asyncio.TimeoutError as exc:
                raise UpstreamUnavailableError("The search timed out. Please try again.") from exc
            except Exception as exc:
                # Provider exception chains can contain API keys in request URLs.
                logger.error("Restaurant search failed (%s)", type(exc).__name__)
                raise UpstreamUnavailableError("Restaurant search is temporarily unavailable. Please try again.") from exc

            now = datetime.now(timezone.utc)
            messages = [
                ConversationMessage(role="user", content=request.user_input, timestamp=now),
                ConversationMessage(role="assistant", content=response.response,
                                    timestamp=datetime.now(timezone.utc),
                                    restaurant_suggestions=response.suggestions),
            ]
            # A successful response means the complete exchange has committed.
            # Existing titles are preserved by both storage implementations.
            await self._call(
                self.storage.append_messages, user_id, session_id,
                [message.model_dump(mode="json", exclude={"id"}) for message in messages],
                derive_conversation_title(request.history or [], request.user_input),
            )
            return response

    async def list_conversations(self, user_id: str, limit=50, cursor=None) -> ConversationPage:
        page = await self._call(self.storage.list_page, user_id, limit, cursor)
        return ConversationPage(**page)

    async def get_conversation_full(self, user_id: str, conversation_id: str) -> ConversationFull:
        metadata = await self._call(self.storage.get_meta, user_id, conversation_id)
        if metadata is None:
            raise ConversationNotFoundError()
        messages = await self.get_conversation_messages(user_id, conversation_id)
        return ConversationFull(**{**metadata, "message_count": len(messages), "messages": messages})

    async def get_conversation_messages(self, user_id: str, conversation_id: str,
                                        limit: int | None = None) -> list[ConversationMessage]:
        messages = await self._call(self.storage.get_messages, user_id, conversation_id, limit)
        return [ConversationMessage(**message) for message in messages]

    async def add_message(self, user_id: str, conversation_id: str,
                          message: ConversationMessageCreate) -> ConversationMessage:
        # Use server timestamps for new writes; clients cannot reorder history.
        validated = ConversationMessage(
            role=message.role, content=message.content,
            timestamp=datetime.now(timezone.utc),
            restaurant_suggestions=message.restaurant_suggestions,
        )
        saved = await self._call(self.storage.append_messages, user_id, conversation_id,
                                 [validated.model_dump(mode="json", exclude={"id"})])
        return ConversationMessage(**saved[0])

    async def update_conversation_title(self, user_id: str, conversation_id: str,
                                         title: str) -> ConversationMeta:
        stored = await self._call(self.storage.update_title, user_id, conversation_id, title)
        return ConversationMeta(**stored)

    async def delete_conversation(self, user_id: str, conversation_id: str):
        removed = await self._call(self.storage.delete, user_id, conversation_id)
        if not removed:
            raise ConversationNotFoundError()
