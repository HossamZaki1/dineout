from typing import Dict, List, Any
from .base_agent import BaseAgent

class PresentationAgent(BaseAgent):
    """
    Agent responsible for synthesizing restaurant data into a user-friendly summary.
    """
    
    def __init__(self):
        super().__init__("Presentation", temperature=0.7)
    
    async def _custom_initialize(self):
        pass
    
    async def summarize_restaurant(self, restaurant_info: Dict[str, Any]) -> str:
        """
        Creates a compelling, AI-generated summary for a restaurant.
        """
        
        system_prompt = self._create_system_prompt(
            "Restaurant Critic and Food Blogger",
            [
                "Create a short, enticing summary for a restaurant based on its details.",
                "Highlight the best features, like cuisine, rating, and atmosphere.",
                "Keep the tone engaging and appetizing."
            ]
        )
        
        user_prompt = f"""
        Please create a summary for the following restaurant:
        
        Name: {restaurant_info.get('name')}
        Address: {restaurant_info.get('address')}
        Rating: {restaurant_info.get('rating')}
        Cuisine: {restaurant_info.get('cuisine', 'Not specified')}
        
        Write a one-sentence summary that would make someone want to go there.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        summary = await self._query_llm(messages)
        return summary.strip()
