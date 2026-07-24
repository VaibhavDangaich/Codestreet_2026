"""Runtime config loaded from environment / .env.

Provider-agnostic: uses Gemini if GOOGLE_API_KEY is set, else OpenAI if
OPENAI_API_KEY is set, else a deterministic keyword fallback (so it always runs).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Choose provider: explicit LLM_PROVIDER wins, else auto-detect from keys.
_explicit = os.getenv("LLM_PROVIDER", "").lower().strip()
if _explicit in ("gemini", "openai", "none"):
    LLM_PROVIDER = _explicit
elif GOOGLE_API_KEY:
    LLM_PROVIDER = "gemini"
elif OPENAI_API_KEY:
    LLM_PROVIDER = "openai"
else:
    LLM_PROVIDER = "none"

OPENAI_MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Confidence below this -> ask for clarification / escalate instead of acting.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))

# LangSmith (optional; set to enable tracing/evals)
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "codestreet-servicing-agent")


def llm_enabled() -> bool:
    return LLM_PROVIDER in ("gemini", "openai")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
