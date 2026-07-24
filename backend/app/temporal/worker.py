"""Temporal worker: hosts the CardMonitorWorkflow + scan activity.

Run (with the backend already up):
    scripts/run_worker.sh
It connects to a local Temporal dev server (localhost:7233).
"""
from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.activities import scan_tick
from app.temporal.workflows import CardMonitorWorkflow

TASK_QUEUE = "card-monitor"
TEMPORAL_ADDR = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")


async def main() -> None:
    client = await Client.connect(TEMPORAL_ADDR)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CardMonitorWorkflow],
        activities=[scan_tick],
    )
    print(f"[worker] connected to {TEMPORAL_ADDR}, task queue '{TASK_QUEUE}' — running")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
