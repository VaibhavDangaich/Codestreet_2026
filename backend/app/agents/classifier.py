"""Intent classifier: few-shot examples + structured output + confidence.

Design choices (for the write-up):
  * Structured output (with_structured_output) makes the model return a validated
    `Classification` object instead of free text we'd have to parse -- far more
    reliable than pure few-shot.
  * Few-shot examples anchor the boundaries between the three intents.
  * The `confidence` field is the escalation lever: low confidence routes to a
    clarifying question or a human, instead of the agent acting on a guess.

Provider-agnostic (Gemini or OpenAI). If no key is present we fall back to a
deterministic keyword classifier so the app still runs (and demos) offline.
"""
from __future__ import annotations

from app.config import (
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    llm_enabled,
)
from app.models.schemas import Classification, Intent

SYSTEM_PROMPT = """You are the triage classifier for an Amex card-servicing agent.
Classify the member's message into exactly one intent:
- fee_reversal: wants a fee (late/annual) waived or refunded.
- limit_increase: wants their credit limit raised.
- card_replacement: card lost, stolen, damaged, or not received; wants a new one.
- unknown: none of the above, or too ambiguous to tell.

Extract useful slots into extracted_fields when present, e.g.:
  amount (number), reason (string), fee_id, lost_or_stolen (bool).
Set confidence honestly: high (>0.8) only when the intent is unmistakable;
low (<0.55) when the message is vague or could be multiple intents."""

FEW_SHOTS = [
    ("Can you waive the $39 late fee on my last statement? I paid a day late.",
     Classification(intent=Intent.FEE_REVERSAL, confidence=0.96,
                    extracted_fields={"amount": 39, "reason": "paid one day late"},
                    rationale="Explicit request to waive a late fee.")),
    ("I've had my card for years and never miss a payment — can I get a higher limit?",
     Classification(intent=Intent.LIMIT_INCREASE, confidence=0.93,
                    extracted_fields={"reason": "long tenure, on-time payments"},
                    rationale="Asking to raise the credit limit.")),
    ("I think I lost my card at the airport, I need a new one asap.",
     Classification(intent=Intent.CARD_REPLACEMENT, confidence=0.95,
                    extracted_fields={"lost_or_stolen": True, "reason": "lost at airport"},
                    rationale="Lost card, needs replacement.")),
    ("Why is my statement so high this month?",
     Classification(intent=Intent.UNKNOWN, confidence=0.4,
                    extracted_fields={},
                    rationale="A billing question, not one of the three service flows.")),
]

_KEYWORDS = {
    Intent.FEE_REVERSAL: ["fee", "waive", "reverse", "refund", "late charge"],
    Intent.LIMIT_INCREASE: ["limit", "increase", "raise", "higher limit", "credit line"],
    Intent.CARD_REPLACEMENT: ["lost", "stolen", "replace", "new card", "damaged", "broken"],
}


def _fallback(message: str) -> Classification:
    text = message.lower()
    best, score = Intent.UNKNOWN, 0
    for intent, kws in _KEYWORDS.items():
        hits = sum(1 for k in kws if k in text)
        if hits > score:
            best, score = intent, hits
    conf = 0.75 if score >= 1 else 0.3
    return Classification(intent=best, confidence=conf, extracted_fields={},
                          rationale="Offline keyword fallback (no LLM key set).")


def _make_llm():
    # max_retries=0 so a quota/rate error fails fast to our fallback instead of
    # blocking the request with exponential-backoff retries.
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0,
                                      google_api_key=GOOGLE_API_KEY,
                                      max_retries=0, timeout=20)
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=OPENAI_MODEL, temperature=0, api_key=OPENAI_API_KEY,
                      max_retries=0, timeout=20)


def _build_llm_classifier():
    # Use concrete message objects for the system prompt + few-shots so their
    # JSON braces are NOT parsed as template variables; only the final human
    # turn is a template. (Tuple form triggers f-string parsing -> breaks on {}.)
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

    structured = _make_llm().with_structured_output(Classification)

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    for user_msg, label in FEW_SHOTS:
        messages.append(HumanMessage(content=user_msg))
        messages.append(AIMessage(content=label.model_dump_json()))
    messages.append(HumanMessagePromptTemplate.from_template("{message}"))
    prompt = ChatPromptTemplate.from_messages(messages)
    return prompt | structured


_CHAIN = None


def classify(message: str) -> Classification:
    global _CHAIN
    if not llm_enabled():
        return _fallback(message)
    try:
        if _CHAIN is None:
            _CHAIN = _build_llm_classifier()
        return _CHAIN.invoke({"message": message})
    except Exception as exc:  # network/key issues -> stay up
        fb = _fallback(message)
        fb.rationale += f" (LLM error: {type(exc).__name__})"
        return fb
