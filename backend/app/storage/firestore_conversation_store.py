"""Transactional Firestore storage. Call through the service's worker threads."""
import hashlib
import os
from datetime import datetime, timezone
from google.cloud import firestore

from .base import (ConversationNotFoundError, RateLimitError, api_dict,
                   decode_cursor, encode_cursor, normalize_messages, updated_metadata)


class FirestoreConversationStore:
    kind = "firestore"

    def __init__(self, client=None):
        self.client = client or firestore.Client(
            project=os.getenv("FIRESTORE_PROJECT_ID") or os.getenv("FIREBASE_PROJECT_ID"))

    def check_health(self):
        self.client.collection("_health").document("ready").get(timeout=5, retry=None)

    def close(self):
        self.client.close()

    def _convs_col(self, user_id):
        return self.client.collection("users").document(user_id).collection("conversations")

    def _conv_ref(self, user_id, conversation_id):
        return self._convs_col(user_id).document(conversation_id)

    def _msgs_col(self, user_id, conversation_id):
        return self._conv_ref(user_id, conversation_id).collection("messages")

    def get_meta(self, user_id, conversation_id):
        snapshot = self._conv_ref(user_id, conversation_id).get(timeout=10)
        data = snapshot.to_dict() or {}
        return api_dict({**data, "id": snapshot.id}) if snapshot.exists and not data.get("deleted") else None

    def list_page(self, user_id, limit=50, cursor=None):
        # Document ID disambiguates equal timestamps without offset scans.
        query = self._convs_col(user_id).order_by(
            "updated_at", direction=firestore.Query.DESCENDING
        ).order_by("__name__", direction=firestore.Query.DESCENDING)
        if cursor:
            timestamp, identifier = decode_cursor(cursor)
            query = query.start_after({
                "updated_at": timestamp,
                "__name__": self._conv_ref(user_id, identifier),
            })
        snapshots = list(query.limit(limit + 1).stream(timeout=10))
        raw_page = [{**s.to_dict(), "id": s.id} for s in snapshots[:limit]]
        return {
            "items": [api_dict(m) for m in raw_page if not m.get("deleted")],
            "next_cursor": encode_cursor(raw_page[-1]) if len(snapshots) > limit else None,
        }

    def append_messages(self, user_id, conversation_id, messages, title=None):
        messages = normalize_messages(messages)
        ref = self._conv_ref(user_id, conversation_id)
        message_refs = [ref.collection("messages").document() for _ in messages]

        @firestore.transactional
        def commit(transaction):
            snapshot = ref.get(transaction=transaction, timeout=10)
            existing = snapshot.to_dict() or {}
            if existing.get("deleted") or (not snapshot.exists and title is None):
                raise ConversationNotFoundError()
            metadata = updated_metadata(existing, conversation_id, title, messages)
            # The complete turn, count and preview commit together.
            transaction.set(ref, metadata, merge=True)
            for message_ref, message in zip(message_refs, messages):
                transaction.set(message_ref, message)

        commit(self.client.transaction(max_attempts=10))
        return [api_dict({**message, "id": ref.id})
                for message, ref in zip(messages, message_refs)]

    def get_messages(self, user_id, conversation_id, limit=None):
        if self.get_meta(user_id, conversation_id) is None:
            raise ConversationNotFoundError()
        query = self._msgs_col(user_id, conversation_id).order_by(
            "timestamp", direction=firestore.Query.DESCENDING
        ).order_by("__name__", direction=firestore.Query.DESCENDING)
        if limit is not None:
            query = query.limit(limit)
        messages = [api_dict({**s.to_dict(), "id": s.id}) for s in query.stream(timeout=10)]
        if self.get_meta(user_id, conversation_id) is None:
            raise ConversationNotFoundError()
        return list(reversed(messages))

    def update_title(self, user_id, conversation_id, title):
        ref = self._conv_ref(user_id, conversation_id)

        @firestore.transactional
        def update(transaction):
            snapshot = ref.get(transaction=transaction, timeout=10)
            data = snapshot.to_dict() or {}
            if not snapshot.exists or data.get("deleted"):
                raise ConversationNotFoundError()
            data.update(id=conversation_id, title=title, updated_at=datetime.now(timezone.utc))
            transaction.update(ref, {"title": title, "updated_at": data["updated_at"]})
            return api_dict(data)

        return update(self.client.transaction())

    def delete(self, user_id, conversation_id):
        ref = self._conv_ref(user_id, conversation_id)

        @firestore.transactional
        def hide(transaction):
            snapshot = ref.get(transaction=transaction, timeout=10)
            if not snapshot.exists:
                return False
            # Append transactions read this document and conflict with deletion.
            # Only a content-free tombstone remains after cleanup.
            transaction.set(ref, {"id": conversation_id, "deleted": True,
                                  "updated_at": datetime.now(timezone.utc)})
            return True

        existed = hide(self.client.transaction())
        # Also clean orphaned messages from conversations deleted by old builds.
        # Retrying deletion resumes cleanup if a batch failed previously.
        while True:
            messages = list(ref.collection("messages").limit(400).stream(timeout=10))
            if not messages:
                break
            batch = self.client.batch()
            for message in messages:
                batch.delete(message.reference)
            batch.commit(timeout=10)
        return existed

    def consume_quota(self, bucket, limit, window):
        # Fixed-window counter shared by all Cloud Run instances.
        identifier = hashlib.sha256(bucket.encode()).hexdigest()
        ref = self.client.collection("request_quotas").document(identifier)

        @firestore.transactional
        def consume(transaction):
            data = ref.get(transaction=transaction, timeout=10).to_dict() or {}
            count = data.get("count", 0) if data.get("window") == window else 0
            if count >= limit:
                raise RateLimitError()
            transaction.set(ref, {"window": window, "count": count + 1})

        consume(self.client.transaction())
