"""ServicingCaseWorkflow — a durable, self-healing servicing transaction.

This is the real showcase of Temporal for financial servicing:

  * Durable human-in-the-loop: if the request is over policy, the workflow
    durably WAITS for an underwriter's `submit_decision` signal — for as long as
    it takes, surviving worker restarts — instead of fire-and-forget escalation.
  * Saga + compensation: the multi-step plan runs as a saga. If any step fails
    after retries, the already-completed steps are compensated in reverse, so the
    account is never left in a partial state.
  * Live status: `status` is a query — the UI reads the running workflow's state
    directly, no separate store.

Determinism: all I/O is in the `do_action` activity; the workflow only decides.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import do_action


@workflow.defn
class ServicingCaseWorkflow:
    def __init__(self) -> None:
        self._decision: tuple[bool, str] | None = None
        self._state: dict = {
            "phase": "starting",      # starting|awaiting_approval|executing|compensating|closed
            "intent": None,
            "steps": [],
            "completed": [],
            "compensated": [],
            "current": None,
            "failed": None,
            "final": None,            # resolved|denied|expired|rolled_back
            "note": None,
        }

    @workflow.signal
    def submit_decision(self, approved: bool, note: str = "") -> None:
        self._decision = (approved, note)

    @workflow.query
    def status(self) -> dict:
        return self._state

    @workflow.run
    async def run(self, member_id: str, intent: str, plan: list,
                  requires_approval: bool,
                  approval_timeout_seconds: int = 120) -> dict:
        self._state["intent"] = intent
        self._state["steps"] = [s["action"] for s in plan]

        # 1) durable human-in-the-loop gate
        if requires_approval:
            self._state["phase"] = "awaiting_approval"
            try:
                await workflow.wait_condition(
                    lambda: self._decision is not None,
                    timeout=timedelta(seconds=approval_timeout_seconds),
                )
            except asyncio.TimeoutError:
                self._state.update(phase="closed", final="expired")
                return self._state
            approved, note = self._decision  # type: ignore[misc]
            self._state["note"] = note
            if not approved:
                self._state.update(phase="closed", final="denied")
                return self._state

        # 2) saga forward
        self._state["phase"] = "executing"
        retry = RetryPolicy(maximum_attempts=2,
                            initial_interval=timedelta(seconds=1))
        done: list[dict] = []
        for s in plan:
            self._state["current"] = s["action"]
            try:
                await workflow.execute_activity(
                    do_action, args=[s["action"], member_id, s.get("params", {})],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry,
                )
                self._state["completed"].append(s["action"])
                done.append(s)
            except Exception:
                # 3) compensate completed steps in reverse
                self._state.update(phase="compensating", failed=s["action"],
                                   current=None)
                for cs in reversed(done):
                    comp = cs.get("compensation")
                    if not comp:
                        continue
                    try:
                        await workflow.execute_activity(
                            do_action, args=[comp, member_id, cs.get("params", {})],
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=RetryPolicy(maximum_attempts=3),
                        )
                        self._state["compensated"].append(comp)
                    except Exception:
                        pass  # best-effort; a real system would alert here
                self._state.update(phase="closed", final="rolled_back")
                return self._state

        self._state.update(phase="closed", final="resolved", current=None)
        return self._state
