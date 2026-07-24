# Demo Video Script & Storyboard — End-to-End Servicing Agent

**Target length: 2:45 (hard cap 3:00).** Screencast of the live app with a clear
voiceover. Not a slide reel. Record at 1440×900+, cursor visible, one clean take
per scene, then stitch. **Upload hours early** (rendering can take a while).

Before recording, have the app running (5 processes: temporal, backend, worker,
frontend) and the browser at `http://localhost:3010`, member **Priya Sharma
(M-1001)**. Reset state by restarting the backend so cards/limits are fresh.

---

### Scene 1 — Hook (0:00–0:15)
**On screen:** the app, full view. Slowly move cursor to the header.
**VO:** "This is the End-to-End Servicing Agent for American Express CodeStreet
2026. It resolves the most common card-servicing requests — fee reversals, limit
increases, card replacements — completely, in one conversation, and it keeps a
tamper-proof record of everything it does."

### Scene 2 — The problem (0:15–0:33)
**On screen:** hover the member stat strip (limit, standing, fees).
**VO:** "Today these routine requests mean holding, repeating yourself, and manual
work — a human-assisted contact costs banks over thirteen dollars. We make the
routine autonomous, safely, so people are freed for the hard cases."

### Scene 3 — Resolve + audit (0:33–1:03)
**On screen:** click the prompt "Please waive my $39 late fee." → answer appears
`resolved`. Point to the **Audit trail** growing (classifier → policy → backend →
agent).
**VO:** "Watch it resolve a late-fee reversal end to end. It classifies the intent
with a confidence score, checks policy, executes the waiver — and every single
decision is written to a SHA-256 hash-chained audit trail on the right. Not a log
you hope is complete — a chain of custody you can prove."

### Scene 4 — Durable saga + rollback ⭐ (1:03–1:38)  *(the money shot)*
**On screen:** click toolbar **Card → rollback**. The Cases panel shows the saga
tick: block old card ✓, charge fee ✓, order fulfillment ✗ **fails**, then the
completed steps strike through as they compensate → **Rolled back**.
**VO:** "Servicing isn't one call — it's a transaction across card systems, ledger,
and fulfillment. We run each one as a durable Temporal workflow. Here the
fulfillment step fails — and instead of leaving the account half-changed, the
workflow automatically rolls back the completed steps in reverse: refund the fee,
unblock the card. Guaranteed to fully complete or cleanly undo. No partial state."

### Scene 5 — Human-in-the-loop (1:38–2:05)
**On screen:** click toolbar **$50k limit → approval**. Case sits at
`awaiting_approval`. Click **Approve** → the saga runs → `resolved`; the member's
limit updates.
**VO:** "When a request is over policy, the agent doesn't guess — the workflow
durably pauses and waits for a human underwriter, holding full context, surviving
restarts. Approve it, and the saga completes. High-volume tasks run autonomously;
high-stakes ones keep a human in the loop."

### Scene 6 — Trust: tamper + graph (2:05–2:28)
**On screen:** in Audit trail, hover an entry → click **tamper** → the badge flips
to **Broken @ seq N**. Then switch the tab to **Audit graph** (optionally the ⤢
fullscreen) — the Neo4j/Cytoscape chain-of-custody graph.
**VO:** "Because it's hash-chained, if anyone edits a past entry, the chain breaks —
and we detect it instantly. The whole trail is persisted to Neo4j, so an analyst
can explore the full chain of custody as a graph, not scroll a log."

### Scene 7 — Why Amex + close (2:28–2:45)
**On screen:** back to chat; type a vague follow-up "raise my limit" → it asks
"to what amount?" → "to 12000" → resolved. (Shows multi-turn.) End on the full app.
**VO:** "It even handles multi-turn follow-ups and voice. Deloitte found only
twenty-one percent of enterprises have mature governance for AI agents — and names
the missing controls as audit trails and human-approval boundaries. Those are
exactly what we built. This is the governance layer that lets Amex push autonomy
further, without widening its risk. Thank you."

---

## Production checklist
- Script each scene; rehearse once; record scene-by-scene (re-record only the
  fumbled one).
- Good mic, quiet room; keep energy up; ~150 words/min.
- Cursor movements slow and deliberate; pause ~1s after each click so viewers see
  the result.
- Keep the audit panel visible during Scenes 3–5 so the trail is always growing.
- **Backup:** also record a clean full run with no narration as a fallback in case
  a live LLM call stalls during the graded pitch.
- Export ≤3:00, 1080p, upload early.
