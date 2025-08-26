from typing import Dict, List, Any
from .base_agent import BaseAgent
import os

class PhotoAgent(BaseAgent):
    """
    Agent responsible for fetching photo URLs for restaurants using the Google Places API.
    """
    
    def __init__(self):
        super().__init__("Photo", temperature=0.1)
        self.api_key = os.getenv("GOOGLE_API_KEY")

    async def _custom_initialize(self):
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

    async def get_primary_photo_url(self, photos_data: List[Dict]) -> str | None:
        """
        Constructs a single photo URL for the primary (first) photo from the Places API data.
        """
        if not photos_data:
            return None
        
        primary_photo = photos_data[0]
        photo_name = primary_photo.get('name')
        
        if photo_name:
            return f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&key={self.api_key}"
        return None
