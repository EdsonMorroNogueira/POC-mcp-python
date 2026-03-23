"""D&D 5e tools for the Nerd Toolkit MCP server."""

import random
from typing import Any

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.server import AppContext, mcp

# CR thresholds for encounter difficulty
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
        f"Duration: {spell.get('duration', '?')} | "
        f"Components: {', '.join(spell.get('components', []))}",
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
        "",
        f"**Hit Die:** d{info.get('hit_die', '?')}",
        f"**Saving Throws:** {saves}",
        f"**Proficiencies:** {proficiencies}",
    ]

    spellcasting = info.get("spellcasting")
    if spellcasting:
        ability = spellcasting.get("spellcasting_ability", {}).get("name", "?")
        lines.append(
            f"**Spellcasting Ability:** {ability} (from level {spellcasting.get('level', '?')})"
        )

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

    cr_options = [0.125, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    closest_cr = min(cr_options, key=lambda x: abs(x - target_cr))

    monsters = await client.search_monsters(challenge_rating=closest_cr)

    if not monsters:
        return f"No monsters found for CR {closest_cr}."

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

    class_spells = await client.get_spells_by_class(class_name)
    max_spell_level = min(9, (level + 1) // 2)
    eligible = [
        s for s in class_spells if s.get("level", 0) <= max_spell_level and s.get("level", 0) > 0
    ]

    recommended: list[str] = []
    for spell in eligible[:30]:
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
    class_info = await client.get_class_info(class_name)

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
    eligible = [
        s for s in class_spells if s.get("level", 0) <= max_spell_level and s.get("level", 0) > 0
    ]

    top_spells: list[str] = []
    for spell in eligible[:20]:
        detail = await client.get_spell_detail(spell["index"])
        school = detail.get("school", {}).get("name", "").lower()
        if school in target_schools:
            top_spells.append(
                f"- **{detail['name']}** (Level {detail['level']}, {detail['school']['name']})"
            )

    proficiencies = ", ".join(p.get("name", "") for p in class_info.get("proficiencies", []))
    saves = ", ".join(s.get("name", "") for s in class_info.get("saving_throws", []))

    spellcasting_section = ""
    if class_info.get("spellcasting"):
        ability = class_info["spellcasting"].get("spellcasting_ability", {}).get("name", "?")
        spellcasting_section = f"\n### Spellcasting\n**Primary Ability:** {ability}\n"

    spell_list = (
        "\n".join(top_spells[:10]) if top_spells else "No specific spells matched this playstyle."
    )

    casting_ability = class_info.get("spellcasting", {}).get("spellcasting_ability", {}).get("name")

    if playstyle == "control":
        focus = "spell save DC and area effects"
    else:
        focus = "damage output and spell slot efficiency"

    priority = "Intelligence" if casting_ability == "INT" else "your primary casting stat"

    return (
        f"## Build Recommendation: {class_name.title()} "
        f"Level {level} ({playstyle.title()})\n\n"
        f"### Class Overview\n"
        f"**Hit Die:** d{class_info.get('hit_die', '?')}\n"
        f"**Saving Throws:** {saves}\n"
        f"**Proficiencies:** {proficiencies}\n"
        f"{spellcasting_section}\n"
        f"### Recommended Spells ({playstyle.title()} focus)\n"
        f"Max spell level at level {level}: {max_spell_level}\n\n"
        f"{spell_list}\n\n"
        f"### Strategy Tips\n"
        f"As a {playstyle} {class_name.lower()}, focus on "
        f"maximizing your {focus}. "
        f"Prioritize {priority} for ability score improvements."
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
    - search_monsters(name="dragon") -- find all dragons
    - search_monsters(challenge_rating=0.25) -- find CR 1/4 monsters
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Searching monsters: name={name}, cr={challenge_rating}")
    return await search_monsters_logic(
        ctx.request_context.lifespan_context.dnd, name, challenge_rating
    )


@mcp.tool()
async def search_spells(
    name: str | None = None,
    level: int | None = None,
    class_name: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Search for D&D 5e spells by name, spell level, or class.

    Examples:
    - search_spells(name="fireball") -- find spells by name
    - search_spells(class_name="wizard", level=3) -- all 3rd level wizard spells
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Searching spells: name={name}, level={level}, class={class_name}")
    return await search_spells_logic(
        ctx.request_context.lifespan_context.dnd, name, level, class_name
    )


@mcp.tool()
async def get_class_info(
    class_name: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Get detailed information about a D&D 5e class.

    Includes hit die, proficiencies, and spellcasting info.
    Available classes: barbarian, bard, cleric, druid, fighter, monk,
    paladin, ranger, rogue, sorcerer, warlock, wizard
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
        difficulty: Encounter difficulty -- easy, medium, hard, or deadly
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(
        f"Generating {difficulty} encounter for {party_size} level-{party_level} players"
    )
    return await generate_encounter_logic(
        ctx.request_context.lifespan_context.dnd, party_level, party_size, difficulty
    )


@mcp.tool()
async def recommend_spells(
    class_name: str,
    level: int,
    spell_type: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Recommend spells for a D&D character based on class, level, and desired type.

    Args:
        class_name: Character's class (e.g., "wizard", "cleric")
        level: Character level (1-20)
        spell_type: Type of spell desired -- attack, healing, control, or utility
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Recommending {spell_type} spells for level {level} {class_name}")
    return await recommend_spells_logic(
        ctx.request_context.lifespan_context.dnd, class_name, level, spell_type
    )


@mcp.tool()
async def recommend_build(
    class_name: str,
    level: int,
    playstyle: str,
    ctx: Context[ServerSession, AppContext] | None = None,
) -> str:
    """Recommend a complete character build for D&D 5e.

    Includes spells, equipment, and strategy tips.

    Args:
        class_name: Character's class (e.g., "wizard", "fighter")
        level: Character level (1-20)
        playstyle: Preferred playstyle -- damage, tank, healer, support, control, or blaster
    """
    if not ctx:
        raise RuntimeError("MCP context required")
    await ctx.info(f"Recommending {playstyle} build for level {level} {class_name}")
    return await recommend_build_logic(
        ctx.request_context.lifespan_context.dnd, class_name, level, playstyle
    )
