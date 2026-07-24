"use client";

import { AuditEntry } from "../lib/api";

/**
 * The visible "brain" — a compact per-reply strip showing exactly how the
 * agent decided: classified → verified → policy rule → executed / handoff.
 * Built from the turn's own audit entries, so it can never drift from the log.
 */

type Pill = { label: string; cls: string };

const STYLES = {
  violet: "border-violet-200 bg-violet-50 text-violet-700",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
  amber: "border-amber-200 bg-amber-50 text-amber-700",
  rose: "border-rose-200 bg-rose-50 text-rose-700",
  sky: "border-sky-200 bg-sky-50 text-sky-700",
  slate: "border-slate-200 bg-slate-100 text-slate-600",
};

function pillsFrom(trace: AuditEntry[]): Pill[] {
  const pills: Pill[] = [];
  for (const e of trace) {
    const p: any = e.payload ?? {};
    switch (e.action) {
      case "intent_classified":
        pills.push({
          label: `classified · ${p.intent} ${Math.round((p.confidence ?? 0) * 100)}%`,
          cls: STYLES.violet,
        });
        break;
      case "verification":
        pills.push({
          label: `verifier · ${p.agree ? "agreed" : "disagreed"}${
            p.attempts > 1 ? ` (loop ×${p.attempts})` : ""
          }`,
          cls: p.agree ? STYLES.violet : STYLES.rose,
        });
        break;
      case "policy_decision":
        pills.push({
          label: `policy · ${p.rule_id} v${p.rule_version} → ${p.outcome}`,
          cls: p.outcome === "approve" ? STYLES.emerald : STYLES.amber,
        });
        break;
      case "escalate_to_human":
        pills.push({ label: "handoff → human", cls: STYLES.rose });
        break;
      case "assist":
        pills.push({ label: `assist · ${p.kind}`, cls: STYLES.violet });
        break;
      case "await_slot":
        pills.push({ label: `awaiting · ${p.slot}`, cls: STYLES.sky });
        break;
      case "followup_slot_filled":
        pills.push({
          label: `follow-up · ${p.slot} = ${p.value}`,
          cls: STYLES.sky,
        });
        break;
      default:
        if (e.actor === "backend")
          pills.push({
            label: `${e.action.replace(/_executed$/, "").replace(/_/g, " ")} ✓`,
            cls: STYLES.emerald,
          });
    }
  }
  return pills;
}

export default function PipelineStrip({ trace }: { trace: AuditEntry[] }) {
  const pills = pillsFrom(trace);
  if (!pills.length) return null;
  return (
    <div className="mt-2 border-t border-slate-100 pt-1.5">
      <p className="mb-1 text-[9px] font-semibold uppercase tracking-wider text-slate-400">
        Decision pipeline
      </p>
      <div className="flex flex-wrap items-center gap-1">
        {pills.map((p, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-[9px] text-slate-300">→</span>}
            <span
              className={`whitespace-nowrap rounded-full border px-1.5 py-0.5 text-[9.5px] font-medium ${p.cls}`}
            >
              {p.label}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
