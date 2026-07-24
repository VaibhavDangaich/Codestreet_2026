"""FastAPI entrypoint for the End-to-End Servicing Agent."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agents.graph import run_agent
from app.audit.chain import AUDIT
from app.config import now_iso
from app.mock_backend import card_system as cards
from app.models.schemas import ChatRequest, ChatResponse
from app.monitoring import anomaly


def _audit_log(actor: str, action: str, payload: dict, member_id: str = "system"):
    """Shared audit writer for autonomous (non-chat) actions."""
    AUDIT.append(ts=now_iso(), session_id="autonomous", member_id=member_id,
                 actor=actor, action=action, payload=payload)

app = FastAPI(title="CodeStreet 2026 — End-to-End Servicing Agent")

app.add_middleware(
    CORSMiddleware,
    # Local demo: allow any localhost port (frontend may run on 3000/3010/etc).
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"], allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    state = run_agent(req.member_id, req.message, req.session_id)
    return ChatResponse(resolution=state["resolution"],
                        classification=state.get("classification"))


@app.get("/member/{member_id}")
def member(member_id: str):
    """Live account snapshot — powers the before/after demo panel."""
    try:
        return cards.snapshot(member_id)
    except KeyError:
        return {"error": "unknown member"}


@app.get("/audit")
def audit(session_id: str | None = None):
    return {"entries": AUDIT.entries(session_id)}


@app.get("/audit/verify")
def audit_verify():
    return AUDIT.verify()


class TamperReq(BaseModel):
    seq: int
    new_payload: dict = {"amount": 999999, "note": "unauthorized edit"}


@app.post("/audit/tamper")
def audit_tamper(req: TamperReq):
    """DEMO ONLY: mutate a past entry without re-hashing so verify() catches it."""
    ok = AUDIT._tamper_for_demo(req.seq, req.new_payload)
    return {"tampered": ok, "verify": AUDIT.verify()}


# --- Autonomous monitoring (driven by the Temporal watcher) ----------------
@app.post("/monitor/tick")
def monitor_tick(member_id: str | None = None):
    """One monitoring pass. Called on a schedule by the Temporal workflow.

    Scans for unusual activity and acts autonomously (freeze + alert + audit).
    Returns the actions taken this tick so the workflow can log them.
    """
    ts = now_iso()
    if member_id:
        actions = anomaly.scan_and_act(member_id, _audit_log, ts)
    else:
        actions = anomaly.scan_all(_audit_log, ts)
    return {"ts": ts, "actions": actions, "count": len(actions)}


@app.post("/simulate/suspicious/{member_id}")
def simulate_suspicious(member_id: str):
    """DEMO: inject an unusual transaction the watcher will catch on its next tick."""
    try:
        txn = anomaly.inject_suspicious_transaction(member_id)
    except KeyError:
        return {"error": "unknown member"}
    return {"injected": txn}


@app.get("/alerts")
def alerts(member_id: str | None = None):
    return {"alerts": anomaly.get_alerts(member_id)}
