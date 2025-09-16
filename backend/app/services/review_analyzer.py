import re
import logging
from typing import List, Dict, Tuple, Set
from collections import Counter
import asyncio
from datetime import datetime
from ..models.restaurant_models import RestaurantReview, DishInfo, ReviewAnalysis

logger = logging.getLogger(__name__)

class ReviewAnalyzer:
    """Service to analyze restaurant reviews and extract mentioned dishes"""
    
    def __init__(self):
        # Common food words and patterns
        self.food_keywords = {
            # Main dishes
            'pizza', 'burger', 'pasta', 'sushi', 'ramen', 'curry', 'steak', 'chicken', 'beef', 'pork',
            'fish', 'salmon', 'tuna', 'shrimp', 'lobster', 'crab', 'rice', 'noodles', 'soup', 'salad',
            'sandwich', 'wrap', 'taco', 'burrito', 'quesadilla', 'enchilada', 'pad thai', 'pho',
            'biryani', 'tikka masala', 'butter chicken', 'dal', 'samosa', 'dumplings', 'spring rolls',
            'fried rice', 'lo mein', 'chow mein', 'tempura', 'teriyaki', 'miso', 'udon', 'soba',
            
            # Appetizers and sides
            'appetizer', 'starter', 'wings', 'fries', 'onion rings', 'mozzarella sticks', 'nachos',
            'breadsticks', 'garlic bread', 'calamari', 'bruschetta', 'antipasto', 'hummus',
            
            # Desserts
            'dessert', 'cake', 'pie', 'ice cream', 'gelato', 'tiramisu', 'cheesecake', 'brownie',
            'cookie', 'pudding', 'mousse', 'tart', 'sorbet', 'cannoli', 'baklava',
            
            # Beverages
            'coffee', 'tea', 'latte', 'cappuccino', 'espresso', 'smoothie', 'juice', 'cocktail',
            'beer', 'wine', 'sake', 'lassi', 'chai'
        }
        
        # Dish name patterns (more specific dishes)
        self.dish_patterns = [
            # Pizza varieties
            r'\b(margherita|pepperoni|hawaiian|supreme|quattro stagioni|diavola|capricciosa)\s*pizza\b',
            r'\b(margherita|pepperoni|hawaiian|supreme)\b(?=.*pizza)',
            
            # Pasta dishes
            r'\b(spaghetti|fettuccine|penne|linguine|ravioli|lasagna|gnocchi)\s*(carbonara|bolognese|alfredo|arrabbiata|puttanesca|marinara)?\b',
            r'\b(carbonara|bolognese|alfredo|arrabbiata|puttanesca)\s*(pasta|spaghetti|penne)?\b',
            
            # Asian dishes
            r'\b(chicken|beef|pork|vegetable|shrimp)\s*(tikka masala|butter chicken|curry|teriyaki|pad thai|fried rice)\b',
            r'\b(miso|tom yum|pho|ramen)\s*soup\b',
            r'\b(california|spicy tuna|salmon|philadelphia)\s*roll\b',
            r'\b(chicken|beef|vegetable|pork)\s*(dumplings|spring rolls|pot stickers)\b',
            
            # American dishes
            r'\b(cheese|bacon|mushroom|veggie|turkey|club)\s*burger\b',
            r'\b(caesar|greek|cobb|garden|caprese)\s*salad\b',
            r'\b(buffalo|bbq|honey garlic|teriyaki)\s*wings\b',
            r'\b(fish|chicken|beef)\s*(tacos|sandwich|wrap)\b',
            
            # Breakfast items
            r'\b(pancakes|waffles|french toast|eggs benedict|omelet|frittata)\b',
            r'\b(bacon|sausage|ham)\s*(and eggs|breakfast)\b',
            
            # Desserts
            r'\b(chocolate|vanilla|strawberry|red velvet)\s*(cake|ice cream|cheesecake)\b',
            r'\b(apple|pumpkin|pecan|key lime)\s*pie\b',
            r'\b(chocolate|fudge|brownie)\s*(sundae|parfait)?\b'
        ]
        
        # Compile regex patterns
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dish_patterns]
        
        # Price patterns
        self.price_patterns = [
            r'\$(\d+(?:\.\d{2})?)',  # $12.99
            r'(\d+(?:\.\d{2})?)\s*dollars?',  # 12.99 dollars
            r'(\d+(?:\.\d{2})?)\s*bucks?',  # 12 bucks
            r'around\s*\$?(\d+(?:\.\d{2})?)',  # around $12
            r'about\s*\$?(\d+(?:\.\d{2})?)',  # about $12
            r'costs?\s*\$?(\d+(?:\.\d{2})?)',  # costs $12
            r'priced?\s*at\s*\$?(\d+(?:\.\d{2})?)',  # priced at $12
        ]
        
        self.compiled_price_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.price_patterns]
    
    async def analyze_reviews(self, reviews: List[RestaurantReview], restaurant_id: str) -> ReviewAnalysis:
        """Analyze reviews to extract mentioned dishes and sentiment"""
        start_time = datetime.now()
        
        mentioned_dishes = Counter()
        all_extracted_dishes = []
        total_sentiment = 0.0
        
        for review in reviews:
            # Extract dishes from review text
            dishes = self._extract_dishes_from_text(review.text)
            
            # Count mentions
            for dish in dishes:
                mentioned_dishes[dish.name] += 1
            
            all_extracted_dishes.extend(dishes)
            
            # Simple sentiment analysis based on rating
            total_sentiment += review.rating
        
        # Calculate average sentiment
        avg_sentiment = total_sentiment / len(reviews) if reviews else 0.0
        
        # Get most popular dishes
        popular_dishes = [dish for dish, count in mentioned_dishes.most_common(10)]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ReviewAnalysis(
            restaurant_id=restaurant_id,
            total_reviews_analyzed=len(reviews),
            mentioned_dishes=dict(mentioned_dishes),
            sentiment_score=avg_sentiment,
            popular_dishes=popular_dishes,
            processing_time=processing_time
        )
    
    def _extract_dishes_from_text(self, text: str) -> List[DishInfo]:
        """Extract dish names from review text"""
        extracted_dishes = []
        text_lower = text.lower()
        
        # First, try pattern matching for specific dishes
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text_lower)
            for match in matches:
                if isinstance(match, tuple):
                    # Handle groups in regex
                    dish_name = ' '.join([part for part in match if part]).strip()
                else:
                    dish_name = match.strip()
                
                if dish_name and len(dish_name) > 2:  # Filter out very short matches
                    # Try to extract price near this dish
                    price = self._extract_price_near_dish(text, dish_name)
                    
                    dish_info = DishInfo(
                        name=dish_name.title(),
                        price=price,
                        confidence=0.8,  # High confidence for pattern matches
                        mentions_count=1
                    )
                    extracted_dishes.append(dish_info)
        
        # Then, look for general food keywords
        words = re.findall(r'\b\w+\b', text_lower)
        for i, word in enumerate(words):
            if word in self.food_keywords:
                # Look for modifiers before and after
                dish_parts = []
                
                # Check previous words for modifiers
                for j in range(max(0, i-2), i):
                    if words[j] in ['chicken', 'beef', 'pork', 'vegetable', 'spicy', 'grilled', 'fried', 'baked']:
                        dish_parts.append(words[j])
                
                dish_parts.append(word)
                
                # Check next words for modifiers
                for j in range(i+1, min(len(words), i+3)):
                    if words[j] in ['masala', 'curry', 'sauce', 'soup', 'salad', 'roll', 'bowl']:
                        dish_parts.append(words[j])
                
                if len(dish_parts) > 1 or word in ['pizza', 'burger', 'sushi', 'pasta']:
                    dish_name = ' '.join(dish_parts)
                    
                    # Check if we already found this dish
                    if not any(existing.name.lower() == dish_name.lower() for existing in extracted_dishes):
                        price = self._extract_price_near_dish(text, dish_name)
                        
                        dish_info = DishInfo(
                            name=dish_name.title(),
                            price=price,
                            confidence=0.6,  # Lower confidence for keyword matches
                            mentions_count=1
                        )
                        extracted_dishes.append(dish_info)
        
        return extracted_dishes
    
    def _extract_price_near_dish(self, text: str, dish_name: str) -> Optional[str]:
        """Try to extract price mentioned near a dish name"""
        # Look for price patterns in the vicinity of the dish name
        dish_pos = text.lower().find(dish_name.lower())
        if dish_pos == -1:
            return None
        
        # Check 100 characters before and after the dish mention
        start = max(0, dish_pos - 100)
        end = min(len(text), dish_pos + len(dish_name) + 100)
        context = text[start:end]
        
        for pattern in self.compiled_price_patterns:
            matches = pattern.findall(context)
            if matches:
                # Return the first price found
                price = matches[0]
                if isinstance(price, tuple):
                    price = price[0]
                try:
                    # Validate it's a reasonable price (between $1 and $200)
                    price_float = float(price)
                    if 1.0 <= price_float <= 200.0:
                        return f"${price}"
                except ValueError:
                    continue
        
        return None
    
    async def extract_top_dishes(self, reviews: List[RestaurantReview], limit: int = 5) -> List[DishInfo]:
        """Extract the most mentioned dishes from reviews"""
        dish_counter = Counter()
        dish_info_map = {}
        
        for review in reviews:
            dishes = self._extract_dishes_from_text(review.text)
            for dish in dishes:
                key = dish.name.lower()
                dish_counter[key] += 1
                
                # Keep the dish info with the highest confidence or with price
                if key not in dish_info_map or (dish.price and not dish_info_map[key].price):
                    dish_info_map[key] = dish
        
        # Get top dishes and update their mention counts
        top_dishes = []
        for dish_key, count in dish_counter.most_common(limit):
            dish_info = dish_info_map[dish_key]
            dish_info.mentions_count = count
            top_dishes.append(dish_info)
        
        return top_dishes
    
    def calculate_dish_popularity_score(self, dish: DishInfo, total_reviews: int) -> float:
        """Calculate a popularity score for a dish based on mentions and confidence"""
        mention_ratio = dish.mentions_count / max(total_reviews, 1)
        confidence_weight = dish.confidence
        price_bonus = 0.1 if dish.price else 0.0
        
        return (mention_ratio * 0.7) + (confidence_weight * 0.2) + price_bonus


