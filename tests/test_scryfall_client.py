from urllib.parse import unquote

import httpx
import pytest
import respx

from nerd_toolkit.clients.scryfall import ScryfallClient


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_returns_card_list() -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(
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
        result = await client.search_cards("lightning bolt")

    assert len(result) == 1
    assert result[0]["name"] == "Lightning Bolt"


@respx.mock
@pytest.mark.asyncio
async def test_random_card_returns_single_card() -> None:
    respx.get("https://api.scryfall.com/cards/random").mock(
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
        result = await client.random_card()

    assert result["name"] == "Black Lotus"


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_with_filters_builds_query() -> None:
    route = respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=httpx.Response(
            200,
            json={"object": "list", "total_cards": 0, "has_more": False, "data": []},
        )
    )

    async with ScryfallClient() as client:
        await client.search_cards("bolt", color="red", card_type="instant", mtg_format="modern")

    url = unquote(str(route.calls[0].request.url))
    assert "c:red" in url
    assert "t:instant" in url
    assert "f:modern" in url


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_retries_on_server_error() -> None:
    route = respx.get("https://api.scryfall.com/cards/search")
    route.side_effect = [
        httpx.Response(500, json={"details": "server error"}),
        httpx.Response(500, json={"details": "server error"}),
        httpx.Response(
            200,
            json={"object": "list", "total_cards": 0, "has_more": False, "data": []},
        ),
    ]

    async with ScryfallClient() as client:
        result = await client.search_cards("test")

    assert result == []
    assert route.call_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_search_cards_raises_after_max_retries() -> None:
    respx.get("https://api.scryfall.com/cards/search").mock(
        return_value=httpx.Response(500, json={"details": "server error"})
    )

    async with ScryfallClient() as client:
        with pytest.raises(Exception, match="500"):
            await client.search_cards("test")
