"use client";

import { Case, caseDecision } from "../lib/api";

const STEP_LABEL: Record<string, string> = {
  block_old_card: "Block old card",
  charge_fee: "Charge fee",
  order_fulfillment: "Order new card",
  send_confirmation: "Notify member",
  reserve_line: "Reserve credit line",
  apply_new_limit: "Apply new limit",
  post_ledger: "Post to ledger",
  apply_credit: "Apply statement credit",
};

const PHASE_BADGE: Record<string, string> = {
  starting: "border-slate-500/40 bg-slate-500/15 text-slate-300",
  awaiting_approval: "border-sky-500/40 bg-sky-500/15 text-sky-300 animate-pulse",
  executing: "border-violet-500/40 bg-violet-500/15 text-violet-300",
  compensating: "border-amber-500/40 bg-amber-500/15 text-amber-300 animate-pulse",
  closed: "border-white/15 bg-white/5 text-white/50",
};

const FINAL_BADGE: Record<string, string> = {
  resolved: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
  rolled_back: "border-amber-500/40 bg-amber-500/15 text-amber-300",
  denied: "border-rose-500/40 bg-rose-500/15 text-rose-300",
  expired: "border-slate-500/40 bg-slate-500/15 text-slate-400",
};

function StepDot({ state }: { state: "done" | "current" | "failed" | "undone" | "pending" }) {
  const map = {
    done: "bg-emerald-400 border-emerald-400",
    current: "bg-sky-400 border-sky-400 animate-pulse",
    failed: "bg-rose-500 border-rose-500",
    undone: "bg-amber-400/30 border-amber-400",
    pending: "bg-transparent border-white/25",
  };
  return <span className={`h-3 w-3 shrink-0 rounded-full border-2 ${map[state]}`} />;
}

function stepState(c: Case, step: string): "done" | "current" | "failed" | "undone" | "pending" {
  const s = c.state;
  if (!s) return "pending";
  if (s.failed === step) return "failed";
  if (s.final === "rolled_back" && s.completed.includes(step)) return "undone";
  if (s.completed.includes(step)) return "done";
  if (s.current === step) return "current";
  return "pending";
}

export default function CasesPanel({
  cases,
  onChanged,
}: {
  cases: Case[];
  onChanged: () => void;
}) {
  async function decide(id: string, approved: boolean) {
    await caseDecision(id, approved, approved ? "approved by underwriter" : "declined");
    onChanged();
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-black/30 p-4 backdrop-blur">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">
            Durable Servicing Cases
          </h2>
          <p className="text-[11px] text-white/40">
            Temporal-orchestrated · saga + auto-compensation · human-in-the-loop
          </p>
        </div>
      </div>

      {cases.length === 0 && (
        <p className="py-6 text-center text-sm text-white/30">
          No cases yet. Start one above to watch the durable workflow execute.
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {cases.map((c) => {
          const s = c.state;
          return (
            <div
              key={c.case_id}
              className="rounded-xl border border-white/10 bg-white/[0.03] p-3"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium text-white/80">
                  {c.intent.replace(/_/g, " ")}{" "}
                  <span className="text-white/30">· {c.member_id}</span>
                </span>
                {s?.final ? (
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      FINAL_BADGE[s.final] ?? ""
                    }`}
                  >
                    {s.final.replace(/_/g, " ")}
                  </span>
                ) : (
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                      PHASE_BADGE[s?.phase ?? "starting"] ?? ""
                    }`}
                  >
                    {(s?.phase ?? "starting").replace(/_/g, " ")}
                  </span>
                )}
              </div>

              {/* step timeline */}
              <div className="space-y-1.5">
                {(s?.steps ?? []).map((step) => {
                  const st = stepState(c, step);
                  return (
                    <div key={step} className="flex items-center gap-2 text-xs">
                      <StepDot state={st} />
                      <span
                        className={
                          st === "undone"
                            ? "text-amber-300/70 line-through"
                            : st === "failed"
                            ? "text-rose-300"
                            : st === "done"
                            ? "text-white/80"
                            : st === "current"
                            ? "text-sky-300"
                            : "text-white/35"
                        }
                      >
                        {STEP_LABEL[step] ?? step}
                      </span>
                      {st === "failed" && (
                        <span className="text-[10px] text-rose-400/70">
                          failed → rolling back
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* approval controls */}
              {s?.phase === "awaiting_approval" && (
                <div className="mt-3 rounded-lg border border-sky-500/30 bg-sky-500/10 p-2">
                  <p className="mb-1.5 text-[11px] text-sky-200/80">
                    ⏳ Durably awaiting underwriter — workflow is paused, holding
                    context (survives restarts).
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(c.case_id, true)}
                      className="flex-1 rounded-md bg-emerald-600/80 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-600"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => decide(c.case_id, false)}
                      className="flex-1 rounded-md border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-200 hover:bg-rose-500/20"
                    >
                      Deny
                    </button>
                  </div>
                </div>
              )}

              {s?.final === "rolled_back" && (
                <p className="mt-2 text-[10px] text-amber-300/70">
                  ↩ Auto-compensated — account left in a consistent state, no
                  partial changes.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
