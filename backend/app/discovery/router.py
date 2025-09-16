from fastapi import APIRouter, Query
from typing import Optional
import logging

from ..models.restaurant_models import LocationRequest, DiscoveryResponse, RestaurantInfo
from ..services.discovery_service import DiscoveryService

logger = logging.getLogger(__name__)

# Create router
discovery_router = APIRouter(prefix="/api/discovery", tags=["Discovery"])

# Service instance
_service: Optional[DiscoveryService] = None

def get_service() -> DiscoveryService:
    """Get discovery service instance"""
    global _service
    if _service is None:
        _service = DiscoveryService()
    return _service

@discovery_router.get("/restaurants", response_model=DiscoveryResponse)
async def discover_restaurants(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius: int = Query(5000, description="Search radius in meters"),
    limit: int = Query(10, description="Max restaurants to return")
):
    """Find restaurants near location"""
    location = LocationRequest(latitude=lat, longitude=lng, radius=radius)
    service = get_service()
    return await service.discover_restaurants(location, limit)

@discovery_router.get("/restaurants/{place_id}", response_model=RestaurantInfo)
async def get_restaurant(place_id: str):
    """Get restaurant details"""
    service = get_service()
    restaurant = await service.get_restaurant(place_id)
    if not restaurant:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

@discovery_router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "discovery"}
