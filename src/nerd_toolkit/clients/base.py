import asyncio
import logging
from typing import Any

import httpx

from nerd_toolkit.config import settings

logger = logging.getLogger(__name__)


class BaseClient:
    """Base HTTP client with exponential backoff retry logic."""

    def __init__(self, base_url: str, headers: dict[str, str] | None = None) -> None:
        self._base_url = base_url
        self._headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseClient":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=httpx.Timeout(settings.request_timeout),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client

    async def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Execute an HTTP request with exponential backoff on 5xx errors."""
        last_exception: Exception | None = None

        for attempt in range(settings.retry_max_attempts):
            try:
                response = await self.client.request(method, url, **kwargs)

                if response.status_code < 500:
                    response.raise_for_status()
                    return response

                last_exception = httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response,
                )
                logger.warning(
                    "Request failed (attempt %d/%d): %s",
                    attempt + 1,
                    settings.retry_max_attempts,
                    response.status_code,
                )

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "Request timed out (attempt %d/%d)",
                    attempt + 1,
                    settings.retry_max_attempts,
                )

            if attempt < settings.retry_max_attempts - 1:
                delay = min(
                    settings.retry_base_delay * (2**attempt),
                    settings.retry_max_delay,
                )
                logger.info("Retrying in %.1fs...", delay)
                await asyncio.sleep(delay)

        raise last_exception or RuntimeError("All retries exhausted")
