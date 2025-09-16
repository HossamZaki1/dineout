import logging
from typing import List
from .google_places_service import GooglePlacesService
from ..models.restaurant_models import LocationRequest, RestaurantInfo, DiscoveryResponse

logger = logging.getLogger(__name__)

class DiscoveryService:
    """Restaurant discovery service"""
    
    def __init__(self):
        self.places_service = GooglePlacesService()
    
    async def discover_restaurants(self, location: LocationRequest, limit: int = 10) -> DiscoveryResponse:
        """Find restaurants with dishes near user location"""
        try:
            logger.info(f"Finding restaurants near {location.latitude}, {location.longitude}")
            
            # Get restaurants
            restaurants = await self.places_service.find_nearby_restaurants(location, limit)
            
            # Convert dict dishes to DishInfo objects
            for restaurant in restaurants:
                if restaurant.top_dishes and isinstance(restaurant.top_dishes[0], dict):
                    from ..models.restaurant_models import DishInfo
                    restaurant.top_dishes = [
                        DishInfo(**dish) for dish in restaurant.top_dishes
                    ]
            
            return DiscoveryResponse(
                restaurants=restaurants,
                total_found=len(restaurants),
                search_location={"lat": location.latitude, "lng": location.longitude}
            )
            
        except Exception as e:
            logger.error(f"Error discovering restaurants: {e}")
            # Return empty response on error
            return DiscoveryResponse(
                restaurants=[],
                total_found=0,
                search_location={"lat": location.latitude, "lng": location.longitude}
            )
    
    async def get_restaurant(self, place_id: str) -> RestaurantInfo:
        """Get single restaurant by ID"""
        try:
            return await self.places_service.get_restaurant_details(place_id)
        except Exception as e:
            logger.error(f"Error getting restaurant {place_id}: {e}")
            return None
    
    async def close(self):
        """Cleanup"""
        await self.places_service.close()
