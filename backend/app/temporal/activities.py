"""Temporal activities — side-effecting saga steps.

`do_action` calls the backend's /internal/action endpoint (the backend owns card
state + the audit chain). Returning ok=False raises, so Temporal retries and, if
still failing, the workflow triggers compensation.
"""
from __future__ import annotations

import os

import httpx
from temporalio import activity

BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8010")


@activity.defn
async def do_action(action: str, member_id: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BACKEND}/internal/action/{action}",
                              json={"member_id": member_id, "params": params})
        r.raise_for_status()
        data = r.json()
    if not data.get("ok"):
        # deliberate failure signal -> Temporal retry / saga compensation
        raise RuntimeError(data.get("error", f"action_failed:{action}"))
    return data
