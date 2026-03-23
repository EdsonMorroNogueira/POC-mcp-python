import httpx
import pytest
import respx

from nerd_toolkit.clients.dnd import DndClient
from nerd_toolkit.dnd.tools import (
    generate_encounter_logic,
    get_class_info_logic,
    recommend_build_logic,
    recommend_spells_logic,
    search_monsters_logic,
    search_spells_logic,
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
                    {
                        "index": "fireball", "name": "Fireball",
                        "level": 3, "url": "/api/spells/fireball",
                    },
                    {
                        "index": "shield", "name": "Shield",
                        "level": 1, "url": "/api/spells/shield",
                    },
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
    assert "Hit Die:** d6" in result


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
        return_value=httpx.Response(
            200,
            json={
                "name": "Goblin", "challenge_rating": 0.25,
                "hit_points": 7, "type": "humanoid",
            },
        ),
    )
    respx.get(f"{DND_BASE}/monsters/wolf").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Wolf", "challenge_rating": 0.25,
                "hit_points": 11, "type": "beast",
            },
        ),
    )

    async with DndClient() as client:
        result = await generate_encounter_logic(
            client, party_level=1, party_size=4, difficulty="easy",
        )

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
                    {
                        "index": "fireball", "name": "Fireball",
                        "level": 3, "url": "/api/spells/fireball",
                    },
                    {
                        "index": "cure-wounds", "name": "Cure Wounds",
                        "level": 1, "url": "/api/spells/cure-wounds",
                    },
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
    respx.get(f"{DND_BASE}/spells/cure-wounds").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Cure Wounds",
                "level": 1,
                "school": {"name": "Evocation"},
                "desc": ["A creature you touch regains hit points..."],
                "range": "Touch",
                "components": ["V", "S"],
                "casting_time": "1 action",
                "duration": "Instantaneous",
                "classes": [{"name": "Cleric"}],
            },
        )
    )

    async with DndClient() as client:
        result = await recommend_spells_logic(
            client, class_name="wizard", level=5, spell_type="attack",
        )

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
                    {
                        "index": "fireball", "name": "Fireball",
                        "level": 3, "url": "/api/spells/fireball",
                    },
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
        result = await recommend_build_logic(
            client, class_name="wizard", level=5, playstyle="control",
        )

    assert "Wizard" in result
    assert "Build" in result or "build" in result
