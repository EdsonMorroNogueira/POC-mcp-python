# Nerd Toolkit MCP Server — Design Document

**Date:** 2026-03-23
**Status:** Approved

## Goal

A proof-of-concept MCP (Model Context Protocol) server in Python that exposes
Magic: The Gathering (via Scryfall API) and Dungeons & Dragons 5e (via D&D 5e API)
tools for LLMs to consume in a structured way.

The project is called **Nerd Toolkit** — an MCP server that turns the LLM into a
nerd consultant: builds MTG decks, recommends D&D builds, generates encounters,
and advises on spells.

---

## Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Package Manager | uv |
| MCP SDK | mcp[cli] (FastMCP) |
| HTTP Client | httpx (async) |
| Validation | pydantic (included in MCP SDK) |
| Config | pydantic-settings (env vars) |
| Tests | pytest + respx |
| Linting | ruff |
| Type Checking | mypy |
| Task Runner | Makefile |

---

## Architecture

### Approach: Modular by Domain

Each domain (MTG, D&D) lives in its own module with tools, resources, and prompts
separated. A central `server.py` registers everything via FastMCP.

```
POC-mcp-python/
├── src/
│   └── nerd_toolkit/
│       ├── __init__.py
│       ├── server.py              # FastMCP server + tool registration
│       ├── config.py              # Settings via pydantic-settings (env vars)
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── scryfall.py        # HTTP client for Scryfall API
│       │   └── dnd.py             # HTTP client for D&D 5e API
│       ├── mtg/
│       │   ├── __init__.py
│       │   ├── tools.py           # search_cards, random_card, build_deck
│       │   ├── resources.py       # mtg://formats
│       │   └── prompts.py         # deck_builder prompt
│       └── dnd/
│           ├── __init__.py
│           ├── tools.py           # search_monsters, search_spells, get_class_info,
│           │                      # generate_encounter, recommend_spells, recommend_build
│           ├── resources.py       # dnd://classes
│           └── prompts.py         # encounter_planner, spell_advisor prompts
├── tests/
│   ├── __init__.py
│   ├── test_mtg_tools.py
│   └── test_dnd_tools.py
├── pyproject.toml
├── Makefile
└── README.md
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────┐
│                 FastMCP Server                   │
│                  (server.py)                     │
│                                                  │
│  ┌──────────────┐       ┌──────────────────┐    │
│  │   mtg/       │       │   dnd/           │    │
│  │  tools.py    │       │  tools.py        │    │
│  │  resources.py│       │  resources.py    │    │
│  │  prompts.py  │       │  prompts.py      │    │
│  └──────┬───────┘       └────────┬─────────┘    │
│         │                        │               │
│  ┌──────▼───────┐       ┌───────▼──────────┐    │
│  │ScyrfallClient│       │   DndClient      │    │
│  │  (httpx)     │       │   (httpx)        │    │
│  └──────┬───────┘       └───────┬──────────┘    │
└─────────┼───────────────────────┼────────────────┘
          │                       │
          ▼                       ▼
   api.scryfall.com      www.dnd5eapi.co
```

---

## Tool, Resource & Prompt Catalog

### MTG (Scryfall API)

#### Tools

| Name | Input | Description |
|---|---|---|
| `search_cards` | `query: str`, `color?: str`, `type?: str`, `format?: str` | Search cards via Scryfall search syntax |
| `random_card` | `color?: str`, `type?: str` | Return a random card with optional filters |
| `build_deck` | `colors: str`, `strategy: str`, `format: str` | Search synergistic cards and build a deck (60 or 100 for Commander) |

#### Resources

| URI | Description |
|---|---|
| `mtg://formats` | List available formats (Standard, Modern, Commander, Pioneer, Legacy, Vintage, Pauper) |

#### Prompts

| Name | Arguments | Description |
|---|---|---|
| `deck_builder` | `colors`, `strategy`, `format` | Template that guides the LLM to build a complete deck with reasoning |

### D&D 5e (dnd5eapi.co)

#### Tools

