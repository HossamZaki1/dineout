import asyncio
import time
from typing import Dict, List, Any, Optional
import logging

from .base_agent import BaseAgent
from .search_agent import SearchAgent
from .photo_agent import PhotoAgent
from .presentation_agent import PresentationAgent
from .chat_agent import ChatAgent, ConversationDetails
from ..models.request_models import RestaurantInfo

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """
    Orchestrates multiple specialized agents to find and present restaurant suggestions.
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all agents"""
        if self.is_initialized:
            return
            
        try:
            self.agents = {
                'chat': ChatAgent(),
                'search': SearchAgent(),
                'photo': PhotoAgent(),
                'presentation': PresentationAgent()
            }
            
            for agent_name, agent in self.agents.items():
                await agent.initialize()
                logger.info(f"Initialized {agent_name} agent")
            
            self.is_initialized = True
            logger.info("Restaurant finder multi-agent system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize multi-agent system: {e}")
            raise

    async def handle_conversation(self, user_input: str, session_id: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """
        Handles the conversation with the user, determines intent, and triggers actions.
        """
        start_time = time.time()

        try:
            # 1. Chat Agent: Understand the user's request
            chat_agent: ChatAgent = self.agents['chat']
            convo_details: ConversationDetails = await asyncio.to_thread(
                chat_agent.run, user_input=user_input, history=history
            )

            if convo_details.intent == 'search_restaurants':
                # 2. If intent is to search, call the find_restaurants flow
                logger.info(f"Intent 'search_restaurants' recognized for session {session_id}")
                restaurant_results = await self.find_restaurants(
                    location=convo_details.location,
                    cuisine_type=convo_details.cuisine,
                )
                # Combine results with conversational response
                restaurant_results['response'] = convo_details.response
                restaurant_results['intent'] = 'search_restaurants'
                restaurant_results['session_id'] = session_id
                restaurant_results['processing_time_seconds'] = round(time.time() - start_time, 2)
                return restaurant_results

            else:
                # 3. For other intents, just return the agent's response
                logger.info(f"Intent '{convo_details.intent}' recognized for session {session_id}")
                return {
                    'session_id': session_id,
                    'intent': convo_details.intent,
                    'response': convo_details.response,
                    'suggestions': [],
                    'processing_time_seconds': round(time.time() - start_time, 2)
                }

        except Exception as e:
            logger.error(f"Error in handle_conversation: {e}")
            raise
    
    async def find_restaurants(self, location: str, cuisine_type: Optional[str]) -> Dict[str, Any]:
        """
        Main method to find restaurants using the multi-agent system.
        """
        try:
            # 1. Search Agent: Find open restaurants
            restaurants = await self.agents['search'].find_open_restaurants(
                location=location,
                cuisine=cuisine_type
            )
            
            # 2. Process restaurants in parallel (Photos and Summaries)
            async def process_restaurant(resto):
                # Photo Agent: Get photo URLs
                photo_data = resto.get('photos', [])
                photo_urls = await self.agents['photo'].get_photo_urls(photo_data)
                
                # Presentation Agent: Create a summary
                resto['cuisine'] = cuisine_type # Add cuisine to info for summary
                summary = await self.agents['presentation'].summarize_restaurant(resto)
                
                return RestaurantInfo(
                    name=resto.get('name'),
                    address=resto.get('address'),
                    rating=resto.get('rating'),
                    is_open_now=resto.get('is_open_now'),
                    photo_urls=photo_urls,
                    summary=summary
                )

            suggestions = await asyncio.gather(*(process_restaurant(r) for r in restaurants))
            
            return {
                'suggestions': suggestions,
            }
            
        except Exception as e:
            logger.error(f"Error in find_restaurants: {e}")
            raise
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents"""
        return {name: "initialized" for name in self.agents}
