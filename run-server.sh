#!/usr/bin/env bash
# Wrapper to run the Nerd Toolkit MCP server with the correct uv path
set -e
UV="/home/edson/snap/code/230/.local/share/mise/installs/uv/0.10.12/uv-x86_64-unknown-linux-musl/uv"
cd "$(dirname "$0")"
unset VIRTUAL_ENV
exec "$UV" run mcp run src/nerd_toolkit/server.py:mcp
