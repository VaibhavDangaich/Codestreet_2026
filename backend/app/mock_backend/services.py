"""Atomic 'services' a servicing saga orchestrates, each with a compensation.

These stand in for real downstream systems (card platform, ledger, fulfillment,
bureau). Every forward action has an inverse so a Temporal saga can roll back
cleanly if a later step fails — no partial financial state.

Each action: (member_id, params) -> {"ok": bool, ...}. Returning ok=False (or
raising) is what triggers compensation upstream.
"""
from __future__ import annotations

from typing import Any

from app.mock_backend import card_system as cards

# --- lightweight side-effect stores (demo) ---------------------------------
_prev_card_status: dict[str, str] = {}
_prev_limit: dict[str, float] = {}
_reserved: dict[str, float] = {}
_fulfillment: dict[str, dict] = {}
LEDGER: list[dict] = []


def _post(member_id: str, kind: str, amount: float = 0.0, **extra):
    entry = {"member": member_id, "type": kind, "amount": amount, **extra}
    LEDGER.append(entry)
    return entry


# --- card ------------------------------------------------------------------
def block_old_card(member_id: str, p: dict) -> dict:
    m = cards.get_member(member_id)
    _prev_card_status[member_id] = m.card_status
    m.card_status = "blocked"
    return {"ok": True, "card_status": "blocked"}


def unblock_card(member_id: str, p: dict) -> dict:
    m = cards.get_member(member_id)
    m.card_status = _prev_card_status.get(member_id, "active")
    return {"ok": True, "card_status": m.card_status}


# --- fees / credits (ledger) ----------------------------------------------
def charge_fee(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _post(member_id, "fee_charge", amt)
    return {"ok": True, "charged": amt}


def refund_fee(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _post(member_id, "fee_refund", -amt)
    return {"ok": True, "refunded": amt}


def apply_credit(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _post(member_id, "statement_credit", -amt)
    return {"ok": True, "credited": amt}


def reverse_credit(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _post(member_id, "statement_credit_reversal", amt)
    return {"ok": True, "reversed": amt}


# --- credit line -----------------------------------------------------------
def reserve_line(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _reserved[member_id] = _reserved.get(member_id, 0.0) + amt
    return {"ok": True, "reserved": amt, "total_reserved": _reserved[member_id]}


def release_line(member_id: str, p: dict) -> dict:
    amt = float(p.get("amount", 0))
    _reserved[member_id] = max(0.0, _reserved.get(member_id, 0.0) - amt)
    return {"ok": True, "released": amt}


def apply_new_limit(member_id: str, p: dict) -> dict:
    m = cards.get_member(member_id)
    _prev_limit[member_id] = m.credit_limit
    m.credit_limit = float(p["new_limit"])
    return {"ok": True, "old_limit": _prev_limit[member_id], "new_limit": m.credit_limit}


def revert_limit(member_id: str, p: dict) -> dict:
    m = cards.get_member(member_id)
    if member_id in _prev_limit:
        m.credit_limit = _prev_limit[member_id]
    return {"ok": True, "restored_limit": m.credit_limit}


def post_ledger(member_id: str, p: dict) -> dict:
    _post(member_id, "ledger_post", detail=p.get("detail", ""))
    return {"ok": True}


def reverse_ledger(member_id: str, p: dict) -> dict:
    _post(member_id, "ledger_reverse", detail=p.get("detail", ""))
    return {"ok": True}


# --- fulfillment (the step we deliberately let fail in the demo) -----------
def order_fulfillment(member_id: str, p: dict) -> dict:
    if p.get("force_fail"):
        return {"ok": False, "error": "fulfillment_provider_timeout"}
    _fulfillment[member_id] = {"status": "ordered", "tracking": f"TRK-{member_id[-4:]}"}
    return {"ok": True, **_fulfillment[member_id]}


def cancel_fulfillment(member_id: str, p: dict) -> dict:
    _fulfillment.pop(member_id, None)
    return {"ok": True, "cancelled": True}


# --- notification ----------------------------------------------------------
def send_confirmation(member_id: str, p: dict) -> dict:
    return {"ok": True, "notified": True}


ACTIONS = {
    "block_old_card": block_old_card, "unblock_card": unblock_card,
    "charge_fee": charge_fee, "refund_fee": refund_fee,
    "apply_credit": apply_credit, "reverse_credit": reverse_credit,
    "reserve_line": reserve_line, "release_line": release_line,
    "apply_new_limit": apply_new_limit, "revert_limit": revert_limit,
    "post_ledger": post_ledger, "reverse_ledger": reverse_ledger,
    "order_fulfillment": order_fulfillment, "cancel_fulfillment": cancel_fulfillment,
    "send_confirmation": send_confirmation,
}


def perform(action: str, member_id: str, params: dict[str, Any] | None) -> dict:
    fn = ACTIONS.get(action)
    if fn is None:
        return {"ok": False, "error": f"unknown_action:{action}"}
    return fn(member_id, params or {})
