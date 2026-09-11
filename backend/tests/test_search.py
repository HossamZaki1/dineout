import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import httpx

from app.agents.opening_hours import next_opening
from app.agents.search_agent import SearchAgent, SearchUnavailableError
from app.agents.presentation_agent import PresentationAgent
from app.agents.photo_agent import PhotoAgent


class OpeningHoursTests(unittest.TestCase):
    def test_monday_opening_is_in_one_hour(self):
        wait, label = next_opening([{"open": {"day": 1, "hour": 11}}],
            now=datetime(2026, 9, 7, 10, tzinfo=timezone.utc), timezone_id="UTC")
        self.assertEqual(60, wait)
        self.assertIn("today", label)

    def test_restaurant_timezone_changes_day(self):
        wait, _ = next_opening([{"open": {"day": 0, "hour": 18}}],
            now=datetime(2026, 9, 7, 0, tzinfo=timezone.utc), timezone_id="America/Los_Angeles")
        self.assertEqual(60, wait)

    def test_passed_opening_wraps_to_next_week(self):
        wait, _ = next_opening([{"open": {"day": 1, "hour": 9}}],
            now=datetime(2026, 9, 7, 10, tzinfo=timezone.utc), timezone_id="UTC")
        self.assertEqual(7 * 24 * 60 - 60, wait)

    def test_dst_uses_elapsed_time(self):
        wait, _ = next_opening([{"open": {"day": 0, "hour": 9}}],
            now=datetime(2026, 3, 28, 9, tzinfo=timezone.utc), timezone_id="Europe/Berlin")
        self.assertEqual(22 * 60, wait)

    def test_provider_exceptional_hours_override_regular_hours(self):
        wait, _ = next_opening([{"open": {"day": 1, "hour": 11}}],
            now=datetime(2026, 9, 7, 10, tzinfo=timezone.utc), timezone_id="UTC",
            next_open_time="2026-09-08T12:00:00Z")
        self.assertEqual(26 * 60, wait)

    def test_dated_period_is_not_repeated_next_week(self):
        wait, _ = next_opening([{"open": {"date": {"year": 2026, "month": 9, "day": 6}, "hour": 11}}],
            now=datetime(2026, 9, 7, 10, tzinfo=timezone.utc), timezone_id="UTC")
        self.assertIsNone(wait)

    def test_missing_timezone_does_not_guess_server_timezone(self):
        wait, label = next_opening([{"open": {"day": 1, "hour": 11}}])
        self.assertIsNone(wait)
        self.assertEqual("Hours not available", label)


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_non_llm_components_initialize_without_gemini(self):
        with patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "test"}, clear=True):
            async with httpx.AsyncClient() as client:
                for stage in (SearchAgent(client), PhotoAgent(), PresentationAgent()):
                    await stage.initialize()
                    self.assertTrue(stage.is_initialized)
                    self.assertFalse(hasattr(stage, "llm"))

    async def test_provider_outage_is_not_an_empty_result(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(503))) as client:
            search = SearchAgent(client)
            search.api_key = "test"
            with self.assertRaises(SearchUnavailableError):
                await search.find_all_restaurants("Berlin", "pizza", coordinates={"lat": 52, "lng": 13})

    async def test_geocoding_denied_is_not_zero_results(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"status": "REQUEST_DENIED"}))) as client:
            with self.assertRaises(SearchUnavailableError):
                await SearchAgent(client)._geocode_location("Berlin")

    async def test_no_reviews_does_not_invent_menu_even_without_cuisine(self):
        summary = await PresentationAgent().summarize_restaurant({"reviews": [], "cuisine": None})
        self.assertIn("not available", summary)
        self.assertNotIn("pizza", summary)

    async def test_mentions_are_attributed_and_not_claimed_available(self):
        summary = await PresentationAgent().summarize_restaurant(
            {"reviews": [{"text": {"text": "We tried the pizza."}}], "cuisine": "italian"})
        self.assertIn("pizza", summary)
        self.assertIn("Mentioned in reviews", summary)
        self.assertNotIn("tiramisu", summary)
