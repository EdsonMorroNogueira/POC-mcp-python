"""MTG prompts for the Nerd Toolkit MCP server."""

from nerd_toolkit.server import mcp


@mcp.prompt()
def deck_builder(colors: str, strategy: str, mtg_format: str, theme: str = "") -> str:
    """Guide the LLM to build a complete MTG deck with reasoning.

    Args:
        colors: Color identity (e.g., "red,blue")
        strategy: Deck strategy (e.g., "aggro", "control")
        mtg_format: Format to build for (e.g., "standard", "modern")
        theme: Optional theme or flavor preference (e.g., "female vampires", "dragons", "angels")
    """
    theme_instruction = ""
    if theme:
        theme_instruction = (
            f"\n**Theme preference:** {theme}\n"
            f"Use the `keyword` parameter in search_cards to filter by theme.\n"
            f"For character gender, use Scryfall regex in keyword like: "
            f"name:/queen|lady|princess|matriarch|baroness/\n"
            f"For creature themes, use type or oracle text filters.\n"
        )

    return (
        f"I want to build a {strategy} deck in {colors} for {mtg_format} format.\n\n"
        f"{theme_instruction}"
        f"Please help me by:\n"
        f"1. First, use `search_cards` to find key cards for a {strategy} strategy in {colors}\n"
        f"2. If there's a theme, use the `keyword` param to filter thematically\n"
        f"3. Use `build_deck` to assemble a full deck\n"
        f"4. Explain the strategy, key synergies, and how to pilot the deck\n"
        f"5. Suggest a sideboard if applicable to {mtg_format}\n\n"
        f"Focus on competitive viability and budget-friendly options when possible."
    )