| Name | Input | Description |
|---|---|---|
| `search_monsters` | `name?: str`, `challenge_rating?: float` | Search monsters by name or challenge rating |
| `search_spells` | `name?: str`, `level?: int`, `class_name?: str` | Search spells with combined filters |
| `get_class_info` | `class_name: str` | Full details of a class (features, proficiencies, spellcasting) |
| `generate_encounter` | `party_level: int`, `party_size: int`, `difficulty: str` | Generate a balanced encounter with appropriate monsters |
| `recommend_spells` | `class_name: str`, `level: int`, `spell_type: str` | Recommend spells filtered by class, level, and type (attack, healing, utility, control) |
| `recommend_build` | `class_name: str`, `level: int`, `playstyle: str` | Recommend a full build: spells + equipment + feats + strategy |

#### Resources

| URI | Description |
|---|---|
| `dnd://classes` | List all 12 available classes with summary |

#### Prompts

| Name | Arguments | Description |
|---|---|---|
| `encounter_planner` | `party_level`, `party_size`, `theme` | Template for planning a themed combat session |
| `spell_advisor` | `class_name`, `level` | Template for the LLM to interactively guide spell selection |

---

## HTTP Clients

### ScyrfallClient

```python
# Required headers
headers = {"User-Agent": "NerdToolkitMCP/1.0", "Accept": "application/json"}

# Endpoints:
# GET /cards/search?q={query}   -> search_cards, build_deck
# GET /cards/random?q={query}   -> random_card
```

- Rate limit: 100ms delay between requests (Scryfall requirement)
- Search syntax built programmatically (e.g., `c:red t:creature f:standard`)

### DndClient

```python
# Base URL: https://www.dnd5eapi.co/api

# Endpoints:
# GET /spells/{index}                -> spell details
# GET /classes/{index}               -> class details
# GET /classes/{index}/spells        -> spells by class
# GET /monsters/{index}              -> monster details
# GET /monsters?challenge_rating={cr} -> monsters by CR
# GET /classes                       -> class list
```

- In-memory cache for static data (classes, spell lists)
- For `recommend_spells`: fetch class spells, enrich with details, filter by level and school
- For `recommend_build`: combine class data + spells + features by level

### Resilience

- **Timeout**: 10s per request
- **Exponential backoff**: 3 retries, base 1s, max 10s, factor 2x
- **Friendly errors**: human-readable message for the LLM on failure

---

## Transport

The server supports both transports via CLI argument:

```python
# stdio (default) — for Claude Desktop / Claude Code
python -m nerd_toolkit.server

# streamable-http — standalone HTTP server
python -m nerd_toolkit.server streamable-http
```

---

## Best Practices

### Structured Logging
- Uses `ctx.info()` and `ctx.debug()` from MCP SDK inside tools
- Logs in HTTP clients for each request/response
- Log level configurable via env var

### Docstrings
- All tools have descriptive docstrings — FastMCP uses them to generate the description
  the LLM sees. Clear docstrings = LLM uses tools more effectively.

### Pydantic Validation
- Tool inputs validated (e.g., `level` between 1-20, `difficulty` in easy/medium/hard/deadly)
- HTTP client responses typed with Pydantic models

### Configuration via Env Vars
- `pydantic-settings` for configuration management
- Timeouts, base URLs, log level are all configurable
- Sensible defaults to work out-of-the-box

### Testing
- **pytest** as the framework
- **respx** for mocking httpx calls (no real API hits)
- Tests per domain: `test_mtg_tools.py`, `test_dnd_tools.py`

### Linting and Type Checking
- **ruff** for linting + formatting (replaces flake8/isort/black)
- **mypy** for static type checking

### Developer Experience
- **Makefile** with targets: `make dev`, `make test`, `make lint`, `make typecheck`
- **MCP Inspector** for interactive testing: `npx @modelcontextprotocol/inspector`

---

## External APIs

| API | URL | Auth | Rate Limit |
|---|---|---|---|
| Scryfall | api.scryfall.com | None (requires User-Agent) | ~10 req/s |
| D&D 5e | www.dnd5eapi.co/api | None | No limit |

---

## Out of Scope (YAGNI)

- Docker / containerization
- CI/CD pipeline
- Server-side rate limiter
- MCP server authentication
- Persistent cache (Redis, SQLite)
- Cloud deployment
