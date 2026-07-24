"""LangGraph orchestration.

Flow:  classify -> route
         route -> (fee | limit | card) handler        [confident + known intent]
         route -> clarify/escalate                     [low confidence or unknown]

The graph is intentionally small and explicit so every transition can be
narrated in the audit trail and drawn on a slide. State is a TypedDict.
"""
from __future__ import annotations

import re
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.assistant import assist
from app.agents.classifier import classify
from app.agents.verifier import Verdict, verify
from app.audit.chain import AUDIT
from app.config import CONFIDENCE_THRESHOLD, now_iso
from app.flows.handlers import DISPATCH, _escalate
from app.models.schemas import Classification, Intent, Resolution


class AgentState(TypedDict, total=False):
    session_id: str
    member_id: str
    message: str
    classification: Classification
    resolution: Resolution
    verified: bool
    verify_reason: str


def _log(state, actor, action, payload):
    AUDIT.append(ts=now_iso(), session_id=state["session_id"],
                 member_id=state["member_id"], actor=actor,
                 action=action, payload=payload)


def _classify_and_verify(message: str):
    """Propose -> verify -> (revise) loop. A second agent must agree the
    interpretation matches the request; on disagreement the proposer re-reads
    with the reviewer's note, bounded to 2 attempts.

    Risk-based: we only spend the second agent on money-moving (limit increase)
    or low-confidence proposals — high-confidence fee/card requests skip it."""
    c = classify(message)
    risky = c.intent == Intent.LIMIT_INCREASE or c.confidence < 0.85
    if not risky:
        return c, Verdict(agree=True,
                          reason="low-risk, high-confidence — second-agent check not required"), 0
    v = verify(message, c.intent.value, c.extracted_fields)
    attempts = 1
    while not v.agree and attempts < 2:
        c = classify(f"{message}\n[Reviewer flagged: {v.reason}. Re-read carefully.]")
        v = verify(message, c.intent.value, c.extracted_fields)
        attempts += 1
    return c, v, attempts


def node_classify(state: AgentState) -> AgentState:
    _log(state, "system", "request_received", {"message": state["message"]})
    c, v, attempts = _classify_and_verify(state["message"])
    _log(state, "classifier", "intent_classified",
         {"intent": c.intent.value, "confidence": c.confidence,
          "fields": c.extracted_fields, "rationale": c.rationale})
    _log(state, "verifier", "verification",
         {"agree": v.agree, "reason": v.reason, "attempts": attempts})
    return {"classification": c, "verified": v.agree, "verify_reason": v.reason}


def _route(state: AgentState) -> str:
    c = state["classification"]
    if not state.get("verified", True):
        return "handle_uncertain"
    if c.intent == Intent.UNKNOWN or c.confidence < CONFIDENCE_THRESHOLD:
        return "handle_uncertain"
    return c.intent.value


def node_uncertain(state: AgentState) -> AgentState:
    c = state["classification"]
    # Verifier disagreed on a known intent -> don't act; get a human.
    if not state.get("verified", True) and c.intent != Intent.UNKNOWN:
        _log(state, "verifier", "verification_failed_escalate",
             {"intent": c.intent.value, "reason": state.get("verify_reason")})
        res = _escalate(
            state["session_id"], state["member_id"], c.intent,
            f"verifier could not confirm this maps to the request "
            f"({state.get('verify_reason')})",
            {"message": state["message"]},
            message=("Let me get a second pair of eyes on this before I act — "
                     "I'm routing it to a specialist to be safe."))
        return {"resolution": res}
    _log(state, "policy", "low_confidence_or_unknown",
         {"intent": c.intent.value, "confidence": c.confidence,
          "threshold": CONFIDENCE_THRESHOLD})
    if c.intent == Intent.UNKNOWN:
        # Not a rigid menu: let the assistant inform, escalate, or clarify —
        # but never *act* on the account (actions stay scoped to the 3 intents).
        a = assist(state["message"])
        _log(state, "agent", "assist", {"kind": a.kind})
        if a.kind == "escalate":
            res = _escalate(state["session_id"], state["member_id"],
                            Intent.UNKNOWN, "out-of-scope servicing request",
                            {"message": state["message"]})
            res.message = a.message
            if a.escalation_summary:
                res.escalation_summary = a.escalation_summary
        elif a.kind == "info":
            res = Resolution(status="answered", intent=Intent.UNKNOWN,
                             message=a.message)
        else:  # clarify
            res = Resolution(status="needs_info", intent=Intent.UNKNOWN,
                             message=a.message)
    else:
        res = _escalate(state["session_id"], state["member_id"], c.intent,
                        f"classifier confidence {c.confidence:.2f} below "
                        f"threshold {CONFIDENCE_THRESHOLD}",
                        {"message": state["message"]})
    return {"resolution": res}


