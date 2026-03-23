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
                    {
                        "index": "fireball",
                        "name": "Fireball",
                        "level": 3,
                        "url": "/api/spells/fireball",
                    },
                    {
                        "index": "magic-missile",
                        "name": "Magic Missile",
                        "level": 1,
                        "url": "/api/spells/magic-missile",
                    },
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
            json={
                "count": 1,
                "results": [
                    {"index": "wizard", "name": "Wizard", "url": "/api/classes/wizard"},
                ],
            },
        )
    )

    async with DndClient() as client:
        await client.list_classes()
        await client.list_classes()

    assert route.call_count == 1
