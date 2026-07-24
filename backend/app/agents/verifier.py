"""Self-verifying agent — a second pair of eyes before we act.

An independent 'reviewer' LLM checks that the primary agent's interpretation
(intent + extracted amounts) faithfully represents what the member asked for and
is safe to act on. The orchestrator runs a bounded propose -> verify -> revise
loop: on disagreement the proposer re-reads (with the reviewer's note) and we
re-verify; if the two agents still can't agree, the request is escalated to a
human rather than acted on.

Fallbacks: with no LLM key, or on a transient error, verification passes (the
deterministic policy engine still governs every action) — a prototype choice; a
production build would fail-closed and escalate.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import llm_enabled

SYSTEM = """You are a compliance reviewer for a card-servicing agent.
Given the member's message and the system's interpretation (intent + extracted
fields), decide whether the interpretation FAITHFULLY represents what the member
asked for and is safe to act on.

Disagree if: the intent looks wrong, an amount was misread or invented, the
request is too ambiguous to act on, or acting would be risky/unauthorised.
Otherwise agree. Return `agree` (bool) and a one-sentence `reason`."""


class Verdict(BaseModel):
    agree: bool = Field(description="True if the interpretation faithfully matches the request.")
    reason: str = Field(description="One-sentence justification.")


_chain = None


def verify(message: str, intent: str, fields: dict) -> Verdict:
    global _chain
    if not llm_enabled():
        return Verdict(agree=True, reason="deterministic pass (no LLM configured)")
    try:
        if _chain is None:
            from langchain_core.prompts import ChatPromptTemplate
            from app.agents.classifier import _make_llm
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM),
                ("human",
                 "Member message: {message}\n"
                 "Interpreted intent: {intent}\n"
                 "Extracted fields: {fields}"),
            ])
            _chain = prompt | _make_llm().with_structured_output(Verdict)
        return _chain.invoke({"message": message, "intent": intent,
                              "fields": str(fields)})
    except Exception:
        return Verdict(agree=True, reason="verifier unavailable — defaulted to pass")
