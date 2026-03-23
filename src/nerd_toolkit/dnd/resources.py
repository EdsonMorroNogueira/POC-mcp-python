"""D&D 5e resources for the Nerd Toolkit MCP server."""

from nerd_toolkit.server import mcp

CLASSES = [
    {"name": "Barbarian", "description": "A fierce warrior who can enter a battle rage"},
    {"name": "Bard", "description": "An inspiring magician whose music and words shape reality"},
    {"name": "Cleric", "description": "A priestly champion who wields divine magic"},
    {"name": "Druid", "description": "A priest of the Old Faith, wielding nature's power"},
    {
        "name": "Fighter",
        "description": "A master of martial combat, skilled with a variety of weapons",
    },
    {"name": "Monk", "description": "A master of martial arts, harnessing the power of ki"},
    {"name": "Paladin", "description": "A holy warrior bound to a sacred oath"},
    {"name": "Ranger", "description": "A warrior who combats threats on the edges of civilization"},
    {
        "name": "Rogue",
        "description": "A scoundrel who uses stealth and trickery to overcome obstacles",
    },
    {
        "name": "Sorcerer",
        "description": "A spellcaster who draws on inherent magic from a gift or bloodline",
    },
    {
        "name": "Warlock",
        "description": "A wielder of magic derived from a pact with an extraplanar entity",
    },
    {"name": "Wizard", "description": "A scholarly magic-user who studies the arcane arts"},
]


@mcp.resource("dnd://classes")
def get_classes() -> str:
    """List all available D&D 5e classes with descriptions."""
    lines = [f"- **{c['name']}**: {c['description']}" for c in CLASSES]
    return "# D&D 5e Classes\n\n" + "\n".join(lines)
