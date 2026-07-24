"""General assist for out-of-scope messages.

The agent AUTONOMOUSLY acts on only three intents. For anything else we don't
dead-end with a menu — we let the LLM decide the safe, helpful response:

  * info     — an informational question we can answer generally (NO account
               changes, NO invented account data).
  * escalate — a real servicing request outside our three abilities → hand off
               to a human with a one-line context summary.
  * clarify  — genuinely too vague → ask one specific question.

Crucially, this path never *acts* on the account — it only informs, routes, or
asks. Actions stay strictly scoped to the three resolvable intents.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.config import llm_enabled

SYSTEM = """You are American Express's card-servicing assistant.
You can AUTONOMOUSLY resolve ONLY: fee reversals, credit-limit increases, and
card replacements. The user's message is NOT clearly one of those.

Choose exactly one kind:
- "info": it is a general/informational question you can answer helpfully and
  safely without changing anything on the account (e.g. how statements work,
  what a fee is, general guidance). Put a concise, friendly answer in `message`.
  NEVER invent account-specific numbers; speak generally or point them to their
  statement/app.
- "escalate": it is a genuine servicing request you are NOT allowed to resolve
  yourself (dispute a charge, close account, travel help, report fraud, etc.).
  Put a brief empathetic handoff line in `message`, and a one-sentence context
  summary for the human agent in `escalation_summary`.
- "clarify": too vague to tell what they want. Ask ONE specific question in
  `message`.

Never claim you performed an account action. Be concise (1-3 sentences)."""


class AssistResult(BaseModel):
    kind: Literal["info", "escalate", "clarify"] = Field(
        description="How to handle this out-of-scope message.")
    message: str = Field(description="The member-facing reply (1-3 sentences).")
    escalation_summary: Optional[str] = Field(
        default=None, description="One-line context for a human, if escalating.")


_MENU = ("I can directly help with fee reversals, credit-limit increases, or "
         "card replacements. For anything else I can answer questions or connect "
         "you to a specialist — what do you need?")

_chain = None


def assist(message: str) -> AssistResult:
    global _chain
    if not llm_enabled():
        return AssistResult(kind="clarify", message=_MENU)
    try:
        if _chain is None:
            from langchain_core.prompts import ChatPromptTemplate
            from app.agents.classifier import _make_llm
            prompt = ChatPromptTemplate.from_messages(
                [("system", SYSTEM), ("human", "{message}")])
            _chain = prompt | _make_llm().with_structured_output(AssistResult)
        return _chain.invoke({"message": message})
    except Exception:
        return AssistResult(kind="clarify", message=_MENU)
