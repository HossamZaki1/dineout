import asyncio
import os
import threading
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
from google.auth.exceptions import DefaultCredentialsError

from app.main import create_app
from app.auth import current_user_id
from app.conversations.models import ConversationRequest
from app.conversations.service import ConversationService, StorageUnavailableError
from app.storage.factory import create_store
from app.storage.mock_conversation_store import MockConversationStore


class FakeAgents:
    async def initialize(self):
        pass

    def get_agent_status(self):
        return {"chat": "initialized"}

    async def handle_conversation(self, user_input, session_id, history):
        return {"session_id": session_id, "intent": "search_restaurants",
                "response": "Found a restaurant", "suggestions": [],
                "processing_time_seconds": 0.01, "search_performed": True}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"FIREBASE_PROJECT_ID": "demo-dineout-review",
                                                  "GOOGLE_MAPS_API_KEY": "test"})
        self.environment.start()
        self.store = MockConversationStore()
        self.app = create_app(self.store, FakeAgents())
        self.app.dependency_overrides[current_user_id] = lambda: "test-user"
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.sid = str(uuid4())

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()

    def chat(self):
        return self.client.post("/chat", json={"user_input": "pizza", "session_id": self.sid})

    def test_success_means_both_messages_are_saved(self):
        response = self.chat()
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json()["search_performed"])
        messages = self.client.get(f"/conversations/{self.sid}/messages")
        self.assertEqual(["user", "assistant"], [m["role"] for m in messages.json()])

    def test_whitespace_rejected_before_storage(self):
        self.chat()
        response = self.client.post(f"/conversations/{self.sid}/messages",
                                    json={"role": "user", "content": "   "})
        self.assertEqual(422, response.status_code)
        response = self.client.get(f"/conversations/{self.sid}/messages")
        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(response.json()))

    def test_full_history_preserves_metadata_for_local_cache(self):
        self.chat()
        page = self.client.get("/conversations").json()["items"][0]
        full = self.client.get(f"/conversations/{self.sid}/full").json()
        self.assertEqual(page["last_message_preview"], full["last_message_preview"])
        self.assertEqual(page["restaurant_suggestion_names"], full["restaurant_suggestion_names"])
        self.assertEqual(2, full["message_count"])

    def test_delete_and_rename_missing_conversation(self):
        self.chat()
        self.assertEqual(200, self.client.delete(f"/conversations/{self.sid}").status_code)
        self.assertEqual(404, self.client.get(f"/conversations/{self.sid}/messages").status_code)
        self.assertEqual(404, self.client.patch(f"/conversations/{self.sid}/title",
                         json={"title": "Resurrect"}).status_code)

    def test_pagination_and_invalid_limits(self):
        self.chat()
        page = self.client.get("/conversations?limit=1").json()
        self.assertEqual(self.sid, page["items"][0]["id"])
        self.assertIsNone(page["next_cursor"])
        self.assertEqual(422, self.client.get("/conversations?limit=0").status_code)
        self.assertEqual(400, self.client.get("/conversations?cursor=broken").status_code)
        self.assertEqual(422, self.client.get(f"/conversations/{self.sid}/messages?limit=-1").status_code)

    def test_photo_requests_require_auth_before_upstream(self):
        self.app.dependency_overrides.clear()
        self.assertEqual(401, self.client.get("/photos/a/b").status_code)
        self.assertEqual(401, self.chat().status_code)

    def test_photo_resolution_cached_and_available_as_json(self):
        class PhotoClient:
            calls = 0
            async def get(inner, url, **kwargs):
                inner.calls += 1
                return httpx.Response(200, json={"photoUri": "https://example.com/photo.jpg"},
                                      request=httpx.Request("GET", url))
        upstream = PhotoClient()
        self.app.state.photo_resolver.client = upstream
        for _ in range(2):
            response = self.client.get("/photos/a/b?redirect=false")
            self.assertEqual(200, response.status_code)
            self.assertEqual("https://example.com/photo.jpg", response.json()["url"])
        self.assertEqual(1, upstream.calls)

    def test_photo_quota_enforced_before_upstream(self):
        import time
        for _ in range(120):
            self.store.consume_quota("photos:user:test-user", 120, int(time.time() // 60))
        response = self.client.get("/photos/a/b?redirect=false")
        self.assertEqual(429, response.status_code)
        self.assertEqual("60", response.headers["retry-after"])

    def test_invalid_photo_path_rejected(self):
        self.assertEqual(422, self.client.get("/photos/a/b.bad?redirect=false").status_code)

    def test_storage_failure_is_not_a_success(self):
        with patch.object(self.store, "append_messages", side_effect=RuntimeError("offline")):
            response = self.chat()
        self.assertEqual(503, response.status_code)
        self.assertEqual([], self.store.list_page("test-user")["items"])

    def test_search_failure_returns_upstream_error(self):
        with patch.object(FakeAgents, "handle_conversation", side_effect=RuntimeError("upstream")):
            self.assertEqual(502, self.chat().status_code)

    def test_exhausted_transaction_retries_are_storage_unavailability(self):
        with patch.object(self.store, "append_messages",
                          side_effect=ValueError("Failed to commit transaction in 10 attempts")):
            self.assertEqual(503, self.chat().status_code)

    def test_provider_errors_do_not_log_secret_urls(self):
        with self.assertLogs("app.conversations.service", level="ERROR") as logs:
            with patch.object(FakeAgents, "handle_conversation",
                              side_effect=RuntimeError("https://provider.test/?key=private-key")):
                self.assertEqual(502, self.chat().status_code)
        self.assertNotIn("private-key", " ".join(logs.output))

    def test_invalid_history_content_is_rejected(self):
        response = self.client.post("/chat", json={
            "user_input": "pizza", "history": [{"role": "user", "content": {"bad": "type"}}]})
        self.assertEqual(422, response.status_code)


class StorageSelectionTests(unittest.TestCase):
    def test_missing_credentials_explain_local_setup_without_fallback(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "firestore", "K_SERVICE": ""}):
            with patch("app.storage.factory.FirestoreConversationStore",
                       side_effect=DefaultCredentialsError("missing")):
                with self.assertRaisesRegex(RuntimeError, "gcloud auth application-default login"):
                    create_store()

    def test_cloud_credentials_error_does_not_recommend_memory(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "firestore", "K_SERVICE": "service"}):
            with patch("app.storage.factory.FirestoreConversationStore",
                       side_effect=DefaultCredentialsError("missing")):
                with self.assertRaisesRegex(RuntimeError, "runtime service account") as error:
                    create_store()
                self.assertNotIn("STORAGE_BACKEND=memory", str(error.exception))

    def test_firestore_failure_does_not_fallback(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "firestore"}):
            with patch("app.storage.factory.FirestoreConversationStore", side_effect=RuntimeError("offline")):
                with self.assertRaises(RuntimeError):
                    create_store()

    def test_memory_forbidden_on_cloud_run(self):
        with patch.dict(os.environ, {"STORAGE_BACKEND": "memory", "K_SERVICE": "service"}):
            with self.assertRaises(RuntimeError):
                create_store()


class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_persistence_is_awaited_without_blocking_event_loop(self):
        started, release = threading.Event(), threading.Event()
        class SlowStore(MockConversationStore):
            def append_messages(self, *args):
                started.set()
                release.wait(2)
                return super().append_messages(*args)
        service = ConversationService(SlowStore(), FakeAgents())
        task = asyncio.create_task(service.process_chat_request(
            ConversationRequest(user_input="pizza"), "user"))
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            await asyncio.sleep(0.01)
            self.assertFalse(task.done(), "Response returned before storage completed")
        finally:
            release.set()
            await task
