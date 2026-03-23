# Nerd Toolkit MCP Server — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MCP server that exposes MTG (Scryfall) and D&D 5e tools, resources, and prompts for LLMs.

**Architecture:** Modular by domain — `mtg/` and `dnd/` modules with isolated HTTP clients, registered into a central FastMCP server. Lifespan pattern manages client lifecycle. Supports stdio and streamable-http transports.

**Tech Stack:** Python 3.10+, uv, mcp[cli] (FastMCP), httpx, pydantic, pydantic-settings, pytest, respx, ruff, mypy

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `src/nerd_toolkit/__init__.py`
- Create: `src/nerd_toolkit/config.py`
- Create: `tests/__init__.py`

**Step 1: Initialize project with uv**

```bash
cd /home/edson/Documents/GitHub/pessoal/POC-mcp-python
uv init --lib --name nerd-toolkit
```

If `uv init` complains the directory already exists, manually create `pyproject.toml` instead.

**Step 2: Replace pyproject.toml with full config**

```toml
[project]
name = "nerd-toolkit"
version = "0.1.0"
description = "MCP server for Magic: The Gathering and D&D 5e — a nerd toolkit for LLMs"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]",
    "httpx",
    "pydantic-settings",
]

[project.scripts]
nerd-toolkit = "nerd_toolkit.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "SIM", "TCH"]

[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio",
    "respx",
    "ruff",
    "mypy",
]
```

**Step 3: Create Makefile**

```makefile
.PHONY: dev test lint typecheck format install

install:
	uv sync --all-groups

dev:
	uv run python -m nerd_toolkit.server

dev-http:
	uv run python -m nerd_toolkit.server streamable-http

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

inspect:
	npx -y @modelcontextprotocol/inspector
```

**Step 4: Create config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_prefix": "NERD_TOOLKIT_"}

    scryfall_base_url: str = "https://api.scryfall.com"
    scryfall_rate_limit_ms: int = 100
    dnd_base_url: str = "https://www.dnd5eapi.co/api"
    request_timeout: int = 10
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 10.0
    log_level: str = "INFO"


settings = Settings()
```

**Step 5: Create __init__.py files**

`src/nerd_toolkit/__init__.py`:
```python
"""Nerd Toolkit — MCP server for MTG and D&D 5e."""
```

`tests/__init__.py`: empty file.

**Step 6: Install dependencies**

```bash
uv sync --all-groups
```

**Step 7: Verify lint and typecheck pass**

```bash
make lint
make typecheck
```

**Step 8: Commit**

```bash
git add pyproject.toml Makefile src/ tests/__init__.py uv.lock
git commit -m "feat: project scaffolding with uv, config, Makefile, and dev tooling"
```

---

## Task 2: HTTP Client Base + ScyrfallClient

**Files:**
- Create: `src/nerd_toolkit/clients/__init__.py`
- Create: `src/nerd_toolkit/clients/base.py`
- Create: `src/nerd_toolkit/clients/scryfall.py`
- Create: `tests/test_scryfall_client.py`

**Step 1: Write the failing test for ScyrfallClient**

`tests/test_scryfall_client.py`:
```python
import httpx
import pytest
import respx

from nerd_toolkit.clients.scryfall import ScyrfallClient


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_returns_card_list() -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": "list",
                "total_cards": 1,
                "has_more": False,
                "data": [
                    {
                        "name": "Lightning Bolt",
                        "mana_cost": "{R}",
                        "type_line": "Instant",
                        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                        "colors": ["R"],
                        "set_name": "Alpha",
                        "rarity": "common",
                        "image_uris": {"normal": "https://example.com/bolt.jpg"},
                    }
                ],
            },
        )
    )

    async with ScyrfallClient() as client:
        result = await client.search_cards("lightning bolt")

    assert len(result) == 1
    assert result[0]["name"] == "Lightning Bolt"


@respx.mock
@pytest.mark.asyncio
async def test_random_card_returns_single_card() -> None:
    respx.get("https://api.scryfall.com/cards/random").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Black Lotus",
                "mana_cost": "{0}",
                "type_line": "Artifact",
                "oracle_text": "Sacrifice Black Lotus: Add three mana of any one color.",
                "colors": [],
                "set_name": "Alpha",
                "rarity": "rare",
                "image_uris": {"normal": "https://example.com/lotus.jpg"},
            },
        )
    )

    async with ScyrfallClient() as client:
        result = await client.random_card()

    assert result["name"] == "Black Lotus"


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_with_filters_builds_query() -> None:
    route = respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={"object": "list", "total_cards": 0, "has_more": False, "data": []},
        )
    )

    async with ScyrfallClient() as client:
        await client.search_cards("bolt", color="red", card_type="instant", mtg_format="modern")

    assert "c:red" in str(route.calls[0].request.url)
    assert "t:instant" in str(route.calls[0].request.url)
    assert "f:modern" in str(route.calls[0].request.url)


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_retries_on_server_error() -> None:
    route = respx.get("https://api.scryfall.com/cards/search")
    route.side_effect = [
        httpx.Response(500, json={"details": "server error"}),
        httpx.Response(500, json={"details": "server error"}),
        httpx.Response(
            200,
            json={"object": "list", "total_cards": 0, "has_more": False, "data": []},
        ),
    ]

    async with ScyrfallClient() as client:
        result = await client.search_cards("test")

    assert result == []
    assert route.call_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_raises_after_max_retries() -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=httpx.Response(500, json={"details": "server error"})
    )

    async with ScyrfallClient() as client:
        with pytest.raises(Exception, match="500"):
            await client.search_cards("test")
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_scryfall_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'nerd_toolkit.clients'`

**Step 3: Create the base client with exponential backoff**

`src/nerd_toolkit/clients/__init__.py`: empty file.

`src/nerd_toolkit/clients/base.py`:
```python
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
```

**Step 4: Implement ScyrfallClient**

`src/nerd_toolkit/clients/scryfall.py`:
```python
import asyncio
import logging
from typing import Any

from nerd_toolkit.clients.base import BaseClient
from nerd_toolkit.config import settings

logger = logging.getLogger(__name__)


