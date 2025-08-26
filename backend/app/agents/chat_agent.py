"""
Chat Agent: Understands user's request, identifies intent, and extracts entities.
"""
from app.agents.base_agent import BaseAgent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

class ConversationDetails(BaseModel):
    """Structured data extracted from the user's request."""
    intent: str = Field(description="The user's intent. Should be 'search_restaurants' or 'clarification' or 'other'.")
    location: Optional[str] = Field(description="The city or area the user wants to search for restaurants in.")
    cuisine: Optional[str] = Field(description="The type of food the user is interested in (e.g., 'Italian', 'Mexican', 'any').")
    search_radius: int = Field(default=5000, description="The search radius in meters.")
    response: str = Field(description="A natural language response to the user.")

class ChatAgent(BaseAgent):
    """An agent that analyzes user input to determine intent and extract entities."""

    def __init__(self):
        """Initializes the ChatAgent with a structured LLM."""
        super().__init__(agent_name="ChatAgent")

    async def _custom_initialize(self):
        """Custom initialization for ChatAgent."""
        pass

    def run(self, user_input: str, history: list = []) -> ConversationDetails:
        """
        Analyzes the user's input to extract conversation details.

        Args:
            user_input: The user's message.
            history: The conversation history.

        Returns:
            A ConversationDetails object with the extracted information.
        """
        # Ensure the agent is initialized
        if not self.is_initialized or not self.llm:
            raise RuntimeError("ChatAgent not initialized. Call initialize() first.")

        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a friendly and helpful assistant for a restaurant suggestion app.
Your goal is to understand the user's request and extract the necessary information to find restaurants.

Analyze the user's input and respond with a JSON object containing:
- intent: 'search_restaurants' if looking for restaurants, 'clarification' if need more info, 'other' if unrelated
- location: the city/area mentioned (null if not provided)
- cuisine: the food type mentioned (null if not specified, 'any' if they want any type)
- search_radius: 5000 (default)
- response: a friendly conversational response

Examples:
User: "I want Italian food in San Francisco"
{{"intent": "search_restaurants", "location": "San Francisco", "cuisine": "Italian", "search_radius": 5000, "response": "Great! I'll help you find Italian restaurants in San Francisco."}}

User: "Find restaurants in NYC"
{{"intent": "clarification", "location": "NYC", "cuisine": null, "search_radius": 5000, "response": "I'd be happy to help you find restaurants in NYC! What type of cuisine are you in the mood for?"}}

User: "What's the weather?"
{{"intent": "other", "location": null, "cuisine": null, "search_radius": 5000, "response": "I'm a restaurant finder assistant. I can help you discover great places to eat! What kind of food are you looking for?"}}

Always respond with valid JSON only, no additional text.
"""),
            ("human", "Previous conversation: {history}"),
            ("human", "User request: {input}"),
        ])

        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "input": user_input,
                "history": str(history) if history else "No previous conversation"
            })

            # Parse the JSON response from the LLM
            response_text = response.content.strip()
            logger.info(f"Raw LLM response: {response_text}")

            # Try to extract JSON from the response
            if response_text.startswith('```json'):
                # Remove markdown code block formatting
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                # Remove any code block formatting
                response_text = response_text.replace('```', '').strip()

            # Find JSON object in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                response_text = response_text[start_idx:end_idx]

            response_data = json.loads(response_text)
            logger.info(f"Parsed response data: {response_data}")

            # Create ConversationDetails object from parsed JSON
            return ConversationDetails(
                intent=response_data.get('intent', 'other'),
                location=response_data.get('location'),
                cuisine=response_data.get('cuisine'),
                search_radius=response_data.get('search_radius', 5000),
                response=response_data.get('response', 'I can help you find restaurants!')
            )

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback if JSON parsing fails
            logger.error(f"Failed to parse LLM response: {e}. Raw response: {response_text if 'response_text' in locals() else 'No response'}")
            return ConversationDetails(
                intent='other',
                location=None,
                cuisine=None,
                search_radius=5000,
                response="I'm here to help you find restaurants! Could you tell me what kind of food you're looking for and where?"
            )

if __name__ == '__main__':
    # Example usage
    chat_agent = ChatAgent()
    
    # Example 1: Clear request
    print("--- Example 1: Clear request ---")
    result1 = chat_agent.run("Hi, I'm looking for Italian restaurants in New York")
    print(result1)

    # Example 2: Missing cuisine
    print("\n--- Example 2: Missing cuisine ---")
    result2 = chat_agent.run("Find me a place to eat in San Francisco")
    print(result2)

    # Example 3: Irrelevant request
    print("\n--- Example 3: Irrelevant request ---")
    result3 = chat_agent.run("What's the weather like today?")
    print(result3)
