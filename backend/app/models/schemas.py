"""Shared pydantic schemas for the servicing agent."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    FEE_REVERSAL = "fee_reversal"
    LIMIT_INCREASE = "limit_increase"
    CARD_REPLACEMENT = "card_replacement"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    """Structured output of the intent classifier."""

    intent: Intent = Field(description="The single best-matching service intent.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model confidence 0-1 that this intent is correct.",
    )
    extracted_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Any slots pulled from the message, e.g. amount, reason, fee_id.",
    )
    rationale: str = Field(description="One short sentence explaining the choice.")


class Resolution(BaseModel):
    """Final outcome of handling a request."""

    status: Literal["resolved", "escalated", "needs_info", "rejected", "answered"]
    message: str
    intent: Intent
    details: dict[str, Any] = Field(default_factory=dict)
    escalation_summary: Optional[str] = None


class ChatRequest(BaseModel):
    member_id: str = Field(default="M-1001")
    message: str
    session_id: str = Field(default="default")


class ChatResponse(BaseModel):
    resolution: Resolution
    classification: Optional[Classification] = None
