"""The three end-to-end resolution flows.

The LLM proposes (intent + amounts); the Policy-as-Code engine *decides* and
returns the exact rule that fired. Handlers execute only on an `approve`
decision; otherwise they escalate — with a counterfactual ("I can do $X now")
where the engine exposes a nearest-approvable figure. Every branch is audited
with the rule citation.
"""
from __future__ import annotations

from typing import Any, Optional

from app.audit.chain import AUDIT
from app.config import now_iso
from app.mock_backend import card_system as cards
from app.models.schemas import Intent, Resolution
from app.policy_engine.engine import DecisionContext, evaluate


def _log(session_id: str, member_id: str, actor: str, action: str,
         payload: dict[str, Any]):
    return AUDIT.append(ts=now_iso(), session_id=session_id, member_id=member_id,
                        actor=actor, action=action, payload=payload)


def _log_decision(session_id, member_id, decision, extra):
    _log(session_id, member_id, "policy", "policy_decision", {
        "outcome": decision.outcome, "rule_id": decision.rule_id,
        "rule_version": decision.rule_version, "reason": decision.reason,
        **extra})


def _escalate(session_id: str, member_id: str, intent: Intent, reason: str,
              context: dict, *, message: Optional[str] = None,
              citation: Optional[str] = None) -> Resolution:
    summary = (f"Escalating {intent.value} for {member_id}: {reason}."
               + (f" Policy: {citation}." if citation else "")
               + f" Context: {context}")
    _log(session_id, member_id, "agent", "escalate_to_human",
         {"intent": intent.value, "reason": reason, "citation": citation,
          "context": context})
    return Resolution(
        status="escalated", intent=intent,
        message=message or (
            "I can't auto-approve this one, so I'm connecting you to a specialist "
            "who already has your full context — you won't need to repeat anything."),
        escalation_summary=summary,
        details={"reason": reason, "citation": citation, **context},
    )


# --- 1. Fee reversal -------------------------------------------------------
def handle_fee_reversal(session_id, member_id, fields) -> Resolution:
    m = cards.get_member(member_id)
    fee = next((f for f in m.fees if not f.reversed), None)
    if fee is None:
        _log(session_id, member_id, "policy", "no_reversible_fee", {})
        return Resolution(status="rejected", intent=Intent.FEE_REVERSAL,
                          message="I don't see any reversible fee on the account.")

    d = evaluate(DecisionContext(intent="fee_reversal", member_id=member_id,
                                 fee_amount=fee.amount,
                                 reversals_used=m.fee_reversals_used))
    _log_decision(session_id, member_id, d, {"fee_amount": fee.amount})

    if d.outcome != "approve":
        return _escalate(session_id, member_id, Intent.FEE_REVERSAL, d.reason,
                         {"fee_amount": fee.amount}, citation=d.citation)

    result = cards.reverse_fee(member_id, fee.fee_id)
    _log(session_id, member_id, "backend", "reverse_fee_executed", result)
    return Resolution(
        status="resolved", intent=Intent.FEE_REVERSAL,
        message=(f"Done — I've reversed the ${fee.amount:.0f} "
                 f"{fee.kind.replace('_', ' ')} (auto-approved under policy "
                 f"{d.citation}). You'll see the credit on your next statement."),
        details={**result, "citation": d.citation},
    )


# --- 2. Credit limit increase ---------------------------------------------
def handle_limit_increase(session_id, member_id, fields) -> Resolution:
    m = cards.get_member(member_id)
    requested = fields.get("new_limit") or fields.get("amount")
    if not requested:  # slot-fill follow-up
        _log(session_id, member_id, "agent", "await_slot",
             {"intent": "limit_increase", "slot": "new_limit"})
        return Resolution(
            status="needs_info", intent=Intent.LIMIT_INCREASE,
            message=(f"Happy to help. Your current limit is ${m.credit_limit:,.0f}"
                     f" — what new limit would you like?"),
            details={"awaiting": "new_limit"})
    new_limit = float(requested)

    d = evaluate(DecisionContext(intent="limit_increase", member_id=member_id,
                                 current_limit=m.credit_limit,
                                 requested_new_limit=new_limit,
                                 good_standing=m.good_standing))
    _log_decision(session_id, member_id, d,
                  {"current_limit": m.credit_limit, "requested_new_limit": new_limit})

    if d.outcome == "approve":
        result = cards.set_credit_limit(member_id, new_limit)
        _log(session_id, member_id, "backend", "set_credit_limit_executed", result)
        return Resolution(
            status="resolved", intent=Intent.LIMIT_INCREASE,
            message=(f"Approved — your credit limit is now ${new_limit:,.0f} "
                     f"(up from ${result['old_limit']:,.0f}), effective immediately "
                     f"(policy {d.citation})."),
            details={**result, "citation": d.citation})

    # escalate — with a counterfactual if the engine exposes a nearest-approvable
    cf = ""
    max_nl = d.max_auto_approvable
    if max_nl and max_nl > m.credit_limit:
        cf = (f" I can auto-approve an increase up to ${max_nl:,.0f} right now — "
              f"want ${max_nl:,.0f} immediately, or shall I send the full "
              f"${new_limit:,.0f} request to an underwriter?")
    msg = (f"A ${new_limit:,.0f} limit needs underwriter review (policy "
           f"{d.citation}).{cf}")
    return _escalate(session_id, member_id, Intent.LIMIT_INCREASE, d.reason,
                     {"requested_new_limit": new_limit,
                      "max_auto_approvable": max_nl},
                     message=msg, citation=d.citation)


# --- 3. Card replacement ---------------------------------------------------
def handle_card_replacement(session_id, member_id, fields) -> Resolution:
    lost_or_stolen = bool(fields.get("lost_or_stolen", False))
    reason = fields.get("reason", "damaged" if not lost_or_stolen else "lost/stolen")
    d = evaluate(DecisionContext(intent="card_replacement", member_id=member_id,
                                 lost_or_stolen=lost_or_stolen))
    _log_decision(session_id, member_id, d, {"lost_or_stolen": lost_or_stolen,
                                             "reason": reason})

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
        details={**result, "citation": d.citation},
    )


DISPATCH = {
    Intent.FEE_REVERSAL: handle_fee_reversal,
    Intent.LIMIT_INCREASE: handle_limit_increase,
    Intent.CARD_REPLACEMENT: handle_card_replacement,
}
