"""The same behavioral contract runs against memory and the Firestore emulator."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.storage.base import ConversationNotFoundError, RateLimitError
from app.storage.mock_conversation_store import MockConversationStore


class StorageContract:
    def setUp(self):
        self.store = self.make_store()
        self.user = "test-" + str(uuid4())
        self.conversation = str(uuid4())
        self.now = datetime.now(timezone.utc)
        self.seed()

    def tearDown(self):
        self.store.close()

    def seed(self, conversation=None, title="Original"):
        return self.store.append_messages(self.user, conversation or self.conversation, [
            {"role": "user", "content": "pizza", "timestamp": self.now},
            {"role": "assistant", "content": "Review mentions", "timestamp": self.now + timedelta(seconds=1),
             "restaurant_suggestions": [{"name": "Test restaurant", "photo_url": "/photos/a/b"}]},
        ], title)

    def test_delete_hides_and_removes_messages_and_prevents_resurrection(self):
        self.assertTrue(self.store.delete(self.user, self.conversation))
        self.assertIsNone(self.store.get_meta(self.user, self.conversation))
        with self.assertRaises(ConversationNotFoundError):
            self.store.get_messages(self.user, self.conversation)
        with self.assertRaises(ConversationNotFoundError):
            self.seed()
        self.assertEqual([], self.store.list_page(self.user)["items"])
        self.assertTrue(self.store.delete(self.user, self.conversation))  # retryable

    def test_title_survives_next_turn(self):
        self.store.update_title(self.user, self.conversation, "My dinner plans")
        self.seed(title="Automatically derived")
        self.assertEqual("My dinner plans", self.store.get_meta(self.user, self.conversation)["title"])

    def test_invalid_turn_is_not_partially_saved(self):
        before = self.store.get_messages(self.user, self.conversation)
        with self.assertRaises(ValueError):
            self.store.append_messages(self.user, self.conversation, [
                {"role": "user", "content": "valid"}, {"role": "assistant", "content": "  "},
            ])
        self.assertEqual(before, self.store.get_messages(self.user, self.conversation))
        self.assertEqual(2, self.store.get_meta(self.user, self.conversation)["message_count"])

    def test_ownership_and_missing_conversation(self):
        self.assertIsNone(self.store.get_meta("other-user", self.conversation))
        with self.assertRaises(ConversationNotFoundError):
            self.store.get_messages("other-user", self.conversation)
        with self.assertRaises(ConversationNotFoundError):
            self.store.append_messages(self.user, str(uuid4()), [{"role": "user", "content": "orphan"}])
        with self.assertRaises(ConversationNotFoundError):
            self.store.update_title(self.user, str(uuid4()), "Missing")

    def test_message_limit_returns_latest_in_chronological_order(self):
        messages = self.store.get_messages(self.user, self.conversation, limit=1)
        self.assertEqual(["assistant"], [m["role"] for m in messages])

    def test_metadata_contains_counts_and_preview(self):
        meta = self.store.list_page(self.user)["items"][0]
        self.assertEqual(2, meta["message_count"])
        self.assertEqual(["Test restaurant"], meta["restaurant_suggestion_names"])
        self.assertEqual(["/photos/a/b"], meta["restaurant_photo_urls"])
        self.assertEqual(1, meta["total_restaurant_suggestions"])
        self.assertIn("pizza", meta["last_message_preview"])

    def test_pagination_visits_each_conversation_once(self):
        for _ in range(5):
            self.seed(str(uuid4()))
        cursor, found = None, []
        while True:
            page = self.store.list_page(self.user, limit=2, cursor=cursor)
            found.extend(item["id"] for item in page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        self.assertEqual(6, len(set(found)))
        self.assertEqual(6, len(found))

    def test_invalid_cursor_rejected(self):
        with self.assertRaises(ValueError):
            self.store.list_page(self.user, cursor="not-a-cursor")

    def test_concurrent_appends_preserve_counts(self):
        def append(index):
            self.store.append_messages(self.user, self.conversation,
                                       [{"role": "user", "content": f"turn {index}"}])
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(append, range(6)))
        self.assertEqual(8, len(self.store.get_messages(self.user, self.conversation)))
        self.assertEqual(8, self.store.get_meta(self.user, self.conversation)["message_count"])

    def test_quota_enforced_and_resets_next_window(self):
        bucket = self.user + ":photos"
        self.store.consume_quota(bucket, 2, 10)
        self.store.consume_quota(bucket, 2, 10)
        with self.assertRaises(RateLimitError):
            self.store.consume_quota(bucket, 2, 10)
        self.store.consume_quota(bucket, 2, 11)


class MemoryStorageTests(StorageContract, unittest.TestCase):
    def make_store(self):
        return MockConversationStore()

    def test_deleted_messages_physically_removed(self):
        self.store.delete(self.user, self.conversation)
        self.assertNotIn((self.user, self.conversation), self.store._messages)


@unittest.skipUnless(os.getenv("FIRESTORE_EMULATOR_HOST"), "Firestore emulator is not running")
class FirestoreStorageTests(StorageContract, unittest.TestCase):
    def make_store(self):
        from google.cloud import firestore
        from app.storage.firestore_conversation_store import FirestoreConversationStore
        host = os.environ["FIRESTORE_EMULATOR_HOST"]
        if not host.startswith(("localhost:", "127.0.0.1:")):
            raise RuntimeError("Storage tests require a local emulator")
        return FirestoreConversationStore(firestore.Client(project="demo-dineout-review"))

    def tearDown(self):
        # Test-only fixture cleanup, always on the explicitly configured emulator.
        self.store.client.recursive_delete(self.store.client.collection("users").document(self.user))
        super().tearDown()

    def test_delete_spans_multiple_batches(self):
        self.store.append_messages(self.user, self.conversation,
                                   [{"role": "user", "content": f"message {i}"} for i in range(405)])
        self.store.delete(self.user, self.conversation)
        remaining = list(self.store._msgs_col(self.user, self.conversation).stream())
        self.assertEqual([], remaining)

    def test_quota_shared_across_clients(self):
        second = self.make_store()
        try:
            self.store.consume_quota(self.user + ":shared", 1, 10)
            with self.assertRaises(RateLimitError):
                second.consume_quota(self.user + ":shared", 1, 10)
        finally:
            second.close()
