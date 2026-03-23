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
