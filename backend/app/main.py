from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import os
import uuid
import logging
from dotenv import load_dotenv

from .agents.multi_agent_system import MultiAgentSystem
from .models.request_models import (
    ConversationRequest, 
    ConversationResponse
)

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Restaurant Finder AI", 
    version="3.0.0",
    description="A conversational AI to help you find the best restaurants.",
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Application State ---
multi_agent_system = MultiAgentSystem()

# --- Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """Initialize the multi-agent system on startup"""
    logger.info("🚀 Starting up and initializing agent system...")
    await multi_agent_system.initialize()
    logger.info("✅ Agent system initialized.")

# --- API Endpoints ---
@app.get("/", tags=["General"])
async def root():
    """Root endpoint providing basic API information."""
    return {"message": "Welcome to the Restaurant Finder AI API"}

@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint to verify service status."""
    return {"status": "healthy", "agents": multi_agent_system.get_agent_status()}

@app.post("/chat", response_model=ConversationResponse, tags=["Chat"])
async def chat(request: ConversationRequest):
    """
    Main endpoint for conversational interaction with the chatbot.
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"Handling chat for session: {session_id}")
        
        result = await multi_agent_system.handle_conversation(
            user_input=request.user_input,
            session_id=session_id,
            history=request.history
        )
        
        return ConversationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error during chat session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
