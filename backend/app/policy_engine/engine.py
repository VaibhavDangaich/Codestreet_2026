"""Policy-as-Code decision engine.

The LLM only *proposes* (intent + amounts). This engine *decides* — deterministically,
from versioned declarative rules — and returns the exact rule that fired. The model
has no authority over money; an auditable rule engine does. Every decision carries
`rule_id` + `rule_version` so the audit trail and analysts can cite it, and a
`max_auto_approvable` figure so we can offer a counterfactual ("I can do $X now").

To change policy you edit RULES (data) and bump a version — no agent code changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from app.policies.policy import POLICY


@dataclass
class DecisionContext:
    intent: str
    member_id: str
    fee_amount: float = 0.0
    reversals_used: int = 0
    current_limit: float = 0.0
    requested_new_limit: Optional[float] = None
    good_standing: bool = True
    lost_or_stolen: bool = False


@dataclass
class Rule:
    id: str
    version: str
    intent: str
    outcome: str              # approve | escalate | deny
    reason: str
    applies: Callable[[DecisionContext], bool]


@dataclass
class Decision:
    outcome: str              # approve | escalate | deny
    rule_id: str
    rule_version: str
    reason: str
    max_auto_approvable: Optional[float] = None   # counterfactual figure
    details: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"{self.rule_id} v{self.rule_version}"


def _limit_max_increase(c: DecisionContext) -> float:
    return min(POLICY.limit_increase_abs_max,
               POLICY.limit_increase_pct_max * c.current_limit)


# Rules are evaluated top-to-bottom; first match for the intent wins.
RULES: list[Rule] = [
    # --- fee reversal ---
    Rule("FEE-LIMIT", "1.0", "fee_reversal", "escalate",
         "Annual fee-reversal limit reached",
         lambda c: c.reversals_used >= POLICY.fee_reversals_per_year),
    Rule("FEE-AUTO", "1.2", "fee_reversal", "approve",
         "Fee within the auto-approve cap and reversal limit",
         lambda c: c.fee_amount <= POLICY.fee_auto_approve_max),
    Rule("FEE-CAP", "1.1", "fee_reversal", "escalate",
         "Fee exceeds the auto-approve cap",
         lambda c: c.fee_amount > POLICY.fee_auto_approve_max),
    # --- limit increase ---
    Rule("LIMIT-STANDING", "1.0", "limit_increase", "escalate",
         "Account not in good standing",
         lambda c: not c.good_standing),
    Rule("LIMIT-AUTO", "2.0", "limit_increase", "approve",
         "Increase within the auto-approve caps",
         lambda c: (c.requested_new_limit or 0) - c.current_limit
                   <= _limit_max_increase(c)),
    Rule("LIMIT-CAP", "1.1", "limit_increase", "escalate",
         "Increase exceeds the auto-approve caps",
         lambda c: True),
    # --- card replacement ---
    Rule("CARD-AUTO", "1.0", "card_replacement", "approve",
         "Card replacement is always auto-approved",
         lambda c: True),
]


def _max_auto_approvable(c: DecisionContext) -> Optional[float]:
    if c.intent == "fee_reversal":
        return POLICY.fee_auto_approve_max if (
            c.reversals_used < POLICY.fee_reversals_per_year) else 0.0
    if c.intent == "limit_increase" and c.good_standing:
        return round(c.current_limit + _limit_max_increase(c), 2)  # max new limit
    return None


def evaluate(ctx: DecisionContext) -> Decision:
    for r in RULES:
        if r.intent == ctx.intent and r.applies(ctx):
            return Decision(outcome=r.outcome, rule_id=r.id,
                            rule_version=r.version, reason=r.reason,
                            max_auto_approvable=_max_auto_approvable(ctx))
    return Decision("escalate", "NO-RULE", "1.0",
                    "No matching policy rule — routed to a human", None)
