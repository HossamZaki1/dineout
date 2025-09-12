from typing import Dict, List, Any
from .base_agent import BaseAgent
import httpx
import os
from datetime import datetime, time, timedelta

class SearchAgent(BaseAgent):
    """
    Agent responsible for searching for restaurants using the Google Places API.
    """
    
    def __init__(self):
        super().__init__("Search", temperature=0.3)
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.places_api_url = "https://places.googleapis.com/v1/places:searchText"

    async def _custom_initialize(self):
        if not self.api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")

    async def _geocode_location(self, location: str) -> Dict[str, float]:
        """
        Converts a location string to latitude and longitude using Google Geocoding API.
        """
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": location,
            "key": self.api_key
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(geocode_url, params=params)
                response.raise_for_status()
                results = response.json()
                if results['status'] == 'OK':
                    return results['results'][0]['geometry']['location']
                else:
                    print(f"Geocoding failed: {results.get('status')}")
                    return None
            except httpx.HTTPStatusError as e:
                print(f"Error geocoding location: {e.response.text}")
                return None
            except Exception as e:
                print(f"An unexpected error occurred during geocoding: {e}")
                return None

    async def find_all_restaurants(self, location: str, cuisine: str, radius: float = 5000.0) -> List[Dict[str, Any]]:
        """
        Searches for all restaurants (both open and closed) using the Google Places API.
        """
        # Geocode the location string to get coordinates
        coordinates = await self._geocode_location(location)
        if not coordinates:
            print("Could not geocode location, aborting search.")
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.photos,places.regularOpeningHours,places.currentOpeningHours,places.googleMapsUri,places.reviews,places.priceLevel,places.types"
        }
        
        data = {
            "textQuery": f"{cuisine} restaurants near {location}",
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": coordinates['lat'],
                        "longitude": coordinates['lng']
                    },
                    "radius": radius
                }
            },
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.places_api_url, json=data, headers=headers)
                response.raise_for_status()
                results = response.json()
                
                # Format all restaurants and sort them
                all_restaurants = []
                for place in results.get('places', []):
                    # Debug logging to see what we're getting from the API
                    print(f"🔍 Place data keys: {list(place.keys())}")
                    print(f"📍 Place ID: {place.get('id')}")
                    print(f"🔗 Google Maps URI: {place.get('googleMapsUri')}")
                    
                    # Determine if restaurant is currently open
                    current_opening_hours = place.get('currentOpeningHours', {})
                    is_open_now = current_opening_hours.get('openNow', False)
                    
                    # Get regular opening hours for sorting
                    regular_opening_hours = place.get('regularOpeningHours', {})
                    opening_hours_periods = regular_opening_hours.get('periods', [])
                    
                    # Calculate next opening time for closed restaurants
                    next_opening_time = None
                    next_opening_display = None
                    if not is_open_now:
                        next_opening_time, next_opening_display = self._calculate_next_opening_time(opening_hours_periods)
                        # Handle infinity values that can't be JSON serialized
                        if next_opening_time == float('inf'):
                            next_opening_time = None
                    
                    restaurant_data = {
                        "name": place.get('displayName', {}).get('text'),
                        "address": place.get('formattedAddress'),
                        "rating": place.get('rating'),
                        "is_open_now": is_open_now,
                        "photos": place.get('photos', []),
                        "place_id": place.get('id'),
                        "google_maps_uri": place.get('googleMapsUri'),
                        "opening_hours_periods": opening_hours_periods,
                        "current_opening_hours": current_opening_hours,
                        "regular_opening_hours": regular_opening_hours,
                        "next_opening_time": next_opening_time,
                        "next_opening_display": next_opening_display,
                        "reviews": place.get('reviews', []),
                        "price_level": place.get('priceLevel'),
                        "types": place.get('types', [])
                    }
                    all_restaurants.append(restaurant_data)
                
                # Sort restaurants: open first, then closed by opening time
                sorted_restaurants = self._sort_restaurants_by_status_and_opening_time(all_restaurants)
                return sorted_restaurants

            except httpx.HTTPStatusError as e:
                print(f"Error searching for restaurants: {e.response.text}")
                return []
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return []

    def _calculate_next_opening_time(self, opening_hours_periods: List[Dict[str, Any]]) -> tuple[float, str]:
        """
        Calculate the next opening time for a closed restaurant and return user-friendly display text.
        
        Returns:
            tuple: (minutes_until_opening, display_text)
        """
        if not opening_hours_periods:
            return float('inf'), "Hours not available"
        
        current_time = datetime.now()
        current_day = current_time.weekday()  # Monday = 0, Sunday = 6
        current_time_minutes = current_time.hour * 60 + current_time.minute
        
        # Google Places API uses Sunday = 0, Monday = 1, ..., Saturday = 6
        google_day_mapping = [6, 0, 1, 2, 3, 4, 5]  # Convert Python weekday to Google day
        current_google_day = google_day_mapping[current_day]
        
        # Find the next opening time
        min_wait_minutes = float('inf')
        next_opening_datetime = None
        
        # Check today first
        for period in opening_hours_periods:
            open_time = period.get('open', {})
            if not open_time:
                continue
            
            open_day = open_time.get('day', 0)
            open_hour = open_time.get('hour', 0)
            open_minute = open_time.get('minute', 0)
            open_time_minutes = open_hour * 60 + open_minute
            
            # Calculate days until this opening time
            days_diff = (open_day - current_google_day) % 7
            
            # If it's today and the opening time hasn't passed yet
            if days_diff == 0 and open_time_minutes > current_time_minutes:
                wait_minutes = open_time_minutes - current_time_minutes
                if wait_minutes < min_wait_minutes:
                    min_wait_minutes = wait_minutes
                    next_opening_datetime = current_time.replace(
                        hour=open_hour, 
                        minute=open_minute, 
                        second=0, 
                        microsecond=0
                    )
            # If it's a future day this week
            elif days_diff > 0:
                wait_minutes = days_diff * 24 * 60 + open_time_minutes - current_time_minutes
                if wait_minutes < min_wait_minutes:
                    min_wait_minutes = wait_minutes
                    target_date = current_time + timedelta(days=days_diff)
                    next_opening_datetime = target_date.replace(
                        hour=open_hour, 
                        minute=open_minute, 
                        second=0, 
                        microsecond=0
                    )
        
        # If no opening time found for this week, check next week
        if min_wait_minutes == float('inf'):
            for period in opening_hours_periods:
                open_time = period.get('open', {})
                if not open_time:
                    continue
                
                open_hour = open_time.get('hour', 0)
                open_minute = open_time.get('minute', 0)
                wait_minutes = 7 * 24 * 60 + open_hour * 60 + open_minute - current_time_minutes
                
                if wait_minutes < min_wait_minutes:
                    min_wait_minutes = wait_minutes
                    target_date = current_time + timedelta(days=7)
                    next_opening_datetime = target_date.replace(
                        hour=open_hour, 
                        minute=open_minute, 
                        second=0, 
                        microsecond=0
                    )
                break  # Take the first opening time next week
        
        # Generate user-friendly display text
        if min_wait_minutes == float('inf') or next_opening_datetime is None:
            return float('inf'), "Hours not available"
        
        display_text = self._format_opening_time_display(next_opening_datetime, min_wait_minutes)
        return min_wait_minutes, display_text

    def _format_opening_time_display(self, opening_datetime: datetime, wait_minutes: float) -> str:
        """Format the opening time for user display."""
        current_time = datetime.now()
        
        # If opening today
        if opening_datetime.date() == current_time.date():
            if wait_minutes < 60:
                return f"Opens in {int(wait_minutes)} min"
            elif wait_minutes < 120:
                return f"Opens in 1 hour"
            else:
                hours = int(wait_minutes / 60)
                return f"Opens in {hours} hours"
        
        # If opening tomorrow
        elif opening_datetime.date() == (current_time + timedelta(days=1)).date():
            time_str = opening_datetime.strftime("%-I:%M %p")
            return f"Opens tomorrow at {time_str}"
        
        # If opening this week
        elif wait_minutes < 7 * 24 * 60:
            day_name = opening_datetime.strftime("%A")
            time_str = opening_datetime.strftime("%-I:%M %p")
            return f"Opens {day_name} at {time_str}"
        
        # If opening next week or later
        else:
            date_str = opening_datetime.strftime("%m/%d")
            time_str = opening_datetime.strftime("%-I:%M %p")
            return f"Opens {date_str} at {time_str}"

    def _sort_restaurants_by_status_and_opening_time(self, restaurants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort restaurants with open restaurants first, then closed restaurants by opening time.
        """
        def get_next_opening_time(restaurant):
            """Get the next opening time for a closed restaurant."""
            # Use the pre-calculated next_opening_time if available
            next_opening_time = restaurant.get('next_opening_time')
            if next_opening_time is not None:
                # Handle infinity values for sorting
                if next_opening_time == float('inf'):
                    return float('inf')
                return next_opening_time
            
            # Fallback to the old calculation method if needed
            opening_hours_periods = restaurant.get('opening_hours_periods', [])
            if not opening_hours_periods:
                return float('inf')  # No opening hours data, sort to end
            
            current_time = datetime.now()
            current_day = current_time.weekday()  # Monday = 0, Sunday = 6
            current_time_minutes = current_time.hour * 60 + current_time.minute
            
            # Google Places API uses Sunday = 0, Monday = 1, ..., Saturday = 6
            google_day_mapping = [6, 0, 1, 2, 3, 4, 5]  # Convert Python weekday to Google day
            current_google_day = google_day_mapping[current_day]
            
            # Find the next opening time
            for period in opening_hours_periods:
                open_time = period.get('open', {})
                if not open_time:
                    continue
                
                open_day = open_time.get('day', 0)
                open_hour = open_time.get('hour', 0)
                open_minute = open_time.get('minute', 0)
                open_time_minutes = open_hour * 60 + open_minute
                
                # Calculate days until this opening time
                days_diff = (open_day - current_google_day) % 7
                
                # If it's today and the opening time hasn't passed yet
                if days_diff == 0 and open_time_minutes > current_time_minutes:
                    return open_time_minutes
                # If it's a future day
                elif days_diff > 0:
                    return days_diff * 24 * 60 + open_time_minutes
            
            # If no opening time found for this week, check next week
            for period in opening_hours_periods:
                open_time = period.get('open', {})
                if not open_time:
                    continue
                
                open_hour = open_time.get('hour', 0)
                open_minute = open_time.get('minute', 0)
                open_time_minutes = open_hour * 60 + open_minute
                
                return 7 * 24 * 60 + open_time_minutes  # Next week
            
            return float('inf')  # No opening hours found
        
        # Separate open and closed restaurants
        open_restaurants = [r for r in restaurants if r.get('is_open_now', False)]
        closed_restaurants = [r for r in restaurants if not r.get('is_open_now', False)]
        
        # Sort closed restaurants by next opening time
        closed_restaurants.sort(key=get_next_opening_time)
        
        # Combine: open restaurants first, then closed restaurants sorted by opening time
        return open_restaurants + closed_restaurants

    async def find_all_restaurants_with_radius_extension(self, location: str, cuisine: str, min_results: int = 2) -> List[Dict[str, Any]]:
        """
        Searches for all restaurants with automatic radius extension if insufficient results are found.
        
        Args:
            location: The location to search in
            cuisine: The cuisine type to search for
            min_results: Minimum number of restaurants required (default: 2)
        
        Returns:
            List of restaurant dictionaries sorted with open restaurants first, then closed by opening time
        """
        # Define radius progression: start with 5km, then expand to 10km, 20km, 50km
        radius_progression = [5000.0, 20000.0, 50000.0]
        
        for i, radius in enumerate(radius_progression):
            print(f"🔍 Searching with radius: {radius/1000:.1f}km")
            restaurants = await self.find_all_restaurants(location, cuisine, radius)
            
            print(f"📊 Found {len(restaurants)} restaurants with {radius/1000:.1f}km radius")
            
            # If we have enough restaurants or this is the last radius, return results
            if len(restaurants) >= min_results or i == len(radius_progression) - 1:
                if len(restaurants) < min_results and i > 0:
                    print(f"⚠️ Extended search radius to {radius/1000:.1f}km but still found only {len(restaurants)} restaurants")
                elif i > 0:
                    print(f"✅ Extended search radius to {radius/1000:.1f}km and found {len(restaurants)} restaurants")
                return restaurants
                
        return []

