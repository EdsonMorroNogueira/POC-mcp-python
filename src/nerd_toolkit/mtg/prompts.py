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
        f"1. First, use the `search_cards` tool to find key cards "
        f"for a {strategy} strategy in {colors}\n"
        f"2. Then, use `build_deck` to assemble a full deck\n"
        f"3. Explain the strategy, key synergies, and how to pilot the deck\n"
        f"4. Suggest a sideboard if applicable to {mtg_format}\n\n"
        f"Focus on competitive viability and budget-friendly options when possible."
    )
