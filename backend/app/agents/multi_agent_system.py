import asyncio
import time
from typing import Dict, List, Any, Optional
import logging
from typing import Protocol

class PipelineStage(Protocol):
    is_initialized: bool
    async def initialize(self): ...

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
    
    def __init__(self, client=None):
        self.client = client
        self.agents: Dict[str, PipelineStage] = {}
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize all agents"""
        if self.is_initialized:
            return
            
        try:
            self.agents = {
                'chat': ChatAgent(),
                'search': SearchAgent(client=self.client),
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

    async def handle_conversation(self, user_input: str, session_id: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Handles the conversation with the user, determines intent, and triggers actions.
        """
        start_time = time.time()

        try:
            # 1. Chat Agent: Understand the user's request
            chat_agent: ChatAgent = self.agents['chat']
            convo_details: ConversationDetails = await chat_agent.run(user_input=user_input, history=history)

            if (convo_details.intent == 'search_restaurants' and
                    convo_details.location and not convo_details.location_ambiguous):
                # 2. If intent is to search, call the find_restaurants flow
                logger.info(f"Intent 'search_restaurants' recognized for session {session_id}")
                restaurant_results = await self.find_restaurants(
                    location=convo_details.location,
                    cuisine_type=convo_details.cuisine,
                )
                # Combine results with conversational response
                # Use no_results_message if available, otherwise use the original response
                if 'no_results_message' in restaurant_results:
                    restaurant_results['response'] = restaurant_results['no_results_message']
                else:
                    restaurant_results['response'] = convo_details.response
                
                restaurant_results['intent'] = 'search_restaurants'
                restaurant_results['session_id'] = session_id
                restaurant_results['processing_time_seconds'] = round(time.time() - start_time, 2)
                restaurant_results['search_performed'] = True  # Flag to indicate actual search was performed
                return restaurant_results

            elif convo_details.intent in ['location_clarification', 'cuisine_clarification']:
                # 3. Handle clarification requests - don't search, just ask for more info
                logger.info(f"Intent '{convo_details.intent}' recognized for session {session_id}")
                return {
                    'session_id': session_id,
                    'intent': convo_details.intent,
                    'response': convo_details.response,
                    'suggestions': [],
                    'processing_time_seconds': round(time.time() - start_time, 2),
                    'search_performed': False  # No search was performed, just asking for clarification
                }

            else:
                # 4. For other intents, just return the agent's response
                logger.info(f"Intent '{convo_details.intent}' recognized for session {session_id}")
                return {
                    'session_id': session_id,
                    'intent': convo_details.intent,
                    'response': convo_details.response,
                    'suggestions': [],
                    'processing_time_seconds': round(time.time() - start_time, 2),
                    'search_performed': False  # No search was performed
                }

        except Exception as e:
            logger.error(f"Error in handle_conversation: {e}")
            raise
    
    async def find_restaurants(self, location: str, cuisine_type: Optional[str]) -> Dict[str, Any]:
        """
        Main method to find restaurants using the multi-agent system with automatic radius extension.
        """
        try:
            # 1. Search Agent: Find all restaurants (open and closed) with automatic radius extension
            restaurants = await self.agents['search'].find_all_restaurants_with_radius_extension(
                location=location,
                cuisine=cuisine_type,
                min_results=2  # Minimum of 2 restaurants required
            )
            
            # Handle case when no restaurants are found
            if not restaurants:
                logger.info(f"No restaurants found for location: {location}, cuisine: {cuisine_type}")
                return {
                    'suggestions': [],
                    'no_results_message': self._generate_no_results_message(location, cuisine_type)
                }
            
            # 2. Process restaurants in parallel (Photos and Summaries)
            async def process_restaurant(resto):
                # Photo Agent: Get photo URLs
                photo_data = resto.get('photos', [])
                photo_url = await self.agents['photo'].get_primary_photo_url(photo_data)
                
                # Presentation Agent: Create a summary
                resto['cuisine'] = cuisine_type # Add cuisine to info for summary
                summary = await self.agents['presentation'].summarize_restaurant(resto)
                
                return RestaurantInfo(
                    name=resto.get('name'),
                    address=resto.get('address'),
                    rating=resto.get('rating'),
                    is_open_now=resto.get('is_open_now'),
                    photo_url=photo_url,
                    summary=summary,
                    place_id=resto.get('place_id'),
                    google_maps_uri=resto.get('google_maps_uri'),
                    opening_hours_periods=resto.get('opening_hours_periods'),
                    current_opening_hours=resto.get('current_opening_hours'),
                    regular_opening_hours=resto.get('regular_opening_hours'),
                    next_opening_time=resto.get('next_opening_time'),
                    next_opening_display=resto.get('next_opening_display')
                )

            suggestions = await asyncio.gather(*(process_restaurant(r) for r in restaurants))
            
            return {
                'suggestions': suggestions,
            }
            
        except Exception as e:
            logger.error(f"Error in find_restaurants: {e}")
            raise
    
    def _generate_no_results_message(self, location: str, cuisine_type: Optional[str]) -> str:
        """
        Generate a simple message when no restaurants are found.
        
        Args:
            location: The search location
            cuisine_type: The cuisine type searched for
            
        Returns:
            A concise user-friendly message
        """
        if cuisine_type:
            return f"Sorry, I couldn't find any {cuisine_type} restaurants in {location}. Try a different cuisine or location!"
        else:
            return f"Sorry, I couldn't find any restaurants in {location}. Try a different location or check back later!"
    
    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents"""
        return {name: "initialized" if agent.is_initialized else "unavailable"
                for name, agent in self.agents.items()}
