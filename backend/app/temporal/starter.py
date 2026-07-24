"""Start (or reuse) the durable card-monitor workflow.

Idempotent: if the monitor is already running, we just report its handle instead
of erroring. Run: scripts/start_monitor.sh
"""
from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from app.temporal.workflows import CardMonitorWorkflow

TASK_QUEUE = "card-monitor"
WORKFLOW_ID = "card-monitor-all"
TEMPORAL_ADDR = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL", "10"))


async def main() -> None:
    from temporalio.service import RPCError

    client = await Client.connect(TEMPORAL_ADDR)
    try:
        handle = await client.start_workflow(
            CardMonitorWorkflow.run,
            args=[INTERVAL_SECONDS, 60],
            id=WORKFLOW_ID,
            task_queue=TASK_QUEUE,
            id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
        )
        print(f"[starter] monitor STARTED: workflow_id={handle.id} "
              f"(scan every {INTERVAL_SECONDS}s)")
    except Exception as exc:  # already running -> reuse
        if "already" in str(exc).lower() or isinstance(exc, RPCError):
            print(f"[starter] monitor already running: workflow_id={WORKFLOW_ID}")
        else:
            raise
    print("Temporal UI: http://localhost:8233")


if __name__ == "__main__":
    asyncio.run(main())
