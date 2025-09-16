import os
import logging
from typing import List
import googlemaps
from ..models.restaurant_models import RestaurantInfo, LocationRequest, DishInfo

logger = logging.getLogger(__name__)

class PlacesService:
    """Google Places service with real API integration"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")    
    async def find_restaurants(self, location: LocationRequest, limit: int = 10) -> List[RestaurantInfo]:
        """Find restaurants near location"""
        if not self.api_key:
            print("Google Places API key not configured")
            return []
        
        try:
            # TODO: Implement real Google Places API integration
            # For now, return empty list until API is properly configured
            return []
        except Exception as e:
            print(f"Error finding restaurants: {e}")
            return []
    
    async def close(self):
        """Cleanup resources"""
        pass
