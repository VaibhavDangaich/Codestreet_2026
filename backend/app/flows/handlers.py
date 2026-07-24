"""The three end-to-end resolution flows.

Each flow: reads member state -> checks policy (logged) -> either executes the
backend change (logged) or escalates with a context summary. Every branch writes
to the audit chain so the trail is complete regardless of outcome.
"""
from __future__ import annotations

from typing import Any

from app.audit.chain import AUDIT
from app.config import now_iso
from app.mock_backend import card_system as cards
from app.models.schemas import Intent, Resolution
from app.policies.policy import POLICY


def _log(session_id: str, member_id: str, actor: str, action: str,
         payload: dict[str, Any]):
    return AUDIT.append(ts=now_iso(), session_id=session_id, member_id=member_id,
                        actor=actor, action=action, payload=payload)


def _escalate(session_id: str, member_id: str, intent: Intent, reason: str,
              context: dict) -> Resolution:
    summary = (f"Escalating {intent.value} for {member_id}: {reason}. "
               f"Context: {context}")
    _log(session_id, member_id, "agent", "escalate_to_human",
         {"intent": intent.value, "reason": reason, "context": context})
    return Resolution(
        status="escalated", intent=intent,
        message=("I can't auto-approve this one, so I'm connecting you to a "
                 "specialist who already has your full context — you won't need "
                 "to repeat anything."),
        escalation_summary=summary, details={"reason": reason, **context},
    )


# --- 1. Fee reversal -------------------------------------------------------
def handle_fee_reversal(session_id, member_id, fields) -> Resolution:
    m = cards.get_member(member_id)
    fee = next((f for f in m.fees if not f.reversed), None)
    if fee is None:
        _log(session_id, member_id, "policy", "no_reversible_fee", {})
        return Resolution(status="rejected", intent=Intent.FEE_REVERSAL,
                          message="I don't see any reversible fee on the account.")

    checks = {
        "fee_amount": fee.amount,
        "auto_approve_max": POLICY.fee_auto_approve_max,
        "reversals_used": m.fee_reversals_used,
        "reversals_allowed": POLICY.fee_reversals_per_year,
    }
    _log(session_id, member_id, "policy", "evaluate_fee_reversal", checks)

    if fee.amount > POLICY.fee_auto_approve_max:
        return _escalate(session_id, member_id, Intent.FEE_REVERSAL,
                         f"fee ${fee.amount} exceeds auto-approve cap "
                         f"${POLICY.fee_auto_approve_max}", checks)
    if m.fee_reversals_used >= POLICY.fee_reversals_per_year:
        return _escalate(session_id, member_id, Intent.FEE_REVERSAL,
                         "annual reversal limit reached", checks)

    result = cards.reverse_fee(member_id, fee.fee_id)
    _log(session_id, member_id, "backend", "reverse_fee_executed", result)
    return Resolution(
        status="resolved", intent=Intent.FEE_REVERSAL,
        message=(f"Done — I've reversed the ${fee.amount:.0f} {fee.kind.replace('_',' ')}. "
                 f"You'll see the credit on your next statement."),
        details=result,
    )


# --- 2. Credit limit increase ---------------------------------------------
def handle_limit_increase(session_id, member_id, fields) -> Resolution:
    m = cards.get_member(member_id)
    requested = fields.get("amount")
    # If member gave a target, treat as desired new limit; else default bump 20%.
    if requested:
        new_limit = float(requested)
        increase = new_limit - m.credit_limit
    else:
        increase = round(m.credit_limit * 0.20, 2)
        new_limit = m.credit_limit + increase

    cap_abs = POLICY.limit_increase_abs_max
    cap_pct = POLICY.limit_increase_pct_max * m.credit_limit
    checks = {
        "current_limit": m.credit_limit, "requested_new_limit": new_limit,
        "increase": increase, "abs_cap": cap_abs, "pct_cap": cap_pct,
        "good_standing": m.good_standing,
    }
    _log(session_id, member_id, "policy", "evaluate_limit_increase", checks)

    if not m.good_standing:
        return _escalate(session_id, member_id, Intent.LIMIT_INCREASE,
                         "account not in good standing", checks)
    if increase <= 0:
        return Resolution(status="needs_info", intent=Intent.LIMIT_INCREASE,
                          message="What new credit limit are you hoping for?")
    if increase > cap_abs or increase > cap_pct:
        return _escalate(session_id, member_id, Intent.LIMIT_INCREASE,
                         f"increase ${increase:.0f} exceeds auto-approve caps "
                         f"(abs ${cap_abs:.0f}, 30% ${cap_pct:.0f})", checks)

    result = cards.set_credit_limit(member_id, new_limit)
    _log(session_id, member_id, "backend", "set_credit_limit_executed", result)
    return Resolution(
        status="resolved", intent=Intent.LIMIT_INCREASE,
        message=(f"Approved — your credit limit is now ${new_limit:,.0f} "
                 f"(up from ${result['old_limit']:,.0f}), effective immediately."),
        details=result,
    )


# --- 3. Card replacement ---------------------------------------------------
def handle_card_replacement(session_id, member_id, fields) -> Resolution:
    lost_or_stolen = bool(fields.get("lost_or_stolen", False))
    reason = fields.get("reason", "damaged" if not lost_or_stolen else "lost/stolen")
    _log(session_id, member_id, "policy", "evaluate_card_replacement",
         {"lost_or_stolen": lost_or_stolen, "reason": reason})

    if lost_or_stolen:
        block = cards.block_card(member_id)
        _log(session_id, member_id, "backend", "block_card_executed", block)

    result = cards.order_replacement(member_id, reason)
    _log(session_id, member_id, "backend", "order_replacement_executed", result)
    blocked_note = (" I've also frozen the old card so it can't be used."
                    if lost_or_stolen else "")
    return Resolution(
        status="resolved", intent=Intent.CARD_REPLACEMENT,
        message=(f"Your replacement card is on the way — arriving in "
                 f"~{result['eta_days']} days (tracking {result['tracking']})."
                 f"{blocked_note}"),
        details=result,
    )


DISPATCH = {
    Intent.FEE_REVERSAL: handle_fee_reversal,
    Intent.LIMIT_INCREASE: handle_limit_increase,
    Intent.CARD_REPLACEMENT: handle_card_replacement,
}
