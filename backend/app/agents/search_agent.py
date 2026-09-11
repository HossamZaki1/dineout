"""Google Places HTTP adapter; no language model is needed for API requests."""
import logging
import os
import httpx
from .opening_hours import next_opening

logger = logging.getLogger(__name__)


class SearchUnavailableError(Exception):
    pass


class SearchAgent:
    def __init__(self, client=None):
        self.client = client
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.is_initialized = False
        self.places_api_url = "https://places.googleapis.com/v1/places:searchText"

    async def initialize(self):
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY must be configured")
        if self.client is None:
            raise ValueError("SearchAgent requires an application-scoped HTTP client")
        self.is_initialized = True

    async def _geocode_location(self, location):
        try:
            response = await self.client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": location, "key": self.api_key})
            response.raise_for_status()
            result = response.json()
            if result.get("status") == "ZERO_RESULTS":
                return None
            if result.get("status") != "OK":
                raise SearchUnavailableError("Geocoding service rejected the request")
            return result["results"][0]["geometry"]["location"]
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            # Do not log the exception URL: geocoding sends its key in the URL.
            raise SearchUnavailableError("Geocoding service is unavailable") from exc

    async def find_all_restaurants(self, location, cuisine, radius=5000.0, *, coordinates=None):
        coordinates = coordinates or await self._geocode_location(location)
        if coordinates is None:
            return []
        fields = (
            "id,displayName,formattedAddress,rating,photos,regularOpeningHours,"
            "currentOpeningHours,googleMapsUri,reviews,timeZone,utcOffsetMinutes"
        )
        query = f"{cuisine} restaurants" if cuisine and cuisine.lower() != "any" else "restaurants"
        try:
            response = await self.client.post(
                self.places_api_url,
                headers={"X-Goog-Api-Key": self.api_key,
                         "X-Goog-FieldMask": ",".join(f"places.{f}" for f in fields.split(","))},
                json={
                    # An explicit location in textQuery can override locationBias.
                    "textQuery": query, "pageSize": 10,
                    "locationBias": {"circle": {
                        "center": {"latitude": coordinates["lat"], "longitude": coordinates["lng"]},
                        "radius": radius,
                    }},
                },
            )
            response.raise_for_status()
            places = response.json().get("places", [])
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise SearchUnavailableError("Restaurant search is unavailable") from exc
        restaurants = []
        for place in places:
            current = place.get("currentOpeningHours") or {}
            regular = place.get("regularOpeningHours") or {}
            is_open = current.get("openNow")
            periods = current.get("periods", regular.get("periods", []))
            wait, display = None, None
            if is_open is False:
                wait, display = next_opening(
                    periods, timezone_id=(place.get("timeZone") or {}).get("id"),
                    utc_offset_minutes=place.get("utcOffsetMinutes"),
                    next_open_time=current.get("nextOpenTime"),
                )
            restaurants.append({
                "name": (place.get("displayName") or {}).get("text"),
                "address": place.get("formattedAddress"),
                "rating": place.get("rating"), "is_open_now": is_open,
                "photos": place.get("photos", []), "place_id": place.get("id"),
                "google_maps_uri": place.get("googleMapsUri"),
                "opening_hours_periods": periods,
                "current_opening_hours": current, "regular_opening_hours": regular,
                "next_opening_time": wait, "next_opening_display": display,
                "reviews": place.get("reviews", []),
            })
        return self._sort_restaurants_by_status_and_opening_time(restaurants)

    def _sort_restaurants_by_status_and_opening_time(self, restaurants):
        return sorted(restaurants, key=lambda r: (
            0 if r.get("is_open_now") is True else 1,
            r["next_opening_time"] if r.get("next_opening_time") is not None else float("inf"),
        ))

    async def find_all_restaurants_with_radius_extension(self, location, cuisine, min_results=2):
        coordinates = await self._geocode_location(location)
        if coordinates is None:
            return []
        # Widen the geographic bias; Places may still return results outside it.
        # Keep earlier results when a later, wider query returns fewer.
        found = {}
        for radius in (5000.0, 20000.0, 50000.0):
            restaurants = await self.find_all_restaurants(
                location, cuisine, radius, coordinates=coordinates)
            for restaurant in restaurants:
                key = restaurant.get("place_id") or (restaurant["name"], restaurant["address"])
                found[key] = restaurant
            if len(found) >= min_results:
                break
        return self._sort_restaurants_by_status_and_opening_time(list(found.values()))[:10]
