import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from ..models.restaurant_models import RestaurantInfo, RestaurantReview, LocationRequest

logger = logging.getLogger(__name__)

class GooglePlacesService:
    """Service to interact with Google Places API and Google Maps reviews"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            logger.warning("Google Places API key not found. Using mock data.")
        
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def find_nearby_restaurants(self, location: LocationRequest, limit: int = 10) -> List[RestaurantInfo]:
        """Find top-rated restaurants near the given location"""
        try:
            # Use Google Places Nearby Search
            nearby_url = f"{self.base_url}/nearbysearch/json"
            params = {
                "key": self.api_key,
                "location": f"{location.latitude},{location.longitude}",
                "radius": location.radius,
                "type": "restaurant",
                "rankby": "prominence"  # Can also use "distance"
            }
            
            response = await self.client.get(nearby_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            restaurants = []
            for result in data.get("results", [])[:limit]:
                restaurant = await self._convert_to_restaurant_info(result)
                if restaurant:
                    restaurants.append(restaurant)
            
            # Sort by rating and total ratings
            restaurants.sort(key=lambda r: (r.rating, r.total_ratings), reverse=True)
            return restaurants[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching restaurants from Google Places: {e}")
            return await self._get_mock_restaurants(location, limit)
    
    async def get_restaurant_details(self, place_id: str) -> Optional[RestaurantInfo]:
        """Get detailed information about a specific restaurant"""
        if not self.api_key:
            return None
        
        try:
            details_url = f"{self.base_url}/details/json"
            params = {
                "key": self.api_key,
                "place_id": place_id,
                "fields": "name,rating,user_ratings_total,price_level,formatted_address,formatted_phone_number,website,opening_hours,geometry,photos,types,reviews"
            }
            
            response = await self.client.get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "result" in data:
                return await self._convert_to_restaurant_info(data["result"], detailed=True)
            
        except Exception as e:
            logger.error(f"Error fetching restaurant details: {e}")
        
        return None
    
    async def get_restaurant_reviews(self, place_id: str, max_reviews: int = 20) -> List[RestaurantReview]:
        """Get recent reviews for a restaurant"""
        if not self.api_key:
            return self._get_mock_reviews(place_id, max_reviews)
        
        try:
            # Get restaurant details including reviews
            restaurant = await self.get_restaurant_details(place_id)
            if not restaurant or not restaurant.recent_reviews:
                return self._get_mock_reviews(place_id, max_reviews)
            
            return restaurant.recent_reviews[:max_reviews]
            
        except Exception as e:
            logger.error(f"Error fetching reviews: {e}")
            return self._get_mock_reviews(place_id, max_reviews)
    
    async def get_photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        """Get actual photo URL from photo reference"""
        if not self.api_key:
            return f"https://via.placeholder.com/{max_width}x600/FF6B35/FFFFFF?text=Restaurant+Photo"
        
        return f"{self.base_url}/photo?maxwidth={max_width}&photoreference={photo_reference}&key={self.api_key}"
    
    async def _convert_to_restaurant_info(self, place_data: Dict[str, Any], detailed: bool = False) -> Optional[RestaurantInfo]:
        """Convert Google Places API response to RestaurantInfo model"""
        try:
            # Extract basic information
            place_id = place_data.get("place_id", "")
            name = place_data.get("name", "Unknown Restaurant")
            rating = place_data.get("rating", 0.0)
            total_ratings = place_data.get("user_ratings_total", 0)
            price_level = place_data.get("price_level")
            
            # Address
            address = place_data.get("formatted_address", place_data.get("vicinity", ""))
            
            # Location
            geometry = place_data.get("geometry", {})
            location_data = geometry.get("location", {})
            location = {
                "lat": location_data.get("lat", 0.0),
                "lng": location_data.get("lng", 0.0)
            }
            
            # Photos
            photos = []
            if "photos" in place_data:
                for photo in place_data["photos"][:5]:  # Limit to 5 photos
                    photo_ref = photo.get("photo_reference")
                    if photo_ref:
                        photo_url = await self.get_photo_url(photo_ref)
                        photos.append(photo_url)
            
            # Cuisine types
            cuisine_types = []
            if "types" in place_data:
                cuisine_types = [t for t in place_data["types"] if t not in ["establishment", "point_of_interest"]]
            
            # Reviews (if detailed)
            recent_reviews = []
            if detailed and "reviews" in place_data:
                for review_data in place_data["reviews"][:10]:
                    review = self._convert_to_review(review_data)
                    if review:
                        recent_reviews.append(review)
            
            return RestaurantInfo(
                place_id=place_id,
                name=name,
                address=address,
                rating=rating,
                total_ratings=total_ratings,
                price_level=price_level,
                cuisine_types=cuisine_types,
                phone_number=place_data.get("formatted_phone_number"),
                website=place_data.get("website"),
                opening_hours=place_data.get("opening_hours"),
                location=location,
                photos=photos,
                recent_reviews=recent_reviews,
                top_dishes=[],  # Will be populated by analysis service
                menu_photos=[]  # Will be populated by photo analysis service
            )
            
        except Exception as e:
            logger.error(f"Error converting place data: {e}")
            return None
    
    def _convert_to_review(self, review_data: Dict[str, Any]) -> Optional[RestaurantReview]:
        """Convert Google Places review data to RestaurantReview model"""
        try:
            return RestaurantReview(
                review_id=review_data.get("time", str(datetime.now().timestamp())),
                author_name=review_data.get("author_name", "Anonymous"),
                rating=review_data.get("rating", 5),
                text=review_data.get("text", ""),
                time=datetime.fromtimestamp(review_data.get("time", datetime.now().timestamp())),
                photos=[]  # Google Places API doesn't provide review photos directly
            )
        except Exception as e:
            logger.error(f"Error converting review data: {e}")
            return None
    
    async def _get_mock_restaurants(self, location: LocationRequest, limit: int) -> List[RestaurantInfo]:
        """Return mock restaurant data when API is not available"""
        mock_restaurants = [
            RestaurantInfo(
                place_id="mock_1",
                name="Tony's Authentic Pizzeria",
                address="123 Main Street, Downtown",
                rating=4.7,
                total_ratings=342,
                price_level=2,
                cuisine_types=["italian", "pizza"],
                phone_number="+1-555-0123",
                location={"lat": location.latitude + 0.001, "lng": location.longitude + 0.001},
                photos=["https://via.placeholder.com/800x600/FF6B35/FFFFFF?text=Tony's+Pizza"],
                top_dishes=[],
                recent_reviews=[],
                menu_photos=[]
            ),
            RestaurantInfo(
                place_id="mock_2",
                name="Spice Garden Indian Cuisine",
                address="456 Oak Avenue, Midtown",
                rating=4.6,
                total_ratings=298,
                price_level=2,
                cuisine_types=["indian", "curry"],
                phone_number="+1-555-0456",
                location={"lat": location.latitude + 0.002, "lng": location.longitude - 0.001},
                photos=["https://via.placeholder.com/800x600/E67E22/FFFFFF?text=Spice+Garden"],
                top_dishes=[],
                recent_reviews=[],
                menu_photos=[]
            ),
            RestaurantInfo(
                place_id="mock_3",
                name="Tokyo Bay Sushi Bar",
                address="789 Pine Road, Eastside",
                rating=4.8,
                total_ratings=456,
                price_level=3,
                cuisine_types=["japanese", "sushi"],
                phone_number="+1-555-0789",
                location={"lat": location.latitude - 0.001, "lng": location.longitude + 0.002},
                photos=["https://via.placeholder.com/800x600/3498DB/FFFFFF?text=Tokyo+Bay"],
                top_dishes=[],
                recent_reviews=[],
                menu_photos=[]
            ),
            RestaurantInfo(
                place_id="mock_4",
                name="Green Leaf Healthy Cafe",
                address="321 Elm Street, Westside",
                rating=4.5,
                total_ratings=189,
                price_level=2,
                cuisine_types=["healthy", "vegetarian"],
                phone_number="+1-555-0321",
                location={"lat": location.latitude + 0.003, "lng": location.longitude - 0.002},
                photos=["https://via.placeholder.com/800x600/27AE60/FFFFFF?text=Green+Leaf"],
                top_dishes=[],
                recent_reviews=[],
                menu_photos=[]
            ),
            RestaurantInfo(
                place_id="mock_5",
                name="Burger Palace Grill",
                address="654 Cedar Lane, Southside",
                rating=4.4,
                total_ratings=521,
                price_level=1,
                cuisine_types=["american", "burgers"],
                phone_number="+1-555-0654",
                location={"lat": location.latitude - 0.002, "lng": location.longitude - 0.001},
                photos=["https://via.placeholder.com/800x600/8B4513/FFFFFF?text=Burger+Palace"],
                top_dishes=[],
                recent_reviews=[],
                menu_photos=[]
            )
        ]
        
        return mock_restaurants[:limit]
    
    def _get_mock_reviews(self, place_id: str, max_reviews: int) -> List[RestaurantReview]:
        """Return mock review data"""
        mock_reviews = [
            RestaurantReview(
                review_id=f"{place_id}_review_1",
                author_name="Sarah Johnson",
                rating=5,
                text="Amazing food! The margherita pizza was absolutely delicious. The crust was perfect and the ingredients were fresh. Also tried their tiramisu which was heavenly. Highly recommend!",
                time=datetime.now(),
                photos=[]
            ),
            RestaurantReview(
                review_id=f"{place_id}_review_2",
                author_name="Mike Chen",
                rating=4,
                text="Great atmosphere and service. The chicken tikka masala was flavorful and the naan bread was soft and warm. Prices are reasonable for the portion size.",
                time=datetime.now(),
                photos=[]
            ),
            RestaurantReview(
                review_id=f"{place_id}_review_3",
                author_name="Emily Rodriguez",
                rating=5,
                text="Best sushi in town! The salmon sashimi was incredibly fresh and the California roll was perfectly made. The miso soup was also excellent. Will definitely come back!",
                time=datetime.now(),
                photos=[]
            )
        ]
        
        return mock_reviews[:max_reviews]
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


