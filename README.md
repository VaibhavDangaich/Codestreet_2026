# End-to-End Servicing Agent — CodeStreet 2026 (Amex)

A conversational AI agent that **fully resolves** high-frequency card-servicing
requests — **fee reversals, credit-limit increases, card replacements** — in a
single interaction, keeps a **tamper-evident hash-chained audit trail** of every
decision, and **escalates to a human with full context** when policy limits are
hit. Plus an **autonomous, Temporal-orchestrated monitor** (the "guardian agent")
that detects unusual card activity and acts on its own — beyond the base problem
statement.

## Architecture

```
Next.js UI  ──HTTP──►  FastAPI  ──►  LangGraph agent
(chat + live                          ├─ classifier (Gemini, few-shot + structured output + confidence)
 audit panel +                        ├─ policy gates (auto-approve vs escalate)
 alert banner)                        ├─ 3 resolution flows → mock card backend
                                      └─ hash-chained audit chain (SHA-256, tamper-evident)

Temporal dev server ──► Worker ──► CardMonitorWorkflow (durable timer loop)
                                      └─ scan activity ──HTTP──► FastAPI /monitor/tick
                                                                  └─ detect anomaly → auto-freeze → alert → audit
```

- **Backend**: Python 3.12 · FastAPI · LangChain/LangGraph · `langchain-google-genai` (Gemini) · Temporal (`temporalio`)
- **Frontend**: Next.js 16 · Tailwind · Web Speech API (voice)
- **Why Gemini**: model-agnostic via LangChain; set `LLM_PROVIDER=openai` to switch.

> Note: the project source lives on the SSD (exFAT). The Python venv lives on the
> internal disk at `~/.venvs/cs2026-backend` (exFAT can't host a uv venv). The run
> scripts export `UV_PROJECT_ENVIRONMENT` so this is transparent.

## Run it (5 terminals)

```bash
# 1. Temporal dev server (UI at http://localhost:8233)
scripts/run_temporal.sh

# 2. Backend API (http://127.0.0.1:8010)
scripts/run_backend.sh

# 3. Temporal worker
scripts/run_worker.sh

# 4. Start the durable monitor workflow (run once)
scripts/start_monitor.sh

# 5. Frontend (http://localhost:3010)
scripts/run_frontend.sh
```

Evals for the slide metrics:
```bash
scripts/run_evals.sh      # accuracy, per-intent, first-contact resolution
```

## Demo script (~3 min)

1. **Fee reversal** — "Please waive my $39 late fee." → resolved instantly; watch
   the audit trail grow (classifier → policy → backend → agent).
2. **Escalation** — "Bump my limit to $50,000." → policy gate → **escalated to a
   human with a full context summary** (no repeating yourself).
3. **Tamper demo** — hover any audit entry → **tamper** → the verify badge flips to
   "⚠ Broken @ seq N". Immutability, proven live.
4. **Autonomous guardian** — click **⚡ Simulate suspicious charge**. Do nothing.
   Within ~10s the Temporal monitor wakes, **freezes the card on its own**, and a
   🛡️ alert banner appears — all logged to the same audit chain.

## Key endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | Resolve a servicing request |
| GET | `/audit` · `/audit/verify` | Fetch chain · verify integrity |
| POST | `/audit/tamper` | Demo: break the chain |
| POST | `/monitor/tick` | One autonomous scan (called by Temporal) |
| POST | `/simulate/suspicious/{id}` | Demo: inject an unusual charge |
| GET | `/alerts` | Proactive alerts raised by the monitor |
