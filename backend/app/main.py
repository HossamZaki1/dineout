from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
import logging
from dotenv import load_dotenv

from .agents.multi_agent_system import MultiAgentSystem
from .conversations import ConversationService, conversation_router
from .conversations.router import set_conversation_service

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

# Initialize conversation service
try:
    conversation_service = ConversationService(multi_agent_system=multi_agent_system)
    set_conversation_service(conversation_service)
    logger.info("Conversation service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize conversation service: {e}")
    conversation_service = None

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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return an empty favicon to prevent 404 errors."""
    return Response(status_code=204)

# --- Include Routers ---
app.include_router(conversation_router)

# All conversation endpoints have been moved to the conversations router

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