class ScyrfallClient(BaseClient):
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
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_scryfall_client.py -v
```

Expected: all 5 tests PASS.

**Step 6: Commit**

```bash
git add src/nerd_toolkit/clients/ tests/test_scryfall_client.py
git commit -m "feat: add BaseClient with exponential backoff and ScyrfallClient"
```

---

## Task 3: DndClient

**Files:**
- Create: `src/nerd_toolkit/clients/dnd.py`
- Create: `tests/test_dnd_client.py`

**Step 1: Write the failing tests**

`tests/test_dnd_client.py`:
```python
import httpx
import pytest
import respx

from nerd_toolkit.clients.dnd import DndClient

DND_BASE = "https://www.dnd5eapi.co/api"


@respx.mock
@pytest.mark.asyncio
async def test_list_classes_returns_class_names() -> None:
    respx.get(f"{DND_BASE}/classes").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"index": "wizard", "name": "Wizard", "url": "/api/classes/wizard"},
                    {"index": "fighter", "name": "Fighter", "url": "/api/classes/fighter"},
                ],
            },
        )
    )

    async with DndClient() as client:
        result = await client.list_classes()

    assert len(result) == 2
    assert result[0]["name"] == "Wizard"


@respx.mock
@pytest.mark.asyncio
async def test_get_class_info_returns_details() -> None:
    respx.get(f"{DND_BASE}/classes/wizard").mock(
        return_value=httpx.Response(
            200,
            json={
                "index": "wizard",
                "name": "Wizard",
                "hit_die": 6,
                "proficiencies": [{"name": "Daggers"}],
                "spellcasting": {"level": 1},
            },
        )
    )

    async with DndClient() as client:
        result = await client.get_class_info("wizard")

    assert result["name"] == "Wizard"
    assert result["hit_die"] == 6


@respx.mock
@pytest.mark.asyncio
async def test_get_spells_by_class_returns_spell_list() -> None:
    respx.get(f"{DND_BASE}/classes/wizard/spells").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"index": "fireball", "name": "Fireball", "level": 3, "url": "/api/spells/fireball"},
                    {"index": "magic-missile", "name": "Magic Missile", "level": 1, "url": "/api/spells/magic-missile"},
                ],
            },
        )
    )

    async with DndClient() as client:
        result = await client.get_spells_by_class("wizard")

    assert len(result) == 2
    assert result[0]["name"] == "Fireball"


@respx.mock
@pytest.mark.asyncio
async def test_get_spell_detail_returns_full_info() -> None:
    respx.get(f"{DND_BASE}/spells/fireball").mock(
        return_value=httpx.Response(
            200,
            json={
                "index": "fireball",
                "name": "Fireball",
                "level": 3,
                "school": {"name": "Evocation"},
                "classes": [{"name": "Wizard"}, {"name": "Sorcerer"}],
                "desc": ["A bright streak flashes..."],
                "damage": {"damage_type": {"name": "Fire"}, "damage_at_slot_level": {"3": "8d6"}},
                "range": "150 feet",
                "components": ["V", "S", "M"],
                "casting_time": "1 action",
                "duration": "Instantaneous",
            },
        )
    )

    async with DndClient() as client:
        result = await client.get_spell_detail("fireball")

    assert result["name"] == "Fireball"
    assert result["level"] == 3
    assert result["school"]["name"] == "Evocation"


@respx.mock
@pytest.mark.asyncio
async def test_search_monsters_by_challenge_rating() -> None:
    respx.get(f"{DND_BASE}/monsters").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "results": [
                    {"index": "goblin", "name": "Goblin", "url": "/api/monsters/goblin"},
                ],
            },
        )
    )

    async with DndClient() as client:
        result = await client.search_monsters(challenge_rating=0.25)

    assert len(result) == 1
    assert result[0]["name"] == "Goblin"


@respx.mock
@pytest.mark.asyncio
async def test_get_monster_detail_returns_full_info() -> None:
    respx.get(f"{DND_BASE}/monsters/goblin").mock(
        return_value=httpx.Response(
            200,
            json={
                "index": "goblin",
                "name": "Goblin",
                "challenge_rating": 0.25,
                "hit_points": 7,
                "armor_class": [{"value": 15}],
                "actions": [{"name": "Scimitar", "desc": "Melee Weapon Attack..."}],
                "type": "humanoid",
                "size": "Small",
            },
        )
    )

    async with DndClient() as client:
        result = await client.get_monster_detail("goblin")

    assert result["name"] == "Goblin"
    assert result["challenge_rating"] == 0.25


@respx.mock
@pytest.mark.asyncio
async def test_list_classes_uses_cache_on_second_call() -> None:
    route = respx.get(f"{DND_BASE}/classes").mock(
        return_value=httpx.Response(
            200,
            json={"count": 1, "results": [{"index": "wizard", "name": "Wizard", "url": "/api/classes/wizard"}]},
        )
    )

    async with DndClient() as client:
        await client.list_classes()
        await client.list_classes()

    assert route.call_count == 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_dnd_client.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement DndClient**

`src/nerd_toolkit/clients/dnd.py`:
```python
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
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_dnd_client.py -v
```

Expected: all 7 tests PASS.

**Step 5: Commit**

```bash
git add src/nerd_toolkit/clients/dnd.py tests/test_dnd_client.py
git commit -m "feat: add DndClient with caching and monster/spell/class endpoints"
```

---

## Task 4: FastMCP Server + Lifespan

**Files:**
- Create: `src/nerd_toolkit/server.py`
- Create: `src/nerd_toolkit/__main__.py`

**Step 1: Create the server with lifespan**

