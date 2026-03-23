import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal

from mcp.server.fastmcp import FastMCP

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.clients.scryfall import ScryfallClient


@dataclass
class AppContext:
    """Application context holding initialized HTTP clients."""

    scryfall: ScryfallClient
    dnd: DndClient


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage HTTP client lifecycle — create on startup, close on shutdown."""
    scryfall = ScryfallClient()
    dnd = DndClient()

    async with scryfall, dnd:
        yield AppContext(scryfall=scryfall, dnd=dnd)


mcp = FastMCP("Nerd Toolkit", lifespan=app_lifespan)

# Import tools, resources, and prompts so they register with the server
import nerd_toolkit.dnd.prompts  # noqa: F401, E402
import nerd_toolkit.dnd.resources  # noqa: F401, E402
import nerd_toolkit.dnd.tools  # noqa: F401, E402
import nerd_toolkit.mtg.prompts  # noqa: F401, E402
import nerd_toolkit.mtg.resources  # noqa: F401, E402
import nerd_toolkit.mtg.tools  # noqa: F401, E402


def main() -> None:
    """Entry point — run the MCP server with configurable transport."""
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] in ("stdio", "sse", "streamable-http"):
        transport = sys.argv[1]  # type: ignore[assignment]
    mcp.run(transport=transport)
