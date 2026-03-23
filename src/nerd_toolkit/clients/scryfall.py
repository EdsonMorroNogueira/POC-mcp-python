import asyncio
import logging
from typing import Any

from nerd_toolkit.clients.base import BaseClient
from nerd_toolkit.config import settings

logger = logging.getLogger(__name__)


class ScryfallClient(BaseClient):
    """HTTP client for the Scryfall Magic: The Gathering API."""

    def __init__(self) -> None:
        super().__init__(
            base_url=settings.scryfall_base_url,
            headers={
                "User-Agent": "NerdToolkitMCP/1.0",
                "Accept": "application/json",
            },
        )
        self._last_request_time: float = 0

    async def _rate_limited_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Make a request respecting Scryfall's rate limit (100ms between requests)."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        delay = settings.scryfall_rate_limit_ms / 1000

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)

        self._last_request_time = asyncio.get_event_loop().time()
        return await self._request_with_retry(method, url, **kwargs)

    def _build_query(
        self,
        query: str,
        color: str | None = None,
        card_type: str | None = None,
        mtg_format: str | None = None,
    ) -> str:
        """Build a Scryfall search query string with optional filters."""
        parts = [query]
        if color:
            parts.append(f"c:{color}")
        if card_type:
            parts.append(f"t:{card_type}")
        if mtg_format:
            parts.append(f"f:{mtg_format}")
        return " ".join(parts)

    async def search_cards(
        self,
        query: str,
        color: str | None = None,
        card_type: str | None = None,
        mtg_format: str | None = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search for cards using Scryfall search syntax."""
        full_query = self._build_query(query, color, card_type, mtg_format)
        logger.info("Searching Scryfall: %s", full_query)

        response = await self._rate_limited_request(
            "GET", "/cards/search", params={"q": full_query, "page": page}
        )
        data = response.json()
        return data.get("data", [])

    async def random_card(
        self,
        color: str | None = None,
        card_type: str | None = None,
    ) -> dict[str, Any]:
        """Get a random card with optional filters."""
        params: dict[str, str] = {}
        query = self._build_query("", color, card_type)
        if query.strip():
            params["q"] = query.strip()

        logger.info("Fetching random card from Scryfall")
        response = await self._rate_limited_request("GET", "/cards/random", params=params)
        return response.json()
