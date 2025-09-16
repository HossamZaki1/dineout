import logging
from typing import List, Optional
import asyncio
from datetime import datetime

from .google_places_service import GooglePlacesService
from .review_analyzer import ReviewAnalyzer
from .menu_photo_analyzer import MenuPhotoAnalyzer
from ..models.restaurant_models import (
    LocationRequest, 
    RestaurantInfo, 
    DiscoveryResponse, 
    DishInfo
)

logger = logging.getLogger(__name__)

class RestaurantDiscoveryService:
    """Main service that orchestrates restaurant discovery, review analysis, and menu photo analysis"""
    
    def __init__(self):
        self.places_service = GooglePlacesService()
        self.review_analyzer = ReviewAnalyzer()
        self.menu_analyzer = MenuPhotoAnalyzer()
    
    async def discover_restaurants_with_dishes(
        self, 
        location: LocationRequest, 
        limit: int = 10
    ) -> DiscoveryResponse:
        """
        Main method to discover restaurants with their top dishes and prices
        """
        logger.info(f"Starting restaurant discovery for location: {location.latitude}, {location.longitude}")
        
        try:
            # Step 1: Find nearby restaurants
            restaurants = await self.places_service.find_nearby_restaurants(location, limit)
            logger.info(f"Found {len(restaurants)} restaurants")
            
            # Step 2: Process each restaurant concurrently (but limit concurrency)
            processed_restaurants = []
            
            # Process restaurants in batches to avoid overwhelming APIs
            batch_size = 3
            for i in range(0, len(restaurants), batch_size):
                batch = restaurants[i:i+batch_size]
                batch_tasks = [self._process_restaurant_details(restaurant) for restaurant in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, RestaurantInfo):
                        processed_restaurants.append(result)
                    else:
                        logger.error(f"Error processing restaurant: {result}")
            
            # Step 3: Sort by rating and dish availability
            processed_restaurants.sort(
                key=lambda r: (len(r.top_dishes), r.rating, r.total_ratings), 
                reverse=True
            )
            
            return DiscoveryResponse(
                restaurants=processed_restaurants,
                total_found=len(processed_restaurants),
                search_location={"lat": location.latitude, "lng": location.longitude},
                search_radius=location.radius,
                generated_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in restaurant discovery: {e}")
            # Return empty response on error
            return DiscoveryResponse(
                restaurants=[],
                total_found=0,
                search_location={"lat": location.latitude, "lng": location.longitude},
                search_radius=location.radius,
                generated_at=datetime.now()
            )
    
    async def _process_restaurant_details(self, restaurant: RestaurantInfo) -> RestaurantInfo:
        """Process a single restaurant to extract dishes and menu information"""
        try:
            logger.info(f"Processing restaurant: {restaurant.name}")
            
            # Step 1: Get detailed restaurant information and reviews
            detailed_restaurant = await self.places_service.get_restaurant_details(restaurant.place_id)
            if detailed_restaurant:
                restaurant = detailed_restaurant
            
            # If no reviews in detailed info, get them separately
            if not restaurant.recent_reviews:
                restaurant.recent_reviews = await self.places_service.get_restaurant_reviews(
                    restaurant.place_id, max_reviews=20
                )
            
            if not restaurant.recent_reviews:
                logger.warning(f"No reviews found for {restaurant.name}")
                return restaurant
            
            # Step 2: Analyze reviews to extract mentioned dishes
            review_analysis = await self.review_analyzer.analyze_reviews(
                restaurant.recent_reviews, 
                restaurant.place_id
            )
            
            # Extract top dishes from reviews
            review_dishes = await self.review_analyzer.extract_top_dishes(
                restaurant.recent_reviews, 
                limit=10
            )
            
            # Step 3: Find and analyze menu photos
            menu_photo_urls = await self.menu_analyzer.find_menu_photos_in_reviews(
                restaurant.recent_reviews
            )
            
            # If no menu photos in reviews, use restaurant photos as potential menu photos
            if not menu_photo_urls and restaurant.photos:
                # Take first few restaurant photos as potential menu photos
                menu_photo_urls = restaurant.photos[:3]
            
            restaurant.menu_photos = menu_photo_urls
            
            # Step 4: Analyze menu photos if available
            menu_analyses = []
            if menu_photo_urls:
                logger.info(f"Analyzing {len(menu_photo_urls)} menu photos for {restaurant.name}")
                menu_analyses = await self.menu_analyzer.analyze_multiple_menu_photos(
                    menu_photo_urls[:5]  # Limit to 5 photos to avoid excessive API calls
                )
            
            # Step 5: Match dishes from reviews with menu photos
            if menu_analyses and review_dishes:
                matched_dishes = await self.menu_analyzer.match_dishes_with_reviews(
                    menu_analyses, 
                    review_dishes
                )
                restaurant.top_dishes = matched_dishes[:8]  # Limit to top 8 dishes
            else:
                # Use review dishes if no menu analysis available
                restaurant.top_dishes = review_dishes[:8]
            
            # Step 6: Ensure we have some dishes even if analysis fails
            if not restaurant.top_dishes:
                restaurant.top_dishes = self._generate_fallback_dishes(restaurant)
            
            logger.info(f"Completed processing {restaurant.name}: found {len(restaurant.top_dishes)} dishes")
            return restaurant
            
        except Exception as e:
            logger.error(f"Error processing restaurant {restaurant.name}: {e}")
            # Return restaurant with fallback dishes
            restaurant.top_dishes = self._generate_fallback_dishes(restaurant)
            return restaurant
    
    def _generate_fallback_dishes(self, restaurant: RestaurantInfo) -> List[DishInfo]:
        """Generate fallback dishes based on restaurant cuisine type"""
        fallback_dishes = []
        
        # Generate dishes based on cuisine type
        cuisine_dishes = {
            'italian': [
                DishInfo(name="Margherita Pizza", price="$16.99", confidence=0.5),
                DishInfo(name="Spaghetti Carbonara", price="$18.50", confidence=0.5),
                DishInfo(name="Caesar Salad", price="$12.99", confidence=0.5)
            ],
            'indian': [
                DishInfo(name="Chicken Tikka Masala", price="$19.99", confidence=0.5),
                DishInfo(name="Butter Chicken", price="$18.99", confidence=0.5),
                DishInfo(name="Garlic Naan", price="$4.99", confidence=0.5)
            ],
            'japanese': [
                DishInfo(name="California Roll", price="$12.99", confidence=0.5),
                DishInfo(name="Chicken Teriyaki", price="$16.99", confidence=0.5),
                DishInfo(name="Miso Soup", price="$4.99", confidence=0.5)
            ],
            'american': [
                DishInfo(name="Classic Burger", price="$14.99", confidence=0.5),
                DishInfo(name="Buffalo Wings", price="$11.99", confidence=0.5),
                DishInfo(name="French Fries", price="$6.99", confidence=0.5)
            ],
            'mexican': [
                DishInfo(name="Chicken Tacos", price="$12.99", confidence=0.5),
                DishInfo(name="Beef Burrito", price="$13.99", confidence=0.5),
                DishInfo(name="Guacamole", price="$7.99", confidence=0.5)
            ]
        }
        
        # Try to match cuisine types
        for cuisine_type in restaurant.cuisine_types:
            cuisine_lower = cuisine_type.lower()
            if cuisine_lower in cuisine_dishes:
                return cuisine_dishes[cuisine_lower]
        
        # Default fallback dishes
        return [
            DishInfo(name="House Special", price="$16.99", confidence=0.5),
            DishInfo(name="Chef's Choice", price="$18.99", confidence=0.5),
            DishInfo(name="Popular Dish", price="$14.99", confidence=0.5)
        ]
    
    async def get_restaurant_by_id(self, place_id: str) -> Optional[RestaurantInfo]:
        """Get detailed information for a specific restaurant"""
        try:
            restaurant = await self.places_service.get_restaurant_details(place_id)
            if restaurant:
                return await self._process_restaurant_details(restaurant)
        except Exception as e:
            logger.error(f"Error getting restaurant details: {e}")
        
        return None
    
    async def close(self):
        """Close all service connections"""
        await self.places_service.close()
        await self.menu_analyzer.close()


