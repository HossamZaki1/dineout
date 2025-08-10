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
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.places_api_url = "https://places.googleapis.com/v1/places:searchNearby"

    async def _custom_initialize(self):
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

    async def find_open_restaurants(self, location: str, cuisine: str) -> List[Dict[str, Any]]:
        """
        Searches for restaurants that are currently open using the Google Places API.
        """
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.photos,places.openingState"
        }
        
        # Note: The new Places API requires location as latitude/longitude.
        # The LocationAgent should be updated to provide this.
        # For now, we'll use a simplified text query.
        
        data = {
            "includedTypes": ["restaurant"],
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": 37.7749, # Placeholder lat
                        "longitude": -122.4194 # Placeholder lon
                    },
                    "radius": 5000.0
                }
            },
            "textQuery": f"{cuisine} restaurants in {location}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.places_api_url, json=data, headers=headers)
                response.raise_for_status()
                results = response.json()
                
                # Filter for open restaurants and format the output
                open_restaurants = []
                for place in results.get('places', []):
                    if place.get('openingState') == 'OPEN':
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

