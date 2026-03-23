.PHONY: dev test lint typecheck format install

install:
	uv sync --all-groups

dev:
	uv run python -m nerd_toolkit.server

dev-http:
	uv run python -m nerd_toolkit.server streamable-http

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

inspect:
	npx -y @modelcontextprotocol/inspector
