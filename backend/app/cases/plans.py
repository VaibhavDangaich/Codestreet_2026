"""Build the multi-step saga plan for a servicing case.

A plan is an ordered list of steps; each step names a forward action and its
compensation (or None). The workflow executes them as a saga and, on failure,
runs the compensations of completed steps in reverse.

`requires_approval` decides whether the case must durably wait for a human
underwriter before the saga runs (over-policy amounts).
"""
from __future__ import annotations

from app.mock_backend.card_system import Member
from app.policies.policy import POLICY


def step(action: str, compensation: str | None, params: dict) -> dict:
    return {"action": action, "compensation": compensation, "params": params}


def build_plan(intent: str, member: Member, params: dict,
               force_fail: bool = False) -> tuple[list[dict], bool]:
    p = params or {}

    if intent == "card_replacement":
        fee = float(p.get("fee", 0))
        plan = [
            step("block_old_card", "unblock_card", {}),
            step("charge_fee", "refund_fee", {"amount": fee}),
            step("order_fulfillment", "cancel_fulfillment", {"force_fail": force_fail}),
            step("send_confirmation", None, {}),
        ]
        return plan, False

    if intent == "limit_increase":
        new_limit = float(p.get("new_limit", member.credit_limit * 1.2))
        increase = new_limit - member.credit_limit
        plan = [
            step("reserve_line", "release_line", {"amount": increase}),
            step("apply_new_limit", "revert_limit", {"new_limit": new_limit}),
            step("post_ledger", "reverse_ledger", {"detail": f"limit->{new_limit:.0f}"}),
            step("send_confirmation", None, {}),
        ]
        requires_approval = increase > POLICY.limit_increase_abs_max
        return plan, requires_approval

    if intent == "fee_reversal":
        amount = float(p.get("amount", 0))
        plan = [
            step("apply_credit", "reverse_credit", {"amount": amount}),
            step("send_confirmation", None, {}),
        ]
        requires_approval = amount > POLICY.fee_auto_approve_max
        return plan, requires_approval

    return [], False
