from typing import Dict, List, Optional


class PhotoAgent:
    """
    Agent responsible for turning Places photo references into links the client
    can load.

    The reference itself is not an image URL, and resolving one requires the
    Maps API key. Rather than embed that key in a URL handed to every client,
    this returns a path on our own API which performs the lookup server-side.
    """

    def __init__(self):
        self.is_initialized = False

    async def initialize(self):
        self.is_initialized = True

    async def get_primary_photo_url(self, photos_data: List[Dict]) -> Optional[str]:
        """
        Build a path to the primary (first) photo, relative to this API.

        Places returns references shaped 'places/<place_id>/photos/<photo_id>'.
        Anything else is skipped rather than guessed at.
        """
        if not photos_data:
            return None

        photo_name = photos_data[0].get('name')
        if not photo_name:
            return None

        parts = photo_name.split('/')
        if len(parts) != 4 or parts[0] != 'places' or parts[2] != 'photos':
            return None

        place_id, photo_id = parts[1], parts[3]
        return f"/photos/{place_id}/{photo_id}"
