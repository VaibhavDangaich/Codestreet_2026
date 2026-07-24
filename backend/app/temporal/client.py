"""Cached Temporal client + shared constants used by the FastAPI process."""
from __future__ import annotations

import os

from temporalio.client import Client

TASK_QUEUE = "servicing-cases"
TEMPORAL_ADDR = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")

_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(TEMPORAL_ADDR)
    return _client
