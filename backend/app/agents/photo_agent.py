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

    async def get_photo_urls(self, photos_data: List[Dict]) -> List[str]:
        """
        Constructs photo URLs from the photo data provided by the Places API.
        """
        photo_urls = []
        for photo in photos_data:
            # The 'name' field in the photo object contains the resource name needed for the URL.
            photo_name = photo.get('name')
            if photo_name:
                # Construct the URL for the photo
                # You can specify max height and width
                url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&key={self.api_key}"
                photo_urls.append(url)
        return photo_urls
