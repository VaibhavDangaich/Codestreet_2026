# End-to-End Servicing Agent — CodeStreet 2026 (Amex)

A conversational AI agent that **fully resolves** high-frequency card-servicing
requests — **fee reversals, credit-limit increases, card replacements** — keeps a
**tamper-evident hash-chained audit trail** of every decision, and **escalates to
a human with full context** when policy limits are hit.

Differentiators beyond a basic servicing bot:

1. **Trustworthy decisioning (the LLM never decides).** The LLM only *proposes*;
   a **Policy-as-Code** engine of versioned declarative rules **decides** and cites
   the exact rule (e.g. `LIMIT-CAP v1.1`). A **self-verifying agent** (risk-based,
   bounded propose→verify→revise loop) must agree before acting. Denials return a
   **counterfactual** ("I can auto-approve up to $X now"). Rules become nodes in
   the audit graph (**decision provenance**).
2. **Durable servicing cases (Temporal)** — high-stakes requests become durable
   workflows: a multi-step **saga with automatic compensation** (if a step fails,
   completed steps roll back — no partial financial state), a **durable
   human-in-the-loop** approval that waits on an underwriter (surviving restarts),
   and **live queryable status**.
3. **Neo4j audit graph** — the audit trail is persisted to Neo4j Aura and rendered
   as an analyst-friendly graph (Cytoscape) showing the full chain-of-custody,
   including which policy rule fired on each decision.

Out-of-scope messages are handled intelligently (answered, escalated with
context, or clarified) — but the agent only ever *acts* on the three scoped
intents.

## Architecture

```
Next.js UI ──HTTP──► FastAPI ──► LangGraph agent
(chat · cases ·                   ├─ classifier (Gemini) — proposes intent + amounts
 audit trail ·                    ├─ verifier (risk-based propose→verify→revise loop)
 audit graph)                     ├─ Policy-as-Code engine — DECIDES + cites rule/version
                                  ├─ 3 resolution flows → mock card backend (+ counterfactual)
                                  ├─ assistant (out-of-scope: answer / escalate / clarify)
                                  └─ hash-chained audit chain (SHA-256)

Temporal server ─► Worker ─► ServicingCaseWorkflow (durable)
                              ├─ human-in-the-loop approval (signal + durable wait)
                              ├─ saga forward steps ──HTTP──► /internal/action
                              └─ on failure: compensate completed steps in reverse

FastAPI /graph ─► Neo4j Aura (persist audit trail) ─► Cytoscape graph in UI
                  (falls back to in-memory graph if Neo4j is unavailable)
```

- **Backend**: Python 3.12 · FastAPI · LangChain/LangGraph · `langchain-google-genai`
  (Gemini, model-agnostic) · Temporal (`temporalio`) · `neo4j`
- **Frontend**: Next.js 16 · Tailwind · Cytoscape · Web Speech API (voice)

> The project source lives on the SSD (exFAT). The Python venv lives on the
> internal disk at `~/.venvs/cs2026-backend` (exFAT can't host a uv venv). The run
> scripts export `UV_PROJECT_ENVIRONMENT`, so this is transparent.

## Configuration

Copy `backend/.env.example` → `backend/.env` and set:
- `GOOGLE_API_KEY` (Gemini) — or set `LLM_PROVIDER=openai` + `OPENAI_API_KEY`.
- `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` / `NEO4J_DATABASE` (Aura). If
  omitted or unreachable, the audit graph falls back to an in-memory build.

## Run it

```bash
scripts/run_temporal.sh    # 1) Temporal dev server (UI http://localhost:8233)
scripts/run_backend.sh     # 2) FastAPI (http://127.0.0.1:8010)
scripts/run_worker.sh      # 3) Temporal worker (hosts ServicingCaseWorkflow)
scripts/run_frontend.sh    # 4) Next.js UI (http://localhost:3010)
```

Evals for the slide metrics:
```bash
scripts/run_evals.sh       # accuracy, per-intent, first-contact resolution
```

> exFAT tip: if the frontend errors with "Failed to open database" after a
> force-kill, clear the Turbopack cache: `rm -rf frontend/.next && scripts/run_frontend.sh`.

## Demo script (~3 min)

1. **Resolve** — "Please waive my $39 late fee." → resolved instantly. Every
   reply shows its **decision pipeline** (classified → verified → policy rule →
   executed), built from the turn's own audit entries, while the audit trail
   grows on the right.
2. **Escalate** — "Bump my limit to $50,000." (via chat) → policy gate → escalated
   with a full context summary.
3. **Out-of-scope** — "Why is my statement so high?" → answered conversationally;
   "I want to dispute a charge" → escalated with handoff context.
4. **Durable saga** — toolbar **New card** → watch the 4-step saga complete.
5. **Auto-rollback** — toolbar **Card → rollback** → the fulfillment step fails and
   completed steps compensate in reverse; the account is left consistent.
6. **Human-in-the-loop** — toolbar **$50k limit → approval** → the case waits at
   `awaiting_approval`; click **Approve** and the saga runs.
7. **Tamper demo** — hover an audit entry → **tamper** → verify flips to "Broken @
   seq N".
8. **Audit graph** — switch the right panel to **Audit graph** to explore the
   chain-of-custody in Neo4j.

## Key endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | Resolve a servicing request (or answer/escalate/clarify) |
| GET | `/audit` · `/audit/verify` | Fetch chain · verify integrity |
| POST | `/audit/tamper` | Demo: break the chain |
| POST | `/cases/start` | Start a durable servicing case |
| POST | `/cases/{id}/decision` | Underwriter approve/deny (signal) |
| GET | `/cases` · `/cases/{id}` | Live case status (workflow query) |
| POST | `/internal/action/{action}` | One saga step (called by the workflow) |
| GET | `/graph` | Audit trail as a graph (Neo4j, memory fallback) |
| GET | `/member/{id}` | Live account snapshot |