`src/nerd_toolkit/server.py`:
```python
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.clients.scryfall import ScyrfallClient


@dataclass
class AppContext:
    """Application context holding initialized HTTP clients."""

    scryfall: ScyrfallClient
    dnd: DndClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage HTTP client lifecycle — create on startup, close on shutdown."""
    scryfall = ScyrfallClient()
    dnd = DndClient()

    async with scryfall, dnd:
        yield AppContext(scryfall=scryfall, dnd=dnd)


mcp = FastMCP("Nerd Toolkit", lifespan=app_lifespan)

# Import tools, resources, and prompts so they register with the server
import nerd_toolkit.mtg.tools  # noqa: F401, E402
import nerd_toolkit.mtg.resources  # noqa: F401, E402
import nerd_toolkit.mtg.prompts  # noqa: F401, E402
import nerd_toolkit.dnd.tools  # noqa: F401, E402
import nerd_toolkit.dnd.resources  # noqa: F401, E402
import nerd_toolkit.dnd.prompts  # noqa: F401, E402


def main() -> None:
    """Entry point — run the MCP server with configurable transport."""
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
```

`src/nerd_toolkit/__main__.py`:
```python
"""Allow running as: python -m nerd_toolkit"""
from nerd_toolkit.server import main

main()
```

**Step 2: Create empty module files so imports don't fail yet**

