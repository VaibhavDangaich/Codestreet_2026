#!/usr/bin/env bash
# Backend runs from the SSD source, but its venv lives on the internal disk
# (exFAT can't host a uv venv reliably). These exports point uv at that venv.
set -euo pipefail
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/cs2026-backend"
export UV_LINK_MODE=copy
cd "$(dirname "$0")/../backend"
exec uv run uvicorn app.main:app --port 8010 --reload
