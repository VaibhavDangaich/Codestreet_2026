#!/usr/bin/env bash
# Local Temporal dev server (in-memory). UI at http://localhost:8233
set -euo pipefail
exec temporal server start-dev --ui-port 8233
