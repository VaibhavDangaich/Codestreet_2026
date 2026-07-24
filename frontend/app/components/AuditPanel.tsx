"use client";

import { AuditEntry, Verify } from "../lib/api";
import { IconRefresh } from "./icons";

const ACTOR_STYLES: Record<string, string> = {
  system: "bg-slate-100 text-slate-600 border-slate-200",
  classifier: "bg-violet-50 text-violet-700 border-violet-200",
  policy: "bg-amber-50 text-amber-700 border-amber-200",
  backend: "bg-emerald-50 text-emerald-700 border-emerald-200",
  agent: "bg-sky-50 text-sky-700 border-sky-200",
  saga: "bg-indigo-50 text-indigo-700 border-indigo-200",
  case: "bg-blue-50 text-blue-700 border-blue-200",
  human: "bg-teal-50 text-teal-700 border-teal-200",
};

function short(h: string) {
  return h.slice(0, 8) + "…" + h.slice(-6);
}

export default function AuditPanel({
  entries,
  verify,
  onTamper,
  onRefresh,
}: {
  entries: AuditEntry[];
  verify: Verify | null;
  onTamper: (seq: number) => void;
  onRefresh: () => void;
}) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">
            Immutable Audit Trail
          </h2>
          <p className="text-[11px] text-slate-400">
            SHA-256 hash-chained · tamper-evident
          </p>
        </div>
        <div className="flex items-center gap-2">
          {verify && (
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                verify.intact
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-rose-200 bg-rose-50 text-rose-700"
              }`}
            >
              {verify.intact
                ? `Chain intact · ${verify.total}`
                : `Broken @ seq ${verify.broken_at_seq}`}
            </span>
          )}
          <button
            onClick={onRefresh}
            className="grid h-7 w-7 place-items-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 hover:text-slate-600"
            aria-label="Refresh"
          >
            <IconRefresh />
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto bg-slate-50/60 px-3 py-3">
        {entries.length === 0 && (
          <p className="pt-10 text-center text-sm text-slate-400">
            No audit events yet. Interact with the agent to grow the chain.
          </p>
        )}
        {entries.map((e) => {
          const broken =
            verify && !verify.intact && verify.broken_at_seq === e.seq;
          return (
            <div
              key={e.seq}
              className={`group rounded-lg border bg-white p-2.5 text-xs shadow-sm transition ${
                broken ? "border-rose-300 ring-1 ring-rose-200" : "border-slate-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-300">#{e.seq}</span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                      ACTOR_STYLES[e.actor] ?? ACTOR_STYLES.system
                    }`}
                  >
                    {e.actor}
                  </span>
                  <span className="font-medium text-slate-700">{e.action}</span>
                </div>
                <button
                  onClick={() => onTamper(e.seq)}
                  title="Demo: tamper with this entry"
                  className="text-[10px] text-slate-300 opacity-0 transition group-hover:opacity-100 hover:text-rose-500"
                >
                  tamper
                </button>
              </div>
              {Object.keys(e.payload).length > 0 && (
                <pre className="mt-1.5 overflow-x-auto rounded-md border border-slate-100 bg-slate-50 p-2 text-[10px] leading-relaxed text-slate-500">
                  {JSON.stringify(e.payload, null, 2)}
                </pre>
              )}
              <div className="mt-1.5 flex items-center gap-1 font-mono text-[10px] text-slate-300">
                <span title={e.prev_hash}>prev {short(e.prev_hash)}</span>
                <span>→</span>
                <span title={e.hash} className="text-slate-400">
                  {short(e.hash)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
