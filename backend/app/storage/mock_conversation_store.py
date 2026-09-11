"""Explicit development storage, with the same thread-safe contract as Firestore."""
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from .base import (ConversationNotFoundError, RateLimitError, api_dict,
                   as_datetime, decode_cursor, encode_cursor, normalize_messages,
                   updated_metadata)


class MockConversationStore:
    kind = "memory"

    def __init__(self):
        self._conversations = {}
        self._messages = {}
        self._quotas = {}
        self._lock = RLock()

    def check_health(self):
        pass

    def close(self):
        pass

    def get_meta(self, user_id, conversation_id):
        with self._lock:
            meta = self._conversations.get((user_id, conversation_id))
            return api_dict(deepcopy(meta)) if meta and not meta.get("deleted") else None

    def list_page(self, user_id, limit=50, cursor=None):
        with self._lock:
            items = [m for (uid, _), m in self._conversations.items() if uid == user_id]
            items.sort(key=lambda m: (as_datetime(m["updated_at"]), m["id"]), reverse=True)
            if cursor:
                position = decode_cursor(cursor)
                items = [m for m in items if (as_datetime(m["updated_at"]), m["id"]) < position]
            page = items[:limit]
            return {
                "items": [api_dict(deepcopy(m)) for m in page if not m.get("deleted")],
                "next_cursor": encode_cursor(page[-1]) if len(items) > limit else None,
            }

    def append_messages(self, user_id, conversation_id, messages, title=None):
        messages = normalize_messages(messages)
        key = (user_id, conversation_id)
        with self._lock:
            existing = self._conversations.get(key, {})
            if existing.get("deleted") or (not existing and title is None):
                raise ConversationNotFoundError()
            saved = [{**m, "id": str(uuid4())} for m in messages]
            metadata = updated_metadata(existing, conversation_id, title, saved)
            self._messages.setdefault(key, []).extend(deepcopy(saved))
            self._conversations[key] = metadata
            return [api_dict(deepcopy(m)) for m in saved]

    def get_messages(self, user_id, conversation_id, limit=None):
        with self._lock:
            if self.get_meta(user_id, conversation_id) is None:
                raise ConversationNotFoundError()
            items = sorted(self._messages.get((user_id, conversation_id), []),
                           key=lambda m: (as_datetime(m["timestamp"]), m["id"]))
            if limit is not None:
                items = items[-limit:]
            return [api_dict(deepcopy(m)) for m in items]

    def update_title(self, user_id, conversation_id, title):
        with self._lock:
            if self.get_meta(user_id, conversation_id) is None:
                raise ConversationNotFoundError()
            self._conversations[(user_id, conversation_id)].update(
                title=title, updated_at=datetime.now(timezone.utc))
            return self.get_meta(user_id, conversation_id)

    def delete(self, user_id, conversation_id):
        key = (user_id, conversation_id)
        with self._lock:
            if key not in self._conversations:
                return False
            # Retain only a marker to prevent in-flight chats resurrecting data.
            self._conversations[key] = {
                "id": conversation_id, "deleted": True,
                "updated_at": datetime.now(timezone.utc),
            }
            self._messages.pop(key, None)
            return True

    def consume_quota(self, bucket, limit, window):
        with self._lock:
            previous_window, count = self._quotas.get(bucket, (window, 0))
            count = count if previous_window == window else 0
            if count >= limit:
                raise RateLimitError()
            self._quotas[bucket] = (window, count + 1)
