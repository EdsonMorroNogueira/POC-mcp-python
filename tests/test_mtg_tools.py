import httpx
import pytest
import respx

from nerd_toolkit.clients.scryfall import ScryfallClient
from nerd_toolkit.mtg.tools import build_deck_logic, random_card_logic, search_cards_logic

SCRYFALL = "https://api.scryfall.com"


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_logic_returns_formatted_cards() -> None:
    respx.get(f"{SCRYFALL}/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "object": "list",
                "total_cards": 1,
                "has_more": False,
                "data": [
                    {
                        "name": "Lightning Bolt",
                        "mana_cost": "{R}",
                        "type_line": "Instant",
                        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                        "colors": ["R"],
                        "set_name": "Alpha",
                        "rarity": "common",
                        "image_uris": {"normal": "https://example.com/bolt.jpg"},
                    }
                ],
            },
        )
    )

    async with ScryfallClient() as client:
        result = await search_cards_logic(client, query="lightning bolt")

    assert "Lightning Bolt" in result
    assert "Instant" in result


@respx.mock
@pytest.mark.asyncio
async def test_random_card_logic_returns_formatted_card() -> None:
    respx.get(f"{SCRYFALL}/cards/random").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Black Lotus",
                "mana_cost": "{0}",
                "type_line": "Artifact",
                "oracle_text": "Sacrifice Black Lotus: Add three mana of any one color.",
                "colors": [],
                "set_name": "Alpha",
                "rarity": "rare",
                "image_uris": {"normal": "https://example.com/lotus.jpg"},
            },
        )
    )

    async with ScryfallClient() as client:
        result = await random_card_logic(client)

    assert "Black Lotus" in result
    assert "Artifact" in result


@respx.mock
@pytest.mark.asyncio
async def test_build_deck_logic_returns_deck_with_cards() -> None:
    cards = [
        {
            "name": f"Card {i}",
            "mana_cost": "{R}",
            "type_line": "Creature",
            "oracle_text": "A creature.",
            "colors": ["R"],
            "set_name": "Test",
            "rarity": "common",
        }
        for i in range(30)
    ]
    respx.get(f"{SCRYFALL}/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={"object": "list", "total_cards": 30, "has_more": False, "data": cards},
        )
    )

    async with ScryfallClient() as client:
        result = await build_deck_logic(
            client, colors="red", strategy="aggro", mtg_format="standard"
        )

    assert "Deck" in result or "deck" in result
    assert "Card 0" in result
