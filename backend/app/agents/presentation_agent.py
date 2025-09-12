from typing import Dict, List, Any, Optional
import re
from .base_agent import BaseAgent

class PresentationAgent(BaseAgent):
    """
    Agent responsible for synthesizing restaurant data into a user-friendly summary.
    """
    
    def __init__(self):
        super().__init__("Presentation", temperature=0.7)
    
    async def _custom_initialize(self):
        pass
    
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
        """
        Creates a compelling, AI-generated summary for a restaurant featuring attractive foods.
        """
        # Extract food mentions from reviews
        reviews = restaurant_info.get('reviews', [])
        food_mentions = self._extract_food_mentions_from_reviews(reviews)
        
        # Get additional context
        rating = restaurant_info.get('rating')
        price_level = restaurant_info.get('price_level')
        types = restaurant_info.get('types', [])
        cuisine = restaurant_info.get('cuisine', 'Not specified')
        
        # Build price context
        price_context = ""
        if price_level:
            price_descriptors = {
                1: "budget-friendly",
                2: "reasonably priced", 
                3: "upscale",
                4: "fine dining"
            }
            price_context = price_descriptors.get(price_level, "")
        
        system_prompt = self._create_system_prompt(
            "Expert Food Critic and Restaurant Reviewer",
            [
                "Create 1-5 bullet points describing available foods and dishes.",
                "Each bullet point should be 1-3 words highlighting specific dishes.",
                "Never mention the restaurant name - only describe the food.",
                "Format as bullet points using • symbol.",
                "Focus on the most appealing and popular dishes."
            ]
        )
        
        # Build food mentions context
        food_context = ""
        if food_mentions:
            food_context = f"\nPopular dishes mentioned in reviews: {', '.join(food_mentions[:5])}"
        else:
            # Fallback food suggestions based on cuisine type
            cuisine_foods = {
                'italian': 'wood-fired pizza, fresh pasta, creamy risotto, tiramisu',
                'chinese': 'crispy dumplings, savory stir-fry, hand-pulled noodles, sweet & sour',
                'indian': 'butter chicken, aromatic biryani, tandoori kebabs, naan bread',
                'mexican': 'street tacos, loaded burritos, spicy enchiladas, fresh guacamole',
                'japanese': 'fresh sushi, rich ramen, crispy tempura, teriyaki',
                'thai': 'pad thai noodles, green curry, tom yum soup, mango sticky rice',
                'american': 'juicy burgers, grilled steaks, loaded fries, apple pie',
                'french': 'buttery croissants, delicate pastries, cheese soufflé, crème brûlée',
                'mediterranean': 'creamy hummus, grilled kebabs, crispy falafel, fresh tabbouleh'
            }
            for key, foods in cuisine_foods.items():
                if key in cuisine.lower():
                    food_context = f"\nTypical {cuisine} dishes: {foods}"
                    break
        
        user_prompt = f"""
        Create 1-5 bullet points describing the most appealing foods available:
        
        Cuisine: {cuisine}
        {food_context}
        
        Format as bullet points (•) with 1-3 words each. Focus on specific dishes that sound most appetizing. No restaurant name, just food descriptions.
        
        Example format:
        • Wood-fired pizza
        • Fresh pasta
        • Grilled chicken
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        summary = await self._query_llm(messages)
        return summary.strip()
