#!/usr/bin/env bash
# Kill any running claude-telegram server and restart it.
set -euo pipefail

echo "Stopping existing claude-telegram processes..."
pkill -f "claude-telegram launch" 2>/dev/null && echo "Killed." || echo "None running."

sleep 1

echo "Reinstalling package..."
uv pip install -e .

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting claude-telegram server..."
exec "$SCRIPT_DIR/.venv/bin/claude-telegram" launch "$@"
