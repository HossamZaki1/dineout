from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import List, Dict, Any, Optional
import os
import uuid
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from .agents.multi_agent_system import MultiAgentSystem
from .models.request_models import (
    ConversationRequest, 
    ConversationResponse,
    ConversationMeta,
    ConversationMetaUpsert,
)
from .storage.firestore_conversation_store import FirestoreConversationStore

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

# Use Firestore for conversations
try:
    conversation_store = FirestoreConversationStore()
    logger.info("Using FirestoreConversationStore for conversations")
except Exception as e:
    logger.error(f"Failed to initialize FirestoreConversationStore: {e}. Conversation features will be unavailable.")
    conversation_store = None

# --- Helpers ---
def _derive_title(history: List[Dict[str, str]], fallback: str) -> str:
    try:
        for item in history:
            if item.get("role") == "user":
                text = (item.get("content") or "").strip()
                if text:
                    return text if len(text) <= 50 else text[:50] + "…"
    except Exception:
        pass
    fb = (fallback or "New Search").strip()
    return fb if len(fb) <= 50 else fb[:50] + "…"

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

@app.post("/chat", response_model=ConversationResponse, tags=["Chat"])
async def chat(request: ConversationRequest):
    """
    Main endpoint for conversational interaction with the chatbot.
    Optionally persists conversation metadata when user_id is provided.
    """
    try:

        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"Handling chat for session: {session_id}")
        
        result = await multi_agent_system.handle_conversation(
            user_input=request.user_input,
            session_id=session_id,
            history=request.history or []
        )

        # Optionally persist conversation metadata
        if request.user_id and conversation_store:
            try:
                title = _derive_title(request.history or [], request.user_input)
                now = datetime.now(timezone.utc).isoformat()
                conversation_store.upsert(
                    request.user_id,
                    {
                        "id": session_id,
                        "title": title,
                        # created_at will be preserved if exists
                        "created_at": None,
                        "updated_at": now,
                        "last_message_preview": (result.get("response") or "")[:200],
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to persist conversation metadata: {e}")

        return ConversationResponse(**result)
        
    except Exception as e:
        logger.error(f"Error during chat session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.")

# --- Conversation Metadata Endpoints ---
@app.get("/conversations", response_model=List[ConversationMeta], tags=["Conversations"])
async def list_conversations(user_id: str = Query(..., description="User ID to list conversations for")):
    if not conversation_store:
        raise HTTPException(status_code=503, detail="Conversation storage is not available.")
    try:
        items = conversation_store.list(user_id)
        # Convert to pydantic models
        parsed: List[ConversationMeta] = []
        for m in items:
            parsed.append(
                ConversationMeta(
                    id=m.get("id"),
                    title=m.get("title") or "New Search",
                    created_at=datetime.fromisoformat(m.get("created_at")) if m.get("created_at") else datetime.now(timezone.utc),
                    updated_at=datetime.fromisoformat(m.get("updated_at")) if m.get("updated_at") else datetime.now(timezone.utc),
                    last_message_preview=m.get("last_message_preview") or "",
                )
            )
        return parsed
    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")

@app.post("/conversations", response_model=ConversationMeta, tags=["Conversations"])
async def upsert_conversation(
    payload: ConversationMetaUpsert,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    if not conversation_store:
        raise HTTPException(status_code=503, detail="Conversation storage is not available.")
    try:
        now = datetime.now(timezone.utc)
        created_at = payload.created_at or now
        updated_at = payload.updated_at or now
        meta_dict = {
            "id": payload.id,
            "title": payload.title or "New Search",
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
            "last_message_preview": payload.last_message_preview or "",
        }
        stored = conversation_store.upsert(user_id, meta_dict)
        return ConversationMeta(
            id=stored.get("id"),
            title=stored.get("title") or "New Search",
            created_at=datetime.fromisoformat(stored.get("created_at")),
            updated_at=datetime.fromisoformat(stored.get("updated_at")),
            last_message_preview=stored.get("last_message_preview") or "",
        )
    except Exception as e:
        logger.error(f"Failed to upsert conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to upsert conversation")

@app.delete("/conversations/{conversation_id}", tags=["Conversations"])
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query(..., description="User ID to scope the conversation"),
):
    if not conversation_store:
        raise HTTPException(status_code=503, detail="Conversation storage is not available.")
    try:
        removed = conversation_store.delete(user_id, conversation_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "deleted", "id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete conversation")

# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)