def _make_handler_node(intent: Intent):
    def node(state: AgentState) -> AgentState:
        c = state["classification"]
        fields = dict(c.extracted_fields)
        # Robustly recover a target amount from the message if the classifier
        # didn't surface one (needed for limit-increase decisions).
        if intent == Intent.LIMIT_INCREASE and not (
                fields.get("new_limit") or fields.get("amount")):
            amt = _extract_amount(state["message"])
            if amt is not None:
                fields["new_limit"] = amt
        res = DISPATCH[intent](state["session_id"], state["member_id"], fields)
        _log(state, "agent", "resolution_emitted",
             {"status": res.status, "intent": intent.value})
        return {"resolution": res}
    return node


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("classify", node_classify)
    g.add_node("handle_uncertain", node_uncertain)
    for intent in (Intent.FEE_REVERSAL, Intent.LIMIT_INCREASE, Intent.CARD_REPLACEMENT):
        g.add_node(intent.value, _make_handler_node(intent))

    g.set_entry_point("classify")
    g.add_conditional_edges("classify", _route, {
        Intent.FEE_REVERSAL.value: Intent.FEE_REVERSAL.value,
        Intent.LIMIT_INCREASE.value: Intent.LIMIT_INCREASE.value,
        Intent.CARD_REPLACEMENT.value: Intent.CARD_REPLACEMENT.value,
        "handle_uncertain": "handle_uncertain",
    })
    for name in ("handle_uncertain", Intent.FEE_REVERSAL.value,
                 Intent.LIMIT_INCREASE.value, Intent.CARD_REPLACEMENT.value):
        g.add_edge(name, END)
    return g.compile()


_GRAPH = None

# --- lightweight per-session memory for multi-turn follow-ups ---------------
# session_id -> {"history": [...], "pending": {...} | None}
SESSIONS: dict[str, dict] = {}

_AMOUNT_RE = re.compile(r"\$?\s*([\d][\d,]*(?:\.\d+)?)\s*(k|thousand)?", re.I)


def _extract_amount(text: str) -> Optional[float]:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    if m.group(2):
        val *= 1000
    return val


def _session(session_id: str) -> dict:
    return SESSIONS.setdefault(session_id, {"history": [], "pending": None})


def _base_state(member_id, session_id, message) -> AgentState:
    return {"session_id": session_id, "member_id": member_id, "message": message}


def run_agent(member_id: str, message: str, session_id: str = "default") -> AgentState:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()

    sess = _session(session_id)
    sess["history"].append({"role": "user", "text": message})
    pending = sess.get("pending")

    # 1) If we're waiting on a slot from a previous turn, try to fill it.
    if pending and pending.get("slot") == "new_limit":
        amount = _extract_amount(message)
        if amount is not None:
            _log(_base_state(member_id, session_id, message), "agent",
                 "followup_slot_filled", {"slot": "new_limit", "value": amount})
            res = DISPATCH[Intent.LIMIT_INCREASE](
                session_id, member_id, {"new_limit": amount})
            sess["pending"] = (
                {"slot": "new_limit"} if res.status == "needs_info" else None)
            sess["history"].append({"role": "agent", "text": res.message})
            return {**_base_state(member_id, session_id, message),
                    "resolution": res}
        # not an amount -> user likely changed topic; fall through to classify
        sess["pending"] = None

    # 2) Normal turn through the graph.
    state = _GRAPH.invoke(_base_state(member_id, session_id, message))
    res = state.get("resolution")

    # 3) Remember if the agent asked a follow-up question, so the next message
    #    is interpreted as the answer.
    if res is not None and res.status == "needs_info":
        if res.intent == Intent.LIMIT_INCREASE:
            sess["pending"] = {"slot": "new_limit"}
        else:
            sess["pending"] = {"slot": "reclassify"}
    else:
        sess["pending"] = None
    if res is not None:
        sess["history"].append({"role": "agent", "text": res.message})
    return state
