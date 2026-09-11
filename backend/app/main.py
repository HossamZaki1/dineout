"""Application setup. Dependencies are created and closed with the app lifespan."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .agents.multi_agent_system import MultiAgentSystem
from .auth import initialize_firebase
from .conversations.router import router as conversation_router
from .conversations.service import (ConversationService, ConversationServiceError,
                                    InvalidRequestError, StorageUnavailableError,
                                    UpstreamUnavailableError)
from .photos.router import PhotoResolver, router as photo_router
from .storage.base import ConversationNotFoundError, RateLimitError
from .storage.factory import create_store

logger = logging.getLogger(__name__)


def create_app(storage=None, agent_system=None) -> FastAPI:
    load_dotenv()
    # Geocoding uses a query-string key; do not log outbound URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    @asynccontextmanager
    async def lifespan(app):
        store = storage if storage is not None else await asyncio.to_thread(create_store)
        agents = None
        resolver = None
        try:
            initialize_firebase()
            await asyncio.to_thread(store.check_health)
            async with httpx.AsyncClient(timeout=httpx.Timeout(10, connect=5)) as client:
                agents = agent_system if agent_system is not None else MultiAgentSystem(client=client)
                resolver = PhotoResolver(client)
                app.state.photo_resolver = resolver
                try:
                    await agents.initialize()
                    app.state.conversation_service = ConversationService(store, agents)
                    yield
                finally:
                    await resolver.close()
                    app.state.conversation_service = None
        finally:
            await asyncio.to_thread(store.close)

    app = FastAPI(title="Restaurant Finder AI", version="3.1.0", lifespan=lifespan)
    app.state.conversation_service = None
    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    async def service_error(request, exc):
        status, detail = 500, "Could not process the request"
        headers = None
        if isinstance(exc, ConversationNotFoundError):
            status, detail = 404, "Conversation not found"
        elif isinstance(exc, RateLimitError):
            status, detail = 429, "Too many requests. Please try again shortly."
            headers = {"Retry-After": "60"}
        elif isinstance(exc, InvalidRequestError):
            status, detail = 400, str(exc)
        elif isinstance(exc, StorageUnavailableError):
            status, detail = 503, str(exc)
        elif isinstance(exc, UpstreamUnavailableError):
            status, detail = 502, str(exc)
        return JSONResponse({"detail": detail}, status_code=status, headers=headers)

    for exception in (ConversationServiceError, ConversationNotFoundError, RateLimitError):
        app.add_exception_handler(exception, service_error)

    @app.get("/")
    async def root():
        return {"message": "Welcome to the Restaurant Finder AI API"}

    @app.get("/health")
    async def health():
        service = app.state.conversation_service
        if service is None:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        await service._call(service.storage.check_health)
        return {"status": "healthy", "storage": service.storage.kind,
                "agents": service.multi_agent_system.get_agent_status()}

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    app.include_router(conversation_router)
    app.include_router(photo_router)
    return app


app = create_app()
