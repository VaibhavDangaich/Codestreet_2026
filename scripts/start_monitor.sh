#!/usr/bin/env bash
# Kick off the durable card-monitor workflow (idempotent).
set -euo pipefail
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/cs2026-backend"
export UV_LINK_MODE=copy
cd "$(dirname "$0")/../backend"
exec uv run python -m app.temporal.starter
