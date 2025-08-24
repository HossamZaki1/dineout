from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system using Google Gemini.
    """
    
    def __init__(self, agent_name: str, temperature: float = 0.7):
        self.agent_name = agent_name
        self.temperature = temperature
        self.llm: Optional[ChatGoogleGenerativeAI] = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the agent with the Gemini LLM and any other required setup"""
        try:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=self.temperature,
                google_api_key=google_api_key,
                convert_system_message_to_human=True # Gemini API has a different message structure
            )
            
            await self._custom_initialize()
            self.is_initialized = True
            logger.info(f"{self.agent_name} agent initialized successfully with Google Gemini")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_name} agent: {e}")
            raise
    
    @abstractmethod
    async def _custom_initialize(self):
        """Custom initialization logic for each agent"""
        pass
    
    def _create_system_prompt(self, role_description: str, guidelines: List[str]) -> str:
        """Create a consistent system prompt for the agent"""
        guidelines_text = "\n".join([f"- {guideline}" for guideline in guidelines])
        
        # For Gemini, the system prompt is often part of the first user message.
        return f"""**Role: {role_description}**

**Your Task:**
You are a specialized agent in a multi-agent system. Your goal is to provide expert assistance based on the user's request.

**Guidelines:**
{guidelines_text}

Please provide your response in the requested format.
"""
    
    async def _query_llm(self, messages: List[Dict[str, str]]) -> str:
        """Query the Gemini LLM with the given messages"""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # The ChatGoogleGenerativeAI model with convert_system_message_to_human=True
                    # will handle this appropriately.
                    langchain_messages.append(SystemMessage(content=msg["content"]))
                elif msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
            
            response = await self.llm.ainvoke(langchain_messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Error querying LLM in {self.agent_name}: {e}")
            raise
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling various formats"""
        import json
        import re
        
        # Try to find JSON in the response
        json_pattern = r'```json\s*(.*?)\s*```'
        json_match = re.search(json_pattern, response, re.DOTALL)
        
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to parse the entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Fallback: try to find JSON-like content
        json_pattern = r'\{.*\}'
        json_match = re.search(json_pattern, response, re.DOTALL)
        
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all else fails, return a structured response with the raw text
        return {
            "raw_response": response,
            "parsing_error": "Could not extract JSON from response"
        }
