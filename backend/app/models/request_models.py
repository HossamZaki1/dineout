from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class RestaurantRequest(BaseModel):
    """Request model for finding restaurants."""
    location: str = Field(..., description="The city, address, or general area to search for restaurants.")
    cuisine_type: Optional[str] = Field(None, description="Optional cuisine type to filter by (e.g., 'Italian', 'Sushi').")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location": "San Francisco, CA",
                "cuisine_type": "sushi"
            }
        }
    )

class RestaurantInfo(BaseModel):
    """Detailed information about a single restaurant."""
    name: Optional[str]
    address: Optional[str]
    rating: Optional[float]
    is_open_now: Optional[bool]
    photo_url: Optional[str] = None
    summary: Optional[str]
    place_id: Optional[str] = None
    google_maps_uri: Optional[str] = None
    opening_hours_periods: Optional[List[Dict[str, Any]]] = None
    current_opening_hours: Optional[Dict[str, Any]] = None
    regular_opening_hours: Optional[Dict[str, Any]] = None
    next_opening_time: Optional[float] = None
    next_opening_display: Optional[str] = None

class RestaurantResponse(BaseModel):
    """Response model containing a list of restaurant suggestions."""
    session_id: str
    suggestions: List[RestaurantInfo]
    processing_time_seconds: float

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "suggestions": [
                    {
                        "name": "The Sushi Spot",
                        "address": "123 Main St, San Francisco, CA",
                        "rating": 4.5,
                        "is_open_now": True,
                        "photo_urls": ["https://example.com/photo1.jpg"],
                        "summary": "A trendy and popular spot known for its fresh fish and creative rolls."
                    }
                ],
                "processing_time_seconds": 4.75
            }
        }
    )

# Conversation models have been moved to app.conversations.models
