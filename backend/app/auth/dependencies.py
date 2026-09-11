"""
Firebase ID token verification.

Every request that touches user data carries a bearer token issued by Firebase
Auth on the client. We verify its signature, issuer and audience here and take
the caller's identity from the token itself, so a caller cannot claim to be
someone else by naming them in the request.

Verification uses Google's public signing certificates, which need no
credentials of our own. That keeps local development working without
application default credentials while behaving identically on Cloud Run.
"""

import asyncio
import logging
import os
import threading
from typing import Optional

import cachecontrol
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)

# auto_error=False so a missing header produces our own message rather than
# FastAPI's generic one.
_bearer_scheme = HTTPBearer(auto_error=False, description="Firebase ID token")

_project_id: Optional[str] = None

# verify_firebase_token refetches Google's signing certificates on every call
# unless the session caches them, so each transport is wrapped in an HTTP cache.
# requests.Session is not thread safe and verification runs on a thread pool,
# so each worker thread gets its own.
_thread_local = threading.local()


def _transport() -> google_requests.Request:
    """Return this thread's cache-aware transport, building it on first use."""
    transport = getattr(_thread_local, "transport", None)
    if transport is None:
        session = cachecontrol.CacheControl(requests.Session())
        transport = google_requests.Request(session=session)
        _thread_local.transport = transport
    return transport


class AuthenticationError(Exception):
    """Raised when authentication cannot be configured."""


def initialize_firebase() -> None:
    """
    Resolve and cache the Firebase project ID at startup.

    The project ID is what a token's audience and issuer are checked against,
    so getting it wrong would mean accepting tokens minted for a different
    project.
    """
    global _project_id
    _project_id = (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
    )
    if not _project_id:
        raise AuthenticationError(
            "FIREBASE_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) must be set so ID "
            "tokens can be checked against the right project."
        )
    logger.info(f"Authentication configured for Firebase project {_project_id}")


def _verify(token: str) -> dict:
    """Verify a token synchronously. Raises ValueError if it is not valid."""
    claims = google_id_token.verify_firebase_token(
        token, _transport(), audience=_project_id
    )
    # verify_firebase_token returns None rather than raising for some inputs.
    if not claims:
        raise ValueError("Token could not be verified")
    expected_issuer = f"https://securetoken.google.com/{_project_id}"
    if claims.get("iss") != expected_issuer:
        raise ValueError(f"Unexpected issuer: {claims.get('iss')}")
    return claims


async def current_user_id(
    token: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> str:
    """
    Resolve the caller's Firebase user ID from the Authorization header.

    Returns the verified subject of the token. Raises 401 for anything else,
    including a missing header, so routes that depend on this can assume the
    identity is real.
    """
    if token is None or not token.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _project_id:
        # Fail closed: without a project to check against we cannot trust
        # any identity.
        logger.error("Auth requested before the project ID was configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not available",
        )

    try:
        # Certificate fetches are blocking, so keep them off the event loop.
        claims = await asyncio.to_thread(_verify, token.credentials)
    except ValueError as e:
        message = str(e)
        if "expired" in message.lower():
            detail = "Token has expired. Sign in again."
        else:
            detail = "Invalid authentication token"
            logger.warning(f"Rejected an ID token: {message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except google_auth_exceptions.TransportError as e:
        # We could not reach Google to fetch signing certificates. That is our
        # outage, not a bad token, and a 401 would make the client sign out.
        logger.error(f"Could not fetch signing certificates: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is temporarily unavailable. Try again.",
        )
    except Exception as e:
        logger.error(f"Token verification failed unexpectedly: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    uid = claims.get("user_id") or claims.get("sub")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token carries no user identity",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return uid
