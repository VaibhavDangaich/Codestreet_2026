"""Autonomous card-activity monitoring.

This is the 'sleeping agent' brain. A durable Temporal workflow calls
`scan_and_act()` on a schedule; between calls the agent is idle. When an unusual
transaction appears, the agent acts on its own — freezes the card, raises an
alert, and writes the whole decision to the SAME hash-chained audit trail used by
the chat flows. No human trigger required.

Detection rules (deliberately simple + explainable for the demo):
  * amount >= HIGH_VALUE_THRESHOLD, or
  * transaction flagged foreign (card-not-present in an unusual geo).
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Optional

from app.mock_backend import card_system as cards

HIGH_VALUE_THRESHOLD = 2000.0

# transactions already assessed, so we don't re-alert every tick
_reviewed: dict[str, set[str]] = {}
# proactive alerts raised, newest first
_alerts: list[dict] = []


def inject_suspicious_transaction(member_id: str) -> dict:
    """Demo helper: drop an obviously-unusual charge onto the member's feed."""
    m = cards.get_member(member_id)
    txn = {
        "id": f"T-{uuid.uuid4().hex[:6]}",
        "merchant": "LuxeElectronics (card-not-present)",
        "amount": 4999.0,
        "city": "Lagos",
        "foreign": True,
    }
    m.recent_transactions.append(txn)
    return txn


def _is_suspicious(txn: dict) -> Optional[str]:
    if txn.get("amount", 0) >= HIGH_VALUE_THRESHOLD:
        return f"high-value charge ${txn['amount']:.0f} (>= ${HIGH_VALUE_THRESHOLD:.0f})"
    if txn.get("foreign"):
        return f"foreign card-not-present charge in {txn.get('city', 'unknown')}"
    return None


def scan_and_act(
    member_id: str,
    log_fn: Callable[..., Any],
    ts: str,
) -> list[dict]:
    """Assess unreviewed transactions; act + audit-log on anything suspicious.

    `log_fn(actor, action, payload)` appends to the shared audit chain.
    Returns the list of actions taken this tick (empty if nothing new).
    """
    m = cards.get_member(member_id)
    seen = _reviewed.setdefault(member_id, set())
    actions: list[dict] = []

    for txn in m.recent_transactions:
        tid = txn.get("id")
        if tid in seen:
            continue
        seen.add(tid)
        reason = _is_suspicious(txn)
        if not reason:
            continue

        # 1) log the detection decision
        log_fn("monitor", "anomaly_detected",
               {"txn": txn, "reason": reason})

        # 2) act autonomously: freeze the card (only if not already blocked)
        if m.card_status != "blocked":
            block = cards.block_card(member_id)
            log_fn("monitor", "auto_freeze_card", block)

        # 3) raise a member-facing alert
        alert = {
            "id": f"A-{uuid.uuid4().hex[:6]}",
            "member_id": member_id,
            "ts": ts,
            "reason": reason,
            "txn": txn,
            "action": "Card frozen automatically; confirm if this was you.",
        }
        _alerts.insert(0, alert)
        log_fn("monitor", "alert_raised", {"alert_id": alert["id"],
                                           "reason": reason})
        actions.append(alert)

    return actions


def scan_all(log_fn: Callable[..., Any], ts: str) -> list[dict]:
    out: list[dict] = []
    for member_id in cards._MEMBERS:
        out.extend(scan_and_act(member_id, log_fn, ts))
    return out


def get_alerts(member_id: Optional[str] = None) -> list[dict]:
    if member_id is None:
        return list(_alerts)
    return [a for a in _alerts if a["member_id"] == member_id]
