"""Temporal workflow — the durable 'sleeping agent'.

The workflow loops: run one scan activity, then sleep. Temporal turns that sleep
into a *durable timer* and records every step in the workflow's event history —
so the monitor survives worker restarts and its history is itself an audit of
when the agent woke and what it did. After a bounded number of iterations it
continues-as-new to keep history compact.

Determinism: no I/O here. All side effects go through the activity.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import scan_tick


@workflow.defn
class CardMonitorWorkflow:
    @workflow.run
    async def run(self, interval_seconds: int = 10,
                  iterations_before_continue: int = 60) -> None:
        for _ in range(iterations_before_continue):
            await workflow.execute_activity(
                scan_tick,
                start_to_close_timeout=timedelta(seconds=30),
            )
            # durable timer — the agent 'sleeps' here without holding resources
            await asyncio.sleep(interval_seconds)

        # keep event history small; carry settings forward
        workflow.continue_as_new(
            args=[interval_seconds, iterations_before_continue]
        )
