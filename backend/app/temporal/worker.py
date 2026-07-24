"""Temporal worker: hosts ServicingCaseWorkflow + the do_action activity.

Run (backend + temporal server already up):  scripts/run_worker.sh
"""
from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.activities import do_action
from app.temporal.client import TASK_QUEUE
from app.temporal.workflows import ServicingCaseWorkflow

TEMPORAL_ADDR = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")


async def main() -> None:
    client = await Client.connect(TEMPORAL_ADDR)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ServicingCaseWorkflow],
        activities=[do_action],
    )
    print(f"[worker] connected to {TEMPORAL_ADDR}, task queue '{TASK_QUEUE}' — running")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
