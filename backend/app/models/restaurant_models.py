from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class LocationRequest(BaseModel):
    """User location for restaurant search"""
    latitude: float
    longitude: float
    radius: int = 5000  # meters

class DishInfo(BaseModel):
    """Dish information"""
    name: str
    price: Optional[str] = None
    confidence: float = 0.8
    mentions_count: int = 1

class RestaurantReview(BaseModel):
    """Restaurant review information"""
    review_id: str
    author_name: str
    rating: float
    text: str
    time: datetime
    photos: List[str] = Field(default_factory=list)

class RestaurantInfo(BaseModel):
    """Restaurant information"""
    place_id: str
    name: str
    address: str
    rating: float
    total_ratings: int
    price_level: Optional[int] = None
    cuisine_types: List[str] = Field(default_factory=list)
    phone_number: Optional[str] = None
    location: Dict[str, float]  # {"lat": 0.0, "lng": 0.0}
    photos: List[str] = Field(default_factory=list)
    top_dishes: List[DishInfo] = Field(default_factory=list)
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    recent_reviews: List[RestaurantReview] = Field(default_factory=list)
    menu_photos: List[str] = Field(default_factory=list)

class DiscoveryResponse(BaseModel):
    """API response for restaurant discovery"""
    restaurants: List[RestaurantInfo]
    total_found: int
    search_location: Dict[str, float]
    generated_at: datetime = Field(default_factory=datetime.now)
