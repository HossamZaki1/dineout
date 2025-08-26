from typing import Dict, List, Any
from .base_agent import BaseAgent
import httpx
import os

class SearchAgent(BaseAgent):
    """
    Agent responsible for searching for restaurants using the Google Places API.
    """
    
    def __init__(self):
        super().__init__("Search", temperature=0.3)
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.places_api_url = "https://places.googleapis.com/v1/places:searchText"

    async def _custom_initialize(self):
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")

    async def _geocode_location(self, location: str) -> Dict[str, float]:
        """
        Converts a location string to latitude and longitude using Google Geocoding API.
        """
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": location,
            "key": self.api_key
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(geocode_url, params=params)
                response.raise_for_status()
                results = response.json()
                if results['status'] == 'OK':
                    return results['results'][0]['geometry']['location']
                else:
                    print(f"Geocoding failed: {results.get('status')}")
                    return None
            except httpx.HTTPStatusError as e:
                print(f"Error geocoding location: {e.response.text}")
                return None
            except Exception as e:
                print(f"An unexpected error occurred during geocoding: {e}")
                return None

    async def find_open_restaurants(self, location: str, cuisine: str) -> List[Dict[str, Any]]:
        """
        Searches for restaurants that are currently open using the Google Places API.
        """
        # Geocode the location string to get coordinates
        coordinates = await self._geocode_location(location)
        if not coordinates:
            print("Could not geocode location, aborting search.")
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.photos,places.regularOpeningHours"
        }
        
        data = {
            "textQuery": f"{cuisine} restaurants near {location}",
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": coordinates['lat'],
                        "longitude": coordinates['lng']
                    },
                    "radius": 5000.0
                }
            },
            "openNow": True,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.places_api_url, json=data, headers=headers)
                response.raise_for_status()
                results = response.json()
                
                # Filter for open restaurants and format the output
                open_restaurants = []
                for place in results.get('places', []):
                    open_restaurants.append({
                        "name": place.get('displayName', {}).get('text'),
                        "address": place.get('formattedAddress'),
                        "rating": place.get('rating'),
                        "is_open_now": True,
                        "photos": place.get('photos', []) 
                    })
                return open_restaurants

            except httpx.HTTPStatusError as e:
                print(f"Error searching for restaurants: {e.response.text}")
                return []
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return []

