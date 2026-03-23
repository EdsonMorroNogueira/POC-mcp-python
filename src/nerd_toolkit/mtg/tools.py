"""MTG tools for the Nerd Toolkit MCP server."""

from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from nerd_toolkit.clients.scryfall import ScryfallClient
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
    client: ScryfallClient,
    query: str,
    color: str | None = None,
    card_type: str | None = None,
    mtg_format: str | None = None,
) -> str:
    """Core logic for search_cards, testable without MCP context."""
    cards = await client.search_cards(
        query, color=color, card_type=card_type, mtg_format=mtg_format
    )
    if not cards:
        return f"No cards found for query: {query}"
    formatted = [_format_card(card) for card in cards[:10]]
    return f"Found {len(cards)} cards (showing up to 10):\n\n" + "\n\n---\n\n".join(formatted)


async def random_card_logic(
    client: ScryfallClient,
    color: str | None = None,
    card_type: str | None = None,
) -> str:
    """Core logic for random_card, testable without MCP context."""
    card = await client.random_card(color=color, card_type=card_type)
    return f"Here's a random card:\n\n{_format_card(card)}"


async def build_deck_logic(
    client: ScryfallClient,
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

    Optionally filter by color (red, blue, green, white, black)
    or type (creature, instant, sorcery).
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
