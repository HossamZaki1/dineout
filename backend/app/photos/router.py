"""Authenticated photo resolution with bounded caching and shared quotas."""
import asyncio
import os
import time
from collections import OrderedDict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse

from ..auth import current_user_id
from ..conversations.router import get_conversation_service
from ..conversations.service import ConversationService

router = APIRouter(prefix="/photos", tags=["Photos"])
CACHE_SECONDS = 300


class PhotoResolver:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.cache = OrderedDict()
        self.pending = {}
        self.semaphore = asyncio.Semaphore(8)

    async def resolve(self, photo_name, height, service):
        key = (photo_name, height)
        cached = self.cache.get(key)
        if cached and cached[0] > time.monotonic():
            self.cache.move_to_end(key)
            return cached[1]
        if key not in self.pending:
            task = asyncio.create_task(self._fetch(photo_name, height, service))
            self.pending[key] = task
            def finished(completed):
                self.pending.pop(key, None)
                # Consume failures even if every waiting HTTP request cancelled.
                if not completed.cancelled():
                    completed.exception()
            task.add_done_callback(finished)
        # Multiple requests for one image share one upstream request.
        return await asyncio.shield(self.pending[key])

    async def _fetch(self, photo_name, height, service):
        async with self.semaphore:
            await service.consume_quota("photos:upstream", 600)
            key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not key:
                raise HTTPException(503, "Photo service is not configured")
            try:
                response = await self.client.get(
                    f"https://places.googleapis.com/v1/{photo_name}/media",
                    params={"maxHeightPx": height, "skipHttpRedirect": "true"},
                    headers={"X-Goog-Api-Key": key},
                )
                response.raise_for_status()
                uri = response.json().get("photoUri")
                if not uri or httpx.URL(uri).scheme != "https":
                    raise HTTPException(502, "Invalid photo response")
            except httpx.HTTPStatusError as exc:
                code = 404 if exc.response.status_code in (400, 404) else 502
                raise HTTPException(code, "Photo could not be retrieved") from exc
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                raise HTTPException(502, "Photo service is temporarily unavailable") from exc
            self.cache[(photo_name, height)] = (time.monotonic() + CACHE_SECONDS, uri)
            self.cache.move_to_end((photo_name, height))
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return uri

    async def close(self):
        tasks = list(self.pending.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


@router.get("/{place_id}/{photo_id}")
async def get_photo(
    request: Request,
    place_id: str = Path(..., pattern=r"^[A-Za-z0-9_=-]+$", max_length=1024),
    photo_id: str = Path(..., pattern=r"^[A-Za-z0-9_=-]+$", max_length=4096),
    max_height: int = Query(400, ge=1, le=1600),
    redirect: bool = Query(True),
    user_id: str = Depends(current_user_id),
    service: ConversationService = Depends(get_conversation_service),
):
    await service.consume_quota(f"photos:user:{user_id}", 120)
    resolver = getattr(request.app.state, "photo_resolver", None)
    if resolver is None:
        raise HTTPException(503, "Photo service is unavailable")
    uri = await resolver.resolve(f"places/{place_id}/photos/{photo_id}", max_height, service)
    headers = {"Cache-Control": f"private, max-age={CACHE_SECONDS}"}
    # Browsers cannot attach an ID token to an <img>. The app first resolves
    # through its authenticated API client, then loads the credential-free URL.
    if not redirect:
        return {"url": uri, "expires_in": CACHE_SECONDS}
    return RedirectResponse(uri, status_code=307, headers=headers)
