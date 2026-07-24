"""FastAPI entrypoint for the End-to-End Servicing Agent."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import uuid

from app.agents.graph import run_agent
from app.audit.chain import AUDIT
from app.cases import plans
from app.config import now_iso
from app.mock_backend import card_system as cards
from app.mock_backend import services
from app.models.schemas import ChatRequest, ChatResponse
from app.temporal.client import TASK_QUEUE, get_temporal_client
from app.temporal.workflows import ServicingCaseWorkflow

# in-memory registry of started cases (id -> metadata) for the /cases list view
_CASES: dict[str, dict] = {}


def _audit_log(actor: str, action: str, payload: dict, member_id: str = "system"):
    """Shared audit writer for non-chat (saga / case) actions."""
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


# --- Saga actions (called by the Temporal workflow's do_action activity) ----
class ActionReq(BaseModel):
    member_id: str
    params: dict = {}


@app.post("/internal/action/{action}")
def internal_action(action: str, req: ActionReq):
    """Execute one atomic service action and audit-log it.

    The Temporal saga calls this per step (and per compensation). Every call is
    written to the audit chain, so a rollback is fully visible in the trail.
    """
    result = services.perform(action, req.member_id, req.params)
    _audit_log("saga", f"action:{action}",
               {"params": req.params, "result": result}, req.member_id)
    return result


# --- Durable servicing cases (Temporal ServicingCaseWorkflow) ---------------
class CaseStartReq(BaseModel):
    member_id: str = "M-1001"
    intent: str
    params: dict = {}
    force_fail: bool = False           # demo: force the fulfillment step to fail
    approval_timeout_seconds: int = 120


@app.post("/cases/start")
async def cases_start(req: CaseStartReq):
    try:
        member = cards.get_member(req.member_id)
    except KeyError:
        return {"error": "unknown member"}
    plan, requires_approval = plans.build_plan(req.intent, member, req.params,
                                               req.force_fail)
    if not plan:
        return {"error": f"no saga plan for intent '{req.intent}'"}

    case_id = f"case-{uuid.uuid4().hex[:8]}"
    client = await get_temporal_client()
    await client.start_workflow(
        ServicingCaseWorkflow.run,
        args=[req.member_id, req.intent, plan, requires_approval,
              req.approval_timeout_seconds],
        id=case_id, task_queue=TASK_QUEUE,
    )
    _CASES[case_id] = {"member_id": req.member_id, "intent": req.intent,
                       "requires_approval": requires_approval,
                       "force_fail": req.force_fail}
    _audit_log("case", "case_started",
               {"case_id": case_id, "intent": req.intent,
                "requires_approval": requires_approval}, req.member_id)
    return {"case_id": case_id, "requires_approval": requires_approval,
            "plan": [s["action"] for s in plan]}


class DecisionReq(BaseModel):
    approved: bool
    note: str = ""


@app.post("/cases/{case_id}/decision")
async def cases_decision(case_id: str, req: DecisionReq):
    client = await get_temporal_client()
    handle = client.get_workflow_handle(case_id)
    await handle.signal(ServicingCaseWorkflow.submit_decision,
                        args=[req.approved, req.note])
    _audit_log("human", "underwriter_decision",
               {"case_id": case_id, "approved": req.approved, "note": req.note},
               _CASES.get(case_id, {}).get("member_id", "system"))
    return {"ok": True}


async def _case_state(client, case_id: str):
    try:
        return await client.get_workflow_handle(case_id).query(
            ServicingCaseWorkflow.status)
    except Exception:
        return None


@app.get("/cases/{case_id}")
async def cases_get(case_id: str):
    client = await get_temporal_client()
    return {"case_id": case_id, **_CASES.get(case_id, {}),
            "state": await _case_state(client, case_id)}


@app.get("/cases")
async def cases_list():
    client = await get_temporal_client()
    out = []
    for cid, meta in reversed(list(_CASES.items())):
        out.append({"case_id": cid, **meta,
                    "state": await _case_state(client, cid)})
    return {"cases": out}
