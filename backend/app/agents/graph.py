"""LangGraph orchestration.

Flow:  classify -> route
         route -> (fee | limit | card) handler        [confident + known intent]
         route -> clarify/escalate                     [low confidence or unknown]

The graph is intentionally small and explicit so every transition can be
narrated in the audit trail and drawn on a slide. State is a TypedDict.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.assistant import assist
from app.agents.classifier import classify
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


def _log(state, actor, action, payload):
    AUDIT.append(ts=now_iso(), session_id=state["session_id"],
                 member_id=state["member_id"], actor=actor,
                 action=action, payload=payload)


def node_classify(state: AgentState) -> AgentState:
    _log(state, "system", "request_received", {"message": state["message"]})
    c = classify(state["message"])
    _log(state, "classifier", "intent_classified",
         {"intent": c.intent.value, "confidence": c.confidence,
          "fields": c.extracted_fields, "rationale": c.rationale})
    return {"classification": c}


def _route(state: AgentState) -> str:
    c = state["classification"]
    if c.intent == Intent.UNKNOWN or c.confidence < CONFIDENCE_THRESHOLD:
        return "handle_uncertain"
    return c.intent.value


def node_uncertain(state: AgentState) -> AgentState:
    c = state["classification"]
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
        res = DISPATCH[intent](state["session_id"], state["member_id"],
                               c.extracted_fields)
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


def run_agent(member_id: str, message: str, session_id: str = "default") -> AgentState:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    state: AgentState = {"session_id": session_id, "member_id": member_id,
                         "message": message}
    return _GRAPH.invoke(state)
