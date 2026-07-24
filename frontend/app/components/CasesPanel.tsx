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
  starting: "border-slate-200 bg-slate-100 text-slate-600",
  awaiting_approval: "border-sky-200 bg-sky-50 text-sky-700",
  executing: "border-violet-200 bg-violet-50 text-violet-700",
  compensating: "border-amber-200 bg-amber-50 text-amber-700",
  closed: "border-slate-200 bg-slate-100 text-slate-500",
};

const FINAL_BADGE: Record<string, string> = {
  resolved: "border-emerald-200 bg-emerald-50 text-emerald-700",
  rolled_back: "border-amber-200 bg-amber-50 text-amber-700",
  denied: "border-rose-200 bg-rose-50 text-rose-700",
  expired: "border-slate-200 bg-slate-100 text-slate-500",
};

type St = "done" | "current" | "failed" | "undone" | "pending";

function stepState(c: Case, step: string): St {
  const s = c.state;
  if (!s) return "pending";
  if (s.failed === step) return "failed";
  if (s.final === "rolled_back" && s.completed.includes(step)) return "undone";
  if (s.completed.includes(step)) return "done";
  if (s.current === step) return "current";
  return "pending";
}

function StepDot({ state }: { state: St }) {
  const map: Record<St, string> = {
    done: "bg-emerald-500 border-emerald-500",
    current: "bg-sky-500 border-sky-500 animate-pulse",
    failed: "bg-rose-500 border-rose-500",
    undone: "bg-amber-100 border-amber-400",
    pending: "bg-white border-slate-300",
  };
  return <span className={`h-2.5 w-2.5 shrink-0 rounded-full border-2 ${map[state]}`} />;
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
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            Durable Servicing Cases
          </h2>
          <p className="text-[11px] text-slate-400">
            Temporal-orchestrated · saga with automatic compensation · human-in-the-loop
          </p>
        </div>
      </div>

      {cases.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50 py-6 text-center text-sm text-slate-400">
          No cases yet. Start one from the toolbar to watch the durable workflow execute.
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {cases.map((c) => {
          const s = c.state;
          return (
            <div
              key={c.case_id}
              className="rounded-lg border border-slate-200 bg-white p-3"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold capitalize text-slate-800">
                  {c.intent.replace(/_/g, " ")}
                  <span className="ml-1 font-normal text-slate-400">
                    · {c.member_id}
                  </span>
                </span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize ${
                    s?.final
                      ? FINAL_BADGE[s.final] ?? ""
                      : PHASE_BADGE[s?.phase ?? "starting"] ?? ""
                  }`}
                >
                  {(s?.final ?? s?.phase ?? "starting").replace(/_/g, " ")}
                </span>
              </div>

              <div className="space-y-1.5">
                {(s?.steps ?? []).map((step) => {
                  const st = stepState(c, step);
                  return (
                    <div key={step} className="flex items-center gap-2 text-xs">
                      <StepDot state={st} />
                      <span
                        className={
                          st === "undone"
                            ? "text-amber-600 line-through"
                            : st === "failed"
                            ? "font-medium text-rose-600"
                            : st === "done"
                            ? "text-slate-700"
                            : st === "current"
                            ? "font-medium text-sky-700"
                            : "text-slate-400"
                        }
                      >
                        {STEP_LABEL[step] ?? step}
                      </span>
                      {st === "failed" && (
                        <span className="text-[10px] text-rose-400">
                          failed → rolling back
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {s?.phase === "awaiting_approval" && (
                <div className="mt-3 rounded-md border border-sky-200 bg-sky-50 p-2">
                  <p className="mb-1.5 text-[11px] text-sky-800">
                    Durably awaiting underwriter — workflow is paused, holding
                    context (survives restarts).
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(c.case_id, true)}
                      className="flex-1 rounded-md bg-emerald-600 px-2 py-1 text-xs font-medium text-white hover:bg-emerald-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => decide(c.case_id, false)}
                      className="flex-1 rounded-md border border-rose-200 bg-white px-2 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50"
                    >
                      Deny
                    </button>
                  </div>
                </div>
              )}

              {s?.final === "rolled_back" && (
                <p className="mt-2 text-[10px] text-amber-600">
                  Auto-compensated — account left consistent, no partial changes.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
