"""
Chat Agent: Understands user's request, identifies intent, and extracts entities.
"""
from app.agents.base_agent import BaseAgent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional

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
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a friendly and helpful assistant for a restaurant suggestion app.
Your goal is to understand the user's request and extract the necessary information to find restaurants.
The required information is: location, cuisine, and search_radius.

- If the user's request is clearly about finding restaurants, set intent to 'search_restaurants'.
- If the user provides some but not all information, ask a clarifying question in the 'response' field and set intent to 'clarification'. For example, if they provide a location but not a cuisine, ask them what kind of food they're looking for.
- If the user's request is not about finding restaurants, politely decline in the 'response' field and set intent to 'other'.
- The user's location is critical. If it's not provided, you must ask for it.
- Assume a default search radius of 5000 meters if not specified.
- For cuisine, if the user doesn't specify, you can default to 'any'.
- Keep your response friendly and conversational.
"""),
            ("human", "Previous conversation: {history}"),
            ("human", "User request: {input}"),
        ])

        chain = prompt | self.llm
        
        return chain.invoke({
            "input": user_input,
            "history": history
        })

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
