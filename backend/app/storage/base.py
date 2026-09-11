"""Shared storage contract and serialization."""
import base64
import json
from datetime import datetime, timezone
from typing import Protocol


class ConversationNotFoundError(Exception):
    pass


class RateLimitError(Exception):
    pass


class StorageValidationError(ValueError):
    """Caller input is invalid, distinct from a provider's ValueError."""


class ConversationStore(Protocol):
    kind: str
    def check_health(self) -> None: ...
    def close(self) -> None: ...
    def list_page(self, user_id: str, limit: int, cursor: str | None) -> dict: ...
    def get_meta(self, user_id: str, conversation_id: str) -> dict | None: ...
    def get_messages(self, user_id: str, conversation_id: str, limit: int | None = None) -> list[dict]: ...
    def append_messages(self, user_id: str, conversation_id: str, messages: list[dict], title: str | None = None) -> list[dict]: ...
    def update_title(self, user_id: str, conversation_id: str, title: str) -> dict: ...
    def delete(self, user_id: str, conversation_id: str) -> bool: ...
    def consume_quota(self, bucket: str, limit: int, window: int) -> None: ...


def as_datetime(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def api_dict(data: dict) -> dict:
    return {key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in data.items()}


def encode_cursor(data: dict) -> str:
    raw = json.dumps([as_datetime(data["updated_at"]).isoformat(), data["id"]])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        if len(cursor) > 1024:
            raise ValueError()
        timestamp, identifier = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if not isinstance(timestamp, str) or not isinstance(identifier, str) or not identifier or "/" in identifier:
            raise ValueError()
        return as_datetime(timestamp), identifier
    except (ValueError, TypeError, KeyError) as exc:
        raise StorageValidationError("Invalid pagination cursor") from exc


def normalize_messages(messages: list[dict]) -> list[dict]:
    normalized = []
    for message in messages:
        content = message.get("content", "").strip()
        if not content or len(content) > 10000:
            raise StorageValidationError("Message content must contain 1 to 10000 characters")
        if message.get("role") not in ("user", "assistant"):
            raise StorageValidationError("Invalid message role")
        normalized.append({
            **message, "content": content,
            "timestamp": as_datetime(message.get("timestamp")),
            "restaurant_suggestions": message.get("restaurant_suggestions") or [],
        })
    return normalized


def updated_metadata(existing: dict, conversation_id: str, title: str | None, messages: list[dict]) -> dict:
    """Maintain bounded list previews in the transaction that saves messages."""
    now = datetime.now(timezone.utc)
    suggestions = [r for m in messages for r in m["restaurant_suggestions"]]
    names = list(dict.fromkeys(existing.get("restaurant_suggestion_names", []) +
                              [r["name"] for r in suggestions if r.get("name")]))[:20]
    photos = list(dict.fromkeys(existing.get("restaurant_photo_urls", []) +
                               [r["photo_url"] for r in suggestions if r.get("photo_url")]))[:12]
    preview = "\n".join(f"{'You' if m['role'] == 'user' else 'AI'}: {m['content'][:100]}"
                        for m in messages[-2:])
    return {
        "id": conversation_id,
        "title": existing.get("title") or title or "New Search",
        "created_at": as_datetime(existing.get("created_at", now)),
        "updated_at": now,
        "message_count": existing.get("message_count", 0) + len(messages),
        "last_message_preview": preview,
        "restaurant_suggestion_names": names,
        "restaurant_photo_urls": photos,
        "total_restaurant_suggestions": existing.get("total_restaurant_suggestions", 0) + len(suggestions),
    }
