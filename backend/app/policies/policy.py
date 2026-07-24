"""Servicing policy limits — the guardrails the agent must stay within.

Kept as plain data so the audit trail can record exactly which rule fired.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    # Fee reversal: auto-approve at or under this amount; above -> human.
    fee_auto_approve_max: float = 50.0
    # A member may only get this many auto fee reversals per rolling window.
    fee_reversals_per_year: int = 2

    # Credit limit increase: auto-approve increases up to this absolute amount
    # AND up to this multiple of current limit; anything larger -> human.
    limit_increase_abs_max: float = 5000.0
    limit_increase_pct_max: float = 0.30  # 30% of current limit
    # Account must be in good standing (no delinquency) to auto-approve.

    # Card replacement: always auto-approved, but lost/stolen forces the old
    # card to be blocked first (fraud-sensitive path).
    card_replacement_fee: float = 0.0


POLICY = Policy()
