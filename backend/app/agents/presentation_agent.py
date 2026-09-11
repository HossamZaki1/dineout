from typing import Dict, List, Any, Optional
import re

class PresentationAgent:
    """
    Agent responsible for synthesizing restaurant data into a user-friendly summary.
    """
    
    def __init__(self):
        self.is_initialized = False
    
    async def initialize(self):
        self.is_initialized = True
    
    def _extract_food_mentions_from_reviews(self, reviews: List[Dict[str, Any]]) -> List[str]:
        """
        Extract food and dish mentions from restaurant reviews.
        """
        food_mentions = []
        
        # Common food words and patterns to look for in reviews
        food_patterns = [
            # Specific dishes
            r'\b(?:pasta|pizza|burger|sandwich|salad|soup|steak|chicken|fish|seafood|sushi|tacos|burrito|ramen|curry|pad thai|pho|biryani|risotto|gnocchi|lasagna|carbonara|alfredo)\b',
            # Cooking styles
            r'\b(?:grilled|fried|baked|roasted|seared|braised|steamed|smoked|barbecued|pan-fried)\s+\w+\b',
            # Food descriptors
            r'\b(?:crispy|tender|juicy|flavorful|delicious|amazing|incredible|fantastic|perfect|fresh|authentic|homemade)\s+(?:chicken|beef|pork|lamb|fish|salmon|tuna|shrimp|lobster|crab|pasta|pizza|bread|dessert|cake|pie)\b',
            # Specific menu items (often in quotes or capitalized)
            r'"[^"]*(?:chicken|beef|fish|pasta|pizza|burger|sandwich|salad)[^"]*"',
            r'\b[A-Z][a-z]+\s+(?:Chicken|Beef|Fish|Pasta|Pizza|Burger|Sandwich|Salad|Soup|Steak)\b'
        ]
        
        if not reviews:
            return []
        
        # Process up to 10 most recent reviews
        for review in reviews[:10]:
            review_text = review.get('text', {}).get('text', '') if isinstance(review.get('text'), dict) else review.get('text', '')
            if not review_text:
                continue
                
            # Extract food mentions using patterns
            for pattern in food_patterns:
                matches = re.findall(pattern, review_text, re.IGNORECASE)
                food_mentions.extend(matches)
        
        # Clean and deduplicate mentions
        cleaned_mentions = []
        seen = set()
        for mention in food_mentions:
            clean_mention = mention.strip().lower()
            if clean_mention and len(clean_mention) > 2 and clean_mention not in seen:
                seen.add(clean_mention)
                cleaned_mentions.append(mention.strip())
        
        return cleaned_mentions[:8]  # Return top 8 mentions
    
    async def summarize_restaurant(self, restaurant_info: Dict[str, Any]) -> str:
        """Report review mentions without inventing or claiming current menu items."""
        mentions = self._extract_food_mentions_from_reviews(restaurant_info.get('reviews') or [])
        if not mentions:
            return "Menu details are not available. Check with the restaurant."
        return "Mentioned in reviews (availability not confirmed):\n" + "\n".join(
            f"• {mention}" for mention in mentions[:5]
        )
