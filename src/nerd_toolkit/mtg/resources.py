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
