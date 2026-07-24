"""A mocked Amex-style card backend.

In production these would be real core-banking API calls. Here we keep an
in-memory member store so the agent can execute *real* state changes that the
demo (and the audit trail) can show before/after.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Fee:
    fee_id: str
    kind: str            # "late_fee", "annual_fee", ...
    amount: float
    reversed: bool = False


@dataclass
class Member:
    member_id: str
    name: str
    credit_limit: float
    good_standing: bool
    fee_reversals_used: int = 0
    fees: list[Fee] = field(default_factory=list)
    card_status: str = "active"        # active | blocked | replaced
    recent_transactions: list[dict] = field(default_factory=list)


# --- seed data used by the demo -------------------------------------------
_MEMBERS: dict[str, Member] = {
    "M-1001": Member(
        member_id="M-1001",
        name="Priya Sharma",
        credit_limit=10000.0,
        good_standing=True,
        fees=[Fee(fee_id="F-9001", kind="late_fee", amount=39.0)],
        recent_transactions=[
            {"id": "T-1", "merchant": "Blue Bottle Coffee", "amount": 6.5, "city": "SF"},
            {"id": "T-2", "merchant": "Whole Foods", "amount": 82.1, "city": "SF"},
        ],
    ),
    "M-2002": Member(
        member_id="M-2002",
        name="Alex Chen",
        credit_limit=4000.0,
        good_standing=False,   # delinquent -> limit increases won't auto-approve
        fees=[Fee(fee_id="F-9002", kind="late_fee", amount=39.0)],
    ),
}


def get_member(member_id: str) -> Member:
    m = _MEMBERS.get(member_id)
    if m is None:
        raise KeyError(f"Unknown member {member_id}")
    return m


def snapshot(member_id: str) -> dict:
    return asdict(get_member(member_id))


# --- operations the agent can execute -------------------------------------
def reverse_fee(member_id: str, fee_id: Optional[str] = None) -> dict:
    m = get_member(member_id)
    fee = None
    if fee_id:
        fee = next((f for f in m.fees if f.fee_id == fee_id), None)
    if fee is None:
        fee = next((f for f in m.fees if not f.reversed), None)
    if fee is None:
        return {"ok": False, "reason": "no_reversible_fee"}
    fee.reversed = True
    m.fee_reversals_used += 1
    return {"ok": True, "fee_id": fee.fee_id, "amount": fee.amount,
            "reversals_used": m.fee_reversals_used}


def set_credit_limit(member_id: str, new_limit: float) -> dict:
    m = get_member(member_id)
    old = m.credit_limit
    m.credit_limit = new_limit
    return {"ok": True, "old_limit": old, "new_limit": new_limit}


def block_card(member_id: str) -> dict:
    m = get_member(member_id)
    m.card_status = "blocked"
    return {"ok": True, "card_status": m.card_status}


def order_replacement(member_id: str, reason: str) -> dict:
    m = get_member(member_id)
    m.card_status = "replaced"
    return {"ok": True, "reason": reason, "eta_days": 3,
            "tracking": f"TRK-{member_id[-4:]}-NEW"}
