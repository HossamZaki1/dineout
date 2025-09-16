import os
import re
import logging
from typing import List, Dict, Optional, Tuple
import httpx
import asyncio
from datetime import datetime
import base64
from ..models.restaurant_models import MenuPhotoAnalysis, DishInfo, RestaurantReview

logger = logging.getLogger(__name__)

class MenuPhotoAnalyzer:
    """Service to analyze menu photos and extract dish information with prices"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            logger.warning("Gemini API key not found. Using mock photo analysis.")
        
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Price patterns for menu extraction
        self.price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',  # $12.99
            r'(\d+(?:\.\d{2})?)\s*\$',  # 12.99$
            r'(\d+(?:\.\d{2})?)\s*USD',  # 12.99 USD
            r'(\d+(?:\.\d{2})?)\s*dollars?',  # 12.99 dollars
            r'Price:?\s*\$?(\d+(?:\.\d{2})?)',  # Price: $12.99
        ]
        
        self.compiled_price_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.price_patterns]
    
    async def find_menu_photos_in_reviews(self, reviews: List[RestaurantReview]) -> List[str]:
        """Extract menu photo URLs from restaurant reviews"""
        menu_photos = []
        
        for review in reviews:
            # Check if review mentions menu-related keywords
            menu_keywords = ['menu', 'price', 'cost', 'dish', 'food', 'meal', 'order']
            review_text_lower = review.text.lower()
            
            if any(keyword in review_text_lower for keyword in menu_keywords):
                # Add review photos as potential menu photos
                menu_photos.extend(review.photos)
        
        # Remove duplicates
        return list(set(menu_photos))
    
    async def analyze_menu_photo(self, photo_url: str, upload_date: Optional[datetime] = None) -> MenuPhotoAnalysis:
        """Analyze a menu photo to extract dishes and prices"""
        start_time = datetime.now()
        
        if not self.gemini_api_key:
            return await self._get_mock_menu_analysis(photo_url, upload_date)
        
        try:
            # Download the image
            image_response = await self.client.get(photo_url)
            image_response.raise_for_status()
            image_data = image_response.content
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare the request for Gemini Vision
            request_data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": """Analyze this menu image and extract all dishes with their prices. 
                                Return the information in this exact JSON format:
                                {
                                    "dishes": [
                                        {
                                            "name": "dish name",
                                            "price": "price as string with $ symbol",
                                            "confidence": confidence_score_between_0_and_1
                                        }
                                    ],
                                    "is_menu": true/false,
                                    "overall_confidence": overall_confidence_score
                                }
                                
                                Only include items that clearly have both a dish name and a price. 
                                Be conservative with confidence scores - only use high confidence (>0.8) for very clear text.
                                Set is_menu to false if this doesn't appear to be a menu image."""
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Make request to Gemini
            response = await self.client.post(
                f"{self.gemini_url}?key={self.gemini_api_key}",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse the response
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                return await self._parse_gemini_response(content, photo_url, upload_date, start_time)
            
        except Exception as e:
            logger.error(f"Error analyzing menu photo with Gemini: {e}")
        
        # Fallback to mock analysis
        return await self._get_mock_menu_analysis(photo_url, upload_date)
    
    async def _parse_gemini_response(self, response_text: str, photo_url: str, upload_date: Optional[datetime], start_time: datetime) -> MenuPhotoAnalysis:
        """Parse Gemini's response and create MenuPhotoAnalysis"""
        try:
            # Try to extract JSON from the response
            import json
            
            # Clean up the response text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                data = json.loads(json_text)
                
                extracted_dishes = []
                
                if data.get("is_menu", False) and "dishes" in data:
                    for dish_data in data["dishes"]:
                        dish = DishInfo(
                            name=dish_data.get("name", ""),
                            price=dish_data.get("price", ""),
                            confidence=float(dish_data.get("confidence", 0.5)),
                            menu_photo_url=photo_url,
                            photo_upload_date=upload_date,
                            mentions_count=1
                        )
                        extracted_dishes.append(dish)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return MenuPhotoAnalysis(
                    photo_url=photo_url,
                    extracted_dishes=extracted_dishes,
                    upload_date=upload_date,
                    confidence_score=float(data.get("overall_confidence", 0.5)),
                    processing_time=processing_time
                )
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
        
        # Fallback to mock analysis
        return await self._get_mock_menu_analysis(photo_url, upload_date)
    
    async def _get_mock_menu_analysis(self, photo_url: str, upload_date: Optional[datetime]) -> MenuPhotoAnalysis:
        """Return mock menu analysis when API is not available"""
        # Simulate some processing time
        await asyncio.sleep(0.5)
        
        # Generate mock dishes based on common menu items
        mock_dishes = [
            DishInfo(
                name="Margherita Pizza",
                price="$16.99",
                confidence=0.9,
                menu_photo_url=photo_url,
                photo_upload_date=upload_date,
                mentions_count=1
            ),
            DishInfo(
                name="Caesar Salad",
                price="$12.50",
                confidence=0.85,
                menu_photo_url=photo_url,
                photo_upload_date=upload_date,
                mentions_count=1
            ),
            DishInfo(
                name="Grilled Chicken Breast",
                price="$22.00",
                confidence=0.8,
                menu_photo_url=photo_url,
                photo_upload_date=upload_date,
                mentions_count=1
            )
        ]
        
        processing_time = 0.5
        
        return MenuPhotoAnalysis(
            photo_url=photo_url,
            extracted_dishes=mock_dishes,
            upload_date=upload_date,
            confidence_score=0.85,
            processing_time=processing_time
        )
    
    async def analyze_multiple_menu_photos(self, photo_urls: List[str]) -> List[MenuPhotoAnalysis]:
        """Analyze multiple menu photos concurrently"""
        tasks = []
        for url in photo_urls:
            task = self.analyze_menu_photo(url)
            tasks.append(task)
        
        # Process up to 5 photos concurrently to avoid rate limiting
        results = []
        for i in range(0, len(tasks), 5):
            batch = tasks[i:i+5]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, MenuPhotoAnalysis):
                    results.append(result)
                else:
                    logger.error(f"Error in menu photo analysis: {result}")
        
        return results
    
    async def match_dishes_with_reviews(self, menu_analyses: List[MenuPhotoAnalysis], review_dishes: List[DishInfo]) -> List[DishInfo]:
        """Match dishes found in menu photos with dishes mentioned in reviews"""
        matched_dishes = []
        
        # Create a map of review dishes by name (lowercase for matching)
        review_dish_map = {dish.name.lower(): dish for dish in review_dishes}
        
        for analysis in menu_analyses:
            for menu_dish in analysis.extracted_dishes:
                menu_dish_lower = menu_dish.name.lower()
                
                # Look for exact matches first
                if menu_dish_lower in review_dish_map:
                    review_dish = review_dish_map[menu_dish_lower]
                    
                    # Merge information - prefer menu photo price if available
                    merged_dish = DishInfo(
                        name=review_dish.name,  # Use review name (might have better capitalization)
                        price=menu_dish.price or review_dish.price,
                        confidence=max(menu_dish.confidence, review_dish.confidence),
                        menu_photo_url=menu_dish.menu_photo_url,
                        photo_upload_date=menu_dish.photo_upload_date,
                        mentions_count=review_dish.mentions_count
                    )
                    matched_dishes.append(merged_dish)
                    
                # Look for partial matches
                else:
                    for review_name, review_dish in review_dish_map.items():
                        if self._is_similar_dish(menu_dish.name, review_name):
                            merged_dish = DishInfo(
                                name=review_dish.name,
                                price=menu_dish.price or review_dish.price,
                                confidence=min(menu_dish.confidence * 0.8, review_dish.confidence),  # Reduce confidence for partial match
                                menu_photo_url=menu_dish.menu_photo_url,
                                photo_upload_date=menu_dish.photo_upload_date,
                                mentions_count=review_dish.mentions_count
                            )
                            matched_dishes.append(merged_dish)
                            break
                    else:
                        # No match found in reviews, but dish exists in menu
                        if menu_dish.confidence > 0.7:  # Only include high-confidence menu items
                            matched_dishes.append(menu_dish)
        
        # Remove duplicates and sort by popularity and confidence
        seen_dishes = set()
        unique_dishes = []
        
        for dish in matched_dishes:
            dish_key = dish.name.lower()
            if dish_key not in seen_dishes:
                seen_dishes.add(dish_key)
                unique_dishes.append(dish)
        
        # Sort by mentions count (popularity) and confidence
        unique_dishes.sort(key=lambda d: (d.mentions_count, d.confidence), reverse=True)
        
        return unique_dishes
    
    def _is_similar_dish(self, name1: str, name2: str) -> bool:
        """Check if two dish names are similar enough to be considered the same dish"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Check if one name contains the other
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return True
        
        # Check for common word overlap
        words1 = set(name1_lower.split())
        words2 = set(name2_lower.split())
        
        # Remove common words that don't help with matching
        common_words = {'with', 'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at'}
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return False
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= 0.5  # 50% word overlap threshold
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


