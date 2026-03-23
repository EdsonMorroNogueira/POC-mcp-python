import logging
from typing import Any

from nerd_toolkit.clients.base import BaseClient
from nerd_toolkit.config import settings

logger = logging.getLogger(__name__)


class DndClient(BaseClient):
    """HTTP client for the D&D 5e SRD API."""

    def __init__(self) -> None:
        super().__init__(base_url=settings.dnd_base_url)
        self._cache: dict[str, Any] = {}

    async def _cached_get(self, cache_key: str, url: str) -> Any:
        """GET with in-memory caching for static data."""
        if cache_key in self._cache:
            logger.debug("Cache hit: %s", cache_key)
            return self._cache[cache_key]

        response = await self._request_with_retry("GET", url)
        data = response.json()
        self._cache[cache_key] = data
        return data

    async def list_classes(self) -> list[dict[str, Any]]:
        """List all available D&D classes."""
        logger.info("Listing D&D classes")
        data = await self._cached_get("classes", "/classes")
        return data.get("results", [])

    async def get_class_info(self, class_name: str) -> dict[str, Any]:
        """Get detailed info about a specific class."""
        index = class_name.lower()
        logger.info("Fetching class info: %s", index)
        response = await self._request_with_retry("GET", f"/classes/{index}")
        return response.json()

    async def get_spells_by_class(self, class_name: str) -> list[dict[str, Any]]:
        """Get all spells available to a class."""
        index = class_name.lower()
        cache_key = f"spells_by_class_{index}"
        logger.info("Fetching spells for class: %s", index)
        data = await self._cached_get(cache_key, f"/classes/{index}/spells")
        return data.get("results", [])

    async def get_spell_detail(self, spell_index: str) -> dict[str, Any]:
        """Get detailed info about a specific spell."""
        logger.info("Fetching spell detail: %s", spell_index)
        response = await self._request_with_retry("GET", f"/spells/{spell_index}")
        return response.json()

    async def search_monsters(
        self,
        challenge_rating: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search monsters, optionally filtered by challenge rating."""
        params: dict[str, Any] = {}
        if challenge_rating is not None:
            params["challenge_rating"] = challenge_rating

        logger.info("Searching monsters with params: %s", params)
        response = await self._request_with_retry("GET", "/monsters", params=params)
        data = response.json()
        return data.get("results", [])

    async def get_monster_detail(self, monster_index: str) -> dict[str, Any]:
        """Get detailed info about a specific monster."""
        logger.info("Fetching monster detail: %s", monster_index)
        response = await self._request_with_retry("GET", f"/monsters/{monster_index}")
        return response.json()
