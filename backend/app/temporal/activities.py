"""Temporal activities — the side-effecting steps.

Activities run OUTSIDE the workflow sandbox, so real I/O (HTTP) is allowed here.
The scan activity calls the FastAPI backend, which owns the card state + audit
chain, keeping a single source of truth.
"""
from __future__ import annotations

import os

import httpx
from temporalio import activity

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")


@activity.defn
async def scan_tick() -> dict:
    """One monitoring pass across all members via the backend."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BACKEND}/monitor/tick")
        r.raise_for_status()
        data = r.json()
    if data.get("count"):
        activity.logger.info(f"Autonomous actions taken: {data['count']}")
    return data