Create these empty files (they'll be implemented in subsequent tasks):

- `src/nerd_toolkit/mtg/__init__.py`
- `src/nerd_toolkit/mtg/tools.py`
- `src/nerd_toolkit/mtg/resources.py`
- `src/nerd_toolkit/mtg/prompts.py`
- `src/nerd_toolkit/dnd/__init__.py`
- `src/nerd_toolkit/dnd/tools.py`
- `src/nerd_toolkit/dnd/resources.py`
- `src/nerd_toolkit/dnd/prompts.py`

**Step 3: Verify the server module imports without errors**

```bash
uv run python -c "from nerd_toolkit.server import mcp; print('Server OK:', mcp.name)"
```

Expected: `Server OK: Nerd Toolkit`

**Step 4: Commit**

```bash
git add src/nerd_toolkit/
git commit -m "feat: add FastMCP server with lifespan and module structure"
```

---

## Task 5: MTG Tools

**Files:**
- Modify: `src/nerd_toolkit/mtg/tools.py`
- Create: `tests/test_mtg_tools.py`

**Step 1: Write the failing tests**

`tests/test_mtg_tools.py`:
```python
import httpx
import pytest
import respx

from nerd_toolkit.clients.scryfall import ScyrfallClient
from nerd_toolkit.mtg.tools import search_cards_logic, random_card_logic, build_deck_logic


SCRYFALL = "https://api.scryfall.com"


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_logic_returns_formatted_cards() -> None:
    respx.get(f"{SCRYFALL}/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": "list",
                "total_cards": 1,
                "has_more": False,
                "data": [
                    {
                        "name": "Lightning Bolt",
                        "mana_cost": "{R}",
                        "type_line": "Instant",
                        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                        "colors": ["R"],
                        "set_name": "Alpha",
                        "rarity": "common",
                        "image_uris": {"normal": "https://example.com/bolt.jpg"},
                    }
                ],
            },
        )
    )

    async with ScyrfallClient() as client:
        result = await search_cards_logic(client, query="lightning bolt")

    assert "Lightning Bolt" in result
    assert "Instant" in result


@respx.mock
@pytest.mark.asyncio
async def test_random_card_logic_returns_formatted_card() -> None:
    respx.get(f"{SCRYFALL}/cards/random").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Black Lotus",
                "mana_cost": "{0}",
                "type_line": "Artifact",
                "oracle_text": "Sacrifice Black Lotus: Add three mana of any one color.",
                "colors": [],
                "set_name": "Alpha",
                "rarity": "rare",
                "image_uris": {"normal": "https://example.com/lotus.jpg"},
            },
        )
    )

    async with ScyrfallClient() as client:
        result = await random_card_logic(client)

    assert "Black Lotus" in result
    assert "Artifact" in result


@respx.mock
@pytest.mark.asyncio
async def test_build_deck_logic_returns_deck_with_cards() -> None:
    cards = [
        {
            "name": f"Card {i}",
            "mana_cost": "{R}",
            "type_line": "Creature",
            "oracle_text": "A creature.",
            "colors": ["R"],
            "set_name": "Test",
            "rarity": "common",
        }
        for i in range(30)
    ]
    respx.get(f"{SCRYFALL}/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={"object": "list", "total_cards": 30, "has_more": False, "data": cards},
        )
    )

    async with ScyrfallClient() as client:
        result = await build_deck_logic(client, colors="red", strategy="aggro", mtg_format="standard")

    assert "Deck" in result or "deck" in result
    assert "Card 0" in result
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/test_mtg_tools.py -v
```

Expected: FAIL — `ImportError`

**Step 3: Implement MTG tools**

`src/nerd_toolkit/mtg/tools.py`:
```python
"""MTG tools for the Nerd Toolkit MCP server."""

from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from nerd_toolkit.clients.scryfall import ScyrfallClient
from nerd_toolkit.server import AppContext, mcp


def _format_card(card: dict[str, Any]) -> str:
    """Format a single card into a readable string."""
    lines = [
        f"**{card.get('name', 'Unknown')}** — {card.get('mana_cost', '')}",
        f"Type: {card.get('type_line', 'Unknown')}",
        f"Text: {card.get('oracle_text', 'N/A')}",
        f"Set: {card.get('set_name', 'Unknown')} | Rarity: {card.get('rarity', 'Unknown')}",
    ]
    image = card.get("image_uris", {}).get("normal")
    if image:
        lines.append(f"Image: {image}")
    return "\n".join(lines)


async def search_cards_logic(
    client: ScyrfallClient,
    query: str,
    color: str | None = None,
    card_type: str | None = None,
    mtg_format: str | None = None,
) -> str:
    """Core logic for search_cards, testable without MCP context."""
    cards = await client.search_cards(query, color=color, card_type=card_type, mtg_format=mtg_format)
    if not cards:
        return f"No cards found for query: {query}"
    formatted = [_format_card(card) for card in cards[:10]]
    return f"Found {len(cards)} cards (showing up to 10):\n\n" + "\n\n---\n\n".join(formatted)


async def random_card_logic(
    client: ScyrfallClient,
    color: str | None = None,
    card_type: str | None = None,
) -> str:
    """Core logic for random_card, testable without MCP context."""
    card = await client.random_card(color=color, card_type=card_type)
    return f"Here's a random card:\n\n{_format_card(card)}"


async def build_deck_logic(
    client: ScyrfallClient,
    colors: str,
    strategy: str,
    mtg_format: str,
) -> str:
    """Core logic for build_deck, testable without MCP context."""
    deck_size = 100 if mtg_format.lower() == "commander" else 60

    cards = await client.search_cards(
        query=strategy,
        color=colors,
        mtg_format=mtg_format,
    )

    if not cards:
        return f"No cards found for {colors} {strategy} in {mtg_format}."

    selected = cards[:deck_size]
    card_list = "\n".join(f"- {card.get('name', 'Unknown')}" for card in selected)

    return (
        f"## Deck: {colors.title()} {strategy.title()} ({mtg_format.title()})\n\n"
        f"**Format:** {mtg_format} | **Size:** {len(selected)}/{deck_size}\n\n"
        f"### Cards\n{card_list}\n\n"
        f"*Note: This is a starting point. Adjust quantities and add lands as needed.*"
    )


@mcp.tool()
async def search_cards(
    query: str,
    color: str | None = None,
    card_type: str | None = None,
    mtg_format: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Search for Magic: The Gathering cards by name, color, type, or format.

    Examples:
    - search_cards("lightning bolt") — find cards by name
    - search_cards("", color="red", card_type="creature", mtg_format="standard")
    """
    if ctx:
        await ctx.info(f"Searching MTG cards: {query}")
        client = ctx.request_context.lifespan_context.scryfall
    else:
        raise RuntimeError("MCP context required")
    return await search_cards_logic(client, query, color, card_type, mtg_format)


@mcp.tool()
async def random_card(
    color: str | None = None,
    card_type: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Get a random Magic: The Gathering card. Great for discovering new cards!

    Optionally filter by color (red, blue, green, white, black) or type (creature, instant, sorcery).
    """
    if ctx:
        await ctx.info("Fetching random MTG card")
        client = ctx.request_context.lifespan_context.scryfall
    else:
        raise RuntimeError("MCP context required")
    return await random_card_logic(client, color, card_type)


@mcp.tool()
async def build_deck(
    colors: str,
    strategy: str,
    mtg_format: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Build a Magic: The Gathering deck based on colors, strategy, and format.

    Args:
        colors: Color identity (e.g., "red", "blue,black", "green,white")
        strategy: Deck strategy (e.g., "aggro", "control", "combo", "midrange", "burn")
        mtg_format: Game format (e.g., "standard", "modern", "commander", "pioneer")
    """
    if ctx:
        await ctx.info(f"Building {colors} {strategy} deck for {mtg_format}")
        client = ctx.request_context.lifespan_context.scryfall
    else:
        raise RuntimeError("MCP context required")
    return await build_deck_logic(client, colors, strategy, mtg_format)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_mtg_tools.py -v
```

Expected: all 3 tests PASS.

**Step 5: Commit**

```bash
git add src/nerd_toolkit/mtg/tools.py tests/test_mtg_tools.py
git commit -m "feat: add MTG tools — search_cards, random_card, build_deck"
```

---

## Task 6: MTG Resources and Prompts

**Files:**
- Modify: `src/nerd_toolkit/mtg/resources.py`
- Modify: `src/nerd_toolkit/mtg/prompts.py`

**Step 1: Implement MTG resource**

`src/nerd_toolkit/mtg/resources.py`:
```python
"""MTG resources for the Nerd Toolkit MCP server."""

from nerd_toolkit.server import mcp

FORMATS = [
    {"name": "Standard", "description": "Rotating format with recent sets (60 cards)"},
    {"name": "Modern", "description": "Non-rotating from 8th Edition onward (60 cards)"},
    {"name": "Commander", "description": "Singleton format with a legendary commander (100 cards)"},
    {"name": "Pioneer", "description": "Non-rotating from Return to Ravnica onward (60 cards)"},
    {"name": "Legacy", "description": "All sets with a ban list (60 cards)"},
    {"name": "Vintage", "description": "All sets with restricted list (60 cards)"},
    {"name": "Pauper", "description": "Commons only (60 cards)"},
    {"name": "Draft", "description": "Build a deck from booster packs (40 cards)"},
]


@mcp.resource("mtg://formats")
def get_formats() -> str:
    """List all available Magic: The Gathering formats with descriptions."""
    lines = [f"- **{f['name']}**: {f['description']}" for f in FORMATS]
    return "# MTG Formats\n\n" + "\n".join(lines)
```

**Step 2: Implement MTG prompt**

`src/nerd_toolkit/mtg/prompts.py`:
```python
"""MTG prompts for the Nerd Toolkit MCP server."""

from nerd_toolkit.server import mcp


@mcp.prompt()
def deck_builder(colors: str, strategy: str, mtg_format: str) -> str:
    """Guide the LLM to build a complete MTG deck with reasoning.

    Args:
        colors: Color identity (e.g., "red,blue")
        strategy: Deck strategy (e.g., "aggro", "control")
        mtg_format: Format to build for (e.g., "standard", "modern")
    """
    return (
        f"I want to build a {strategy} deck in {colors} for {mtg_format} format.\n\n"
        f"Please help me by:\n"
        f"1. First, use the `search_cards` tool to find key cards for a {strategy} strategy in {colors}\n"
        f"2. Then, use `build_deck` to assemble a full deck\n"
        f"3. Explain the strategy, key synergies, and how to pilot the deck\n"
        f"4. Suggest a sideboard if applicable to {mtg_format}\n\n"
        f"Focus on competitive viability and budget-friendly options when possible."
    )
```

**Step 3: Verify server still imports cleanly**

```bash
uv run python -c "from nerd_toolkit.server import mcp; print('OK')"
```

**Step 4: Commit**

```bash
git add src/nerd_toolkit/mtg/resources.py src/nerd_toolkit/mtg/prompts.py
git commit -m "feat: add MTG resource (formats) and prompt (deck_builder)"
```

---

## Task 7: D&D Tools

**Files:**
- Modify: `src/nerd_toolkit/dnd/tools.py`
- Create: `tests/test_dnd_tools.py`

**Step 1: Write the failing tests**

`tests/test_dnd_tools.py`:
```python
import httpx
import pytest
import respx

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.dnd.tools import (
    search_monsters_logic,
    search_spells_logic,
    get_class_info_logic,
    generate_encounter_logic,
    recommend_spells_logic,
    recommend_build_logic,
)

DND_BASE = "https://www.dnd5eapi.co/api"


@respx.mock
@pytest.mark.asyncio
async def test_search_monsters_logic_by_cr() -> None:
    respx.get(f"{DND_BASE}/monsters").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "results": [{"index": "goblin", "name": "Goblin", "url": "/api/monsters/goblin"}],
            },
        )
    )
    respx.get(f"{DND_BASE}/monsters/goblin").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Goblin",
                "challenge_rating": 0.25,
                "hit_points": 7,
                "armor_class": [{"value": 15}],
                "type": "humanoid",
                "size": "Small",
                "actions": [{"name": "Scimitar", "desc": "Melee attack"}],
            },
        )
    )

    async with DndClient() as client:
        result = await search_monsters_logic(client, challenge_rating=0.25)

    assert "Goblin" in result
    assert "CR 0.25" in result


@respx.mock
@pytest.mark.asyncio
async def test_search_spells_logic_by_class_and_level() -> None:
    respx.get(f"{DND_BASE}/classes/wizard/spells").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"index": "fireball", "name": "Fireball", "level": 3, "url": "/api/spells/fireball"},
                    {"index": "shield", "name": "Shield", "level": 1, "url": "/api/spells/shield"},
                ],
            },
        )
    )

    async with DndClient() as client:
        result = await search_spells_logic(client, class_name="wizard", level=3)

    assert "Fireball" in result
    assert "Shield" not in result


@respx.mock
@pytest.mark.asyncio
async def test_get_class_info_logic() -> None:
    respx.get(f"{DND_BASE}/classes/wizard").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Wizard",
                "hit_die": 6,
                "proficiencies": [{"name": "Daggers"}, {"name": "Quarterstaffs"}],
                "saving_throws": [{"name": "INT"}, {"name": "WIS"}],
                "spellcasting": {"level": 1, "spellcasting_ability": {"name": "INT"}},
            },
        )
    )

    async with DndClient() as client:
        result = await get_class_info_logic(client, "wizard")

    assert "Wizard" in result
    assert "Hit Die: d6" in result


@respx.mock
@pytest.mark.asyncio
async def test_generate_encounter_logic() -> None:
    respx.get(f"{DND_BASE}/monsters").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"index": "goblin", "name": "Goblin", "url": "/api/monsters/goblin"},
                    {"index": "wolf", "name": "Wolf", "url": "/api/monsters/wolf"},
                ],
            },
        )
    )
    respx.get(f"{DND_BASE}/monsters/goblin").mock(
        return_value=httpx.Response(200, json={"name": "Goblin", "challenge_rating": 0.25, "hit_points": 7, "type": "humanoid"}),
    )
    respx.get(f"{DND_BASE}/monsters/wolf").mock(
        return_value=httpx.Response(200, json={"name": "Wolf", "challenge_rating": 0.25, "hit_points": 11, "type": "beast"}),
    )

    async with DndClient() as client:
        result = await generate_encounter_logic(client, party_level=1, party_size=4, difficulty="easy")

    assert "Encounter" in result or "encounter" in result


@respx.mock
@pytest.mark.asyncio
async def test_recommend_spells_logic() -> None:
    respx.get(f"{DND_BASE}/classes/wizard/spells").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {"index": "fireball", "name": "Fireball", "level": 3, "url": "/api/spells/fireball"},
                    {"index": "cure-wounds", "name": "Cure Wounds", "level": 1, "url": "/api/spells/cure-wounds"},
                ],
            },
        )
    )
    respx.get(f"{DND_BASE}/spells/fireball").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Fireball",
                "level": 3,
                "school": {"name": "Evocation"},
                "desc": ["A bright streak flashes from your pointing finger..."],
                "damage": {"damage_type": {"name": "Fire"}},
                "range": "150 feet",
                "components": ["V", "S", "M"],
                "casting_time": "1 action",
                "duration": "Instantaneous",
                "classes": [{"name": "Wizard"}, {"name": "Sorcerer"}],
            },
        )
    )

    async with DndClient() as client:
        result = await recommend_spells_logic(client, class_name="wizard", level=5, spell_type="attack")

    assert "Fireball" in result


@respx.mock
@pytest.mark.asyncio
async def test_recommend_build_logic() -> None:
    respx.get(f"{DND_BASE}/classes/wizard").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Wizard",
                "hit_die": 6,
                "proficiencies": [{"name": "Daggers"}],
                "saving_throws": [{"name": "INT"}, {"name": "WIS"}],
                "spellcasting": {"level": 1, "spellcasting_ability": {"name": "INT"}},
            },
        )
    )
    respx.get(f"{DND_BASE}/classes/wizard/spells").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 1,
                "results": [
                    {"index": "fireball", "name": "Fireball", "level": 3, "url": "/api/spells/fireball"},
                ],
            },
        )
    )
    respx.get(f"{DND_BASE}/spells/fireball").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Fireball",
                "level": 3,
                "school": {"name": "Evocation"},
                "desc": ["A bright streak flashes..."],
                "damage": {"damage_type": {"name": "Fire"}},
                "range": "150 feet",
                "components": ["V", "S", "M"],
                "casting_time": "1 action",
                "duration": "Instantaneous",
                "classes": [{"name": "Wizard"}],
            },
        )
    )

    async with DndClient() as client:
        result = await recommend_build_logic(client, class_name="wizard", level=5, playstyle="control")

    assert "Wizard" in result
    assert "Build" in result or "build" in result
```

**Step 2: Run tests to verify failure**

```bash
uv run pytest tests/test_dnd_tools.py -v
```

Expected: FAIL — `ImportError`

**Step 3: Implement D&D tools**

`src/nerd_toolkit/dnd/tools.py`:
```python
"""D&D 5e tools for the Nerd Toolkit MCP server."""

from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.server import AppContext, mcp

# Mapping of CR thresholds to party level for encounter generation
CR_BY_DIFFICULTY: dict[str, dict[str, float]] = {
    "easy": {"multiplier": 0.5},
    "medium": {"multiplier": 1.0},
    "hard": {"multiplier": 1.5},
    "deadly": {"multiplier": 2.0},
}

ATTACK_SCHOOLS = {"evocation", "necromancy", "conjuration"}
HEALING_SCHOOLS = {"evocation", "necromancy", "abjuration"}
CONTROL_SCHOOLS = {"enchantment", "illusion", "transmutation"}
UTILITY_SCHOOLS = {"divination", "transmutation", "abjuration"}

SPELL_TYPE_SCHOOLS: dict[str, set[str]] = {
    "attack": ATTACK_SCHOOLS,
    "healing": HEALING_SCHOOLS,
    "control": CONTROL_SCHOOLS,
    "utility": UTILITY_SCHOOLS,
}


def _format_monster(monster: dict[str, Any]) -> str:
    """Format a monster into a readable string."""
    ac = monster.get("armor_class", [{}])
    ac_val = ac[0].get("value", "?") if isinstance(ac, list) and ac else "?"
    return (
        f"**{monster.get('name', 'Unknown')}** — CR {monster.get('challenge_rating', '?')}\n"
        f"Type: {monster.get('type', 'Unknown')} | Size: {monster.get('size', 'Unknown')}\n"
        f"HP: {monster.get('hit_points', '?')} | AC: {ac_val}"
    )


def _format_spell(spell: dict[str, Any]) -> str:
    """Format a spell into a readable string."""
    lines = [
        f"**{spell.get('name', 'Unknown')}** (Level {spell.get('level', '?')})",
        f"School: {spell.get('school', {}).get('name', 'Unknown')}",
        f"Casting Time: {spell.get('casting_time', '?')} | Range: {spell.get('range', '?')}",
        f"Duration: {spell.get('duration', '?')} | Components: {', '.join(spell.get('components', []))}",
    ]
    desc = spell.get("desc", [])
    if desc:
        lines.append(f"Description: {desc[0][:200]}...")
    damage = spell.get("damage", {})
    if damage:
        dtype = damage.get("damage_type", {}).get("name", "")
        if dtype:
            lines.append(f"Damage Type: {dtype}")
    return "\n".join(lines)


async def search_monsters_logic(
    client: DndClient,
    name: str | None = None,
    challenge_rating: float | None = None,
) -> str:
    """Core logic for search_monsters."""
    monsters = await client.search_monsters(challenge_rating=challenge_rating)

    if name:
        monsters = [m for m in monsters if name.lower() in m.get("name", "").lower()]

    if not monsters:
        return "No monsters found matching your criteria."

    detailed: list[str] = []
    for monster in monsters[:10]:
        detail = await client.get_monster_detail(monster["index"])
        detailed.append(_format_monster(detail))

    return f"Found {len(monsters)} monsters (showing up to 10):\n\n" + "\n\n---\n\n".join(detailed)


async def search_spells_logic(
    client: DndClient,
    name: str | None = None,
    level: int | None = None,
    class_name: str | None = None,
) -> str:
    """Core logic for search_spells."""
    if class_name:
        spells = await client.get_spells_by_class(class_name)
    else:
        # Without a class filter, we'd need to list all spells — use the base endpoint
        response = await client._request_with_retry("GET", "/spells")
        data = response.json()
        spells = data.get("results", [])

    if level is not None:
        spells = [s for s in spells if s.get("level") == level]

    if name:
        spells = [s for s in spells if name.lower() in s.get("name", "").lower()]

    if not spells:
        return "No spells found matching your criteria."

    lines = [f"- **{s['name']}** (Level {s.get('level', '?')})" for s in spells[:20]]
    return f"Found {len(spells)} spells (showing up to 20):\n\n" + "\n".join(lines)


async def get_class_info_logic(client: DndClient, class_name: str) -> str:
    """Core logic for get_class_info."""
    info = await client.get_class_info(class_name)

    proficiencies = ", ".join(p.get("name", "") for p in info.get("proficiencies", []))
    saves = ", ".join(s.get("name", "") for s in info.get("saving_throws", []))

    lines = [
        f"# {info.get('name', 'Unknown')}",
        f"",
        f"**Hit Die:** d{info.get('hit_die', '?')}",
        f"**Saving Throws:** {saves}",
        f"**Proficiencies:** {proficiencies}",
    ]

    spellcasting = info.get("spellcasting")
    if spellcasting:
        ability = spellcasting.get("spellcasting_ability", {}).get("name", "?")
        lines.append(f"**Spellcasting Ability:** {ability} (from level {spellcasting.get('level', '?')})")

    return "\n".join(lines)


async def generate_encounter_logic(
    client: DndClient,
    party_level: int,
    party_size: int,
    difficulty: str,
) -> str:
    """Core logic for generate_encounter."""
    difficulty = difficulty.lower()
    if difficulty not in CR_BY_DIFFICULTY:
        return f"Invalid difficulty. Choose from: {', '.join(CR_BY_DIFFICULTY.keys())}"

    multiplier = CR_BY_DIFFICULTY[difficulty]["multiplier"]
    target_cr = max(0.125, party_level * multiplier / party_size)

    # Find monsters near the target CR
    cr_options = [0.125, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    closest_cr = min(cr_options, key=lambda x: abs(x - target_cr))

    monsters = await client.search_monsters(challenge_rating=closest_cr)

    if not monsters:
        return f"No monsters found for CR {closest_cr}."

    # Pick a few monsters for the encounter
    import random
    selected = random.sample(monsters, min(party_size, len(monsters)))
    detailed: list[str] = []
    for monster in selected:
        detail = await client.get_monster_detail(monster["index"])
        detailed.append(_format_monster(detail))

    return (
        f"## Encounter ({difficulty.title()})\n\n"
        f"**Party:** {party_size} players, level {party_level}\n"
        f"**Target CR:** {closest_cr}\n\n"
        f"### Monsters\n\n" + "\n\n---\n\n".join(detailed)
    )


async def recommend_spells_logic(
    client: DndClient,
    class_name: str,
    level: int,
    spell_type: str,
) -> str:
    """Core logic for recommend_spells."""
    spell_type = spell_type.lower()
    target_schools = SPELL_TYPE_SCHOOLS.get(spell_type)
    if not target_schools:
        return f"Invalid spell type. Choose from: {', '.join(SPELL_TYPE_SCHOOLS.keys())}"

    # Get all spells for this class
    class_spells = await client.get_spells_by_class(class_name)

    # Filter by max castable level (class level determines max spell level)
    max_spell_level = min(9, (level + 1) // 2)
    eligible = [s for s in class_spells if s.get("level", 0) <= max_spell_level and s.get("level", 0) > 0]

    # Get details and filter by school
    recommended: list[str] = []
    for spell in eligible[:30]:  # Limit API calls
        detail = await client.get_spell_detail(spell["index"])
        school = detail.get("school", {}).get("name", "").lower()
        if school in target_schools:
            recommended.append(_format_spell(detail))

    if not recommended:
        return f"No {spell_type} spells found for {class_name} at level {level}."

    return (
        f"## Recommended {spell_type.title()} Spells for {class_name.title()} (Level {level})\n\n"
        f"Max spell level you can cast: {max_spell_level}\n\n"
        + "\n\n---\n\n".join(recommended[:10])
    )


async def recommend_build_logic(
    client: DndClient,
    class_name: str,
    level: int,
    playstyle: str,
) -> str:
    """Core logic for recommend_build."""
    # Get class info
    class_info = await client.get_class_info(class_name)

    # Get recommended spells matching playstyle
    spell_type_map = {
        "damage": "attack",
        "tank": "utility",
        "healer": "healing",
        "support": "utility",
        "control": "control",
        "blaster": "attack",
    }
    mapped_type = spell_type_map.get(playstyle.lower(), "attack")
    target_schools = SPELL_TYPE_SCHOOLS.get(mapped_type, ATTACK_SCHOOLS)

    max_spell_level = min(9, (level + 1) // 2)
    class_spells = await client.get_spells_by_class(class_name)
    eligible = [s for s in class_spells if s.get("level", 0) <= max_spell_level and s.get("level", 0) > 0]

    top_spells: list[str] = []
    for spell in eligible[:20]:
        detail = await client.get_spell_detail(spell["index"])
        school = detail.get("school", {}).get("name", "").lower()
        if school in target_schools:
            top_spells.append(f"- **{detail['name']}** (Level {detail['level']}, {detail['school']['name']})")

    proficiencies = ", ".join(p.get("name", "") for p in class_info.get("proficiencies", []))
    saves = ", ".join(s.get("name", "") for s in class_info.get("saving_throws", []))

    spellcasting_section = ""
    if class_info.get("spellcasting"):
        ability = class_info["spellcasting"].get("spellcasting_ability", {}).get("name", "?")
        spellcasting_section = f"\n### Spellcasting\n**Primary Ability:** {ability}\n"

    spell_list = "\n".join(top_spells[:10]) if top_spells else "No specific spells matched this playstyle."

    return (
        f"## Build Recommendation: {class_name.title()} Level {level} ({playstyle.title()})\n\n"
        f"### Class Overview\n"
        f"**Hit Die:** d{class_info.get('hit_die', '?')}\n"
        f"**Saving Throws:** {saves}\n"
        f"**Proficiencies:** {proficiencies}\n"
        f"{spellcasting_section}\n"
        f"### Recommended Spells ({playstyle.title()} focus)\n"
        f"Max spell level at level {level}: {max_spell_level}\n\n"
        f"{spell_list}\n\n"
        f"### Strategy Tips\n"
        f"As a {playstyle} {class_name.lower()}, focus on maximizing your "
        f"{'spell save DC and area effects' if playstyle == 'control' else 'damage output and spell slot efficiency'}. "
        f"Prioritize {'Intelligence' if class_info.get('spellcasting', {}).get('spellcasting_ability', {}).get('name') == 'INT' else 'your primary casting stat'} "
        f"for ability score improvements."
    )


# --- MCP Tool Registration ---


@mcp.tool()
async def search_monsters(
    name: str | None = None,
    challenge_rating: float | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Search for D&D 5e monsters by name or challenge rating (CR).

    Examples:
    - search_monsters(name="dragon") — find all dragons
    - search_monsters(challenge_rating=0.25) — find CR 1/4 monsters
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Searching monsters: name={name}, cr={challenge_rating}")
    return await search_monsters_logic(ctx.request_context.lifespan_context.dnd, name, challenge_rating)


@mcp.tool()
async def search_spells(
    name: str | None = None,
    level: int | None = None,
    class_name: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Search for D&D 5e spells by name, spell level, or class.

    Examples:
    - search_spells(name="fireball") — find spells by name
    - search_spells(class_name="wizard", level=3) — all 3rd level wizard spells
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Searching spells: name={name}, level={level}, class={class_name}")
    return await search_spells_logic(ctx.request_context.lifespan_context.dnd, name, level, class_name)


@mcp.tool()
async def get_class_info(
    class_name: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Get detailed information about a D&D 5e class including hit die, proficiencies, and spellcasting.

    Available classes: barbarian, bard, cleric, druid, fighter, monk, paladin, ranger, rogue, sorcerer, warlock, wizard
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Fetching class info: {class_name}")
    return await get_class_info_logic(ctx.request_context.lifespan_context.dnd, class_name)


@mcp.tool()
async def generate_encounter(
    party_level: int,
    party_size: int,
    difficulty: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Generate a balanced D&D 5e combat encounter for a party.

    Args:
        party_level: Average level of the party (1-20)
        party_size: Number of players in the party
        difficulty: Encounter difficulty — easy, medium, hard, or deadly
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Generating {difficulty} encounter for {party_size} level-{party_level} players")
    return await generate_encounter_logic(ctx.request_context.lifespan_context.dnd, party_level, party_size, difficulty)


@mcp.tool()
async def recommend_spells(
    class_name: str,
    level: int,
    spell_type: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Recommend spells for a D&D character based on class, level, and desired type.

    Perfect for: "I'm a level 5 wizard and I want attack spells — what do you recommend?"

    Args:
        class_name: Character's class (e.g., "wizard", "cleric")
        level: Character level (1-20)
        spell_type: Type of spell desired — attack, healing, control, or utility
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Recommending {spell_type} spells for level {level} {class_name}")
    return await recommend_spells_logic(ctx.request_context.lifespan_context.dnd, class_name, level, spell_type)


@mcp.tool()
async def recommend_build(
    class_name: str,
    level: int,
    playstyle: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Recommend a complete character build for D&D 5e including spells, equipment, and strategy.

    Perfect for: "I want to play a level 5 wizard focused on control — what's the best build?"

    Args:
        class_name: Character's class (e.g., "wizard", "fighter")
        level: Character level (1-20)
        playstyle: Preferred playstyle — damage, tank, healer, support, control, or blaster
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Recommending {playstyle} build for level {level} {class_name}")
    return await recommend_build_logic(ctx.request_context.lifespan_context.dnd, class_name, level, playstyle)
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_dnd_tools.py -v
```

Expected: all 6 tests PASS.

**Step 5: Commit**

```bash
git add src/nerd_toolkit/dnd/tools.py tests/test_dnd_tools.py
git commit -m "feat: add D&D tools — search, encounters, spell/build recommendations"
```

---

## Task 8: D&D Resources and Prompts

**Files:**
- Modify: `src/nerd_toolkit/dnd/resources.py`
- Modify: `src/nerd_toolkit/dnd/prompts.py`

**Step 1: Implement D&D resource**

`src/nerd_toolkit/dnd/resources.py`:
```python
"""D&D 5e resources for the Nerd Toolkit MCP server."""

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from nerd_toolkit.server import AppContext, mcp


@mcp.resource("dnd://classes")
async def get_classes(ctx: Context[ServerSession, AppContext]) -> str:
    """List all available D&D 5e classes with a brief description."""
    client = ctx.request_context.lifespan_context.dnd
    classes = await client.list_classes()

    lines = [f"- **{c['name']}**" for c in classes]
    return "# D&D 5e Classes\n\n" + "\n".join(lines)
```

**Step 2: Implement D&D prompts**

`src/nerd_toolkit/dnd/prompts.py`:
```python
"""D&D 5e prompts for the Nerd Toolkit MCP server."""

from nerd_toolkit.server import mcp


@mcp.prompt()
def encounter_planner(party_level: str, party_size: str, theme: str) -> str:
    """Plan a themed combat encounter for a D&D party.

    Args:
        party_level: Average party level
        party_size: Number of players
        theme: Encounter theme (e.g., "undead crypt", "goblin ambush", "dragon lair")
    """
    return (
        f"I need to plan a {theme} encounter for {party_size} players at level {party_level}.\n\n"
        f"Please:\n"
        f"1. Use `generate_encounter` to create a balanced fight (try 'medium' difficulty first)\n"
        f"2. Use `search_monsters` to find thematic monsters matching '{theme}'\n"
        f"3. Describe the battlefield setup and terrain features\n"
        f"4. Suggest tactical strategies for the monsters\n"
        f"5. Include potential loot and XP rewards\n\n"
        f"Make the encounter feel dramatic and memorable!"
    )


@mcp.prompt()
def spell_advisor(class_name: str, level: str) -> str:
    """Interactively guide a player in choosing spells for their character.

    Args:
        class_name: Character's class
        level: Character's level
    """
    return (
        f"I'm playing a {class_name} at level {level} and need help choosing spells.\n\n"
        f"Please:\n"
        f"1. Use `get_class_info` to check the {class_name}'s spellcasting details\n"
        f"2. Ask me about my playstyle preference (attack, control, healing, utility)\n"
        f"3. Use `recommend_spells` to find the best options\n"
        f"4. Explain each recommended spell — when to use it, combos, and tactical tips\n"
        f"5. Suggest a balanced spell loadout for different situations\n\n"
        f"Be opinionated! Tell me which spells are must-haves and which are traps."
    )
```

**Step 3: Verify server imports cleanly**

```bash
uv run python -c "from nerd_toolkit.server import mcp; print('OK')"
```

**Step 4: Commit**

```bash
git add src/nerd_toolkit/dnd/resources.py src/nerd_toolkit/dnd/prompts.py
git commit -m "feat: add D&D resource (classes) and prompts (encounter_planner, spell_advisor)"
```

---

## Task 9: Full Test Suite + Lint + Typecheck

**Step 1: Run full test suite**

```bash
make test
```

Expected: all tests PASS.

**Step 2: Run linter**

```bash
make lint
```

Fix any issues that arise.

**Step 3: Run formatter**

```bash
make format
```

**Step 4: Run type checker**

```bash
make typecheck
```

Fix any type errors. Common issues:
- Add `type: ignore` for dynamic MCP context access if mypy complains
- Ensure all function signatures have return types

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: fix lint and type errors across codebase"
```

---

## Task 10: Integration Test with MCP Inspector

**Step 1: Start the server in HTTP mode**

```bash
make dev-http
```

**Step 2: Open MCP Inspector in another terminal**

```bash
make inspect
```

**Step 3: Manual test checklist**

Connect to `http://localhost:8000/mcp` and verify:

- [ ] Tools tab shows all 9 tools with correct descriptions
- [ ] Resources tab shows `mtg://formats` and `dnd://classes`
- [ ] Prompts tab shows `deck_builder`, `encounter_planner`, `spell_advisor`
- [ ] Call `random_card` — returns a card with name, type, and text
- [ ] Call `search_cards` with query "lightning bolt" — returns results
- [ ] Call `search_spells` with class_name "wizard", level 3 — returns spells
- [ ] Call `recommend_spells` with class_name "wizard", level 5, spell_type "attack" — returns attack spells
- [ ] Call `recommend_build` with class_name "wizard", level 5, playstyle "control" — returns full build
- [ ] Call `generate_encounter` with party_level 3, party_size 4, difficulty "medium" — returns encounter

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: nerd toolkit MCP server — complete POC with MTG and D&D tools"
```
