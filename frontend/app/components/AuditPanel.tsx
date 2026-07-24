"use client";

import { AuditEntry, Verify } from "../lib/api";

const ACTOR_STYLES: Record<string, string> = {
  system: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  classifier: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  policy: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  backend: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  agent: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  monitor: "bg-rose-500/15 text-rose-300 border-rose-500/30",
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
    <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-black/30 backdrop-blur">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-white">
            Immutable Audit Trail
          </h2>
          <p className="text-[11px] text-white/40">
            SHA-256 hash-chained · tamper-evident
          </p>
        </div>
        <div className="flex items-center gap-2">
          {verify && (
            <span
              className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                verify.intact
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : "border-rose-500/40 bg-rose-500/15 text-rose-300"
              }`}
            >
              {verify.intact
                ? `✓ Chain intact (${verify.total})`
                : `⚠ Broken @ seq ${verify.broken_at_seq}`}
            </span>
          )}
          <button
            onClick={onRefresh}
            className="rounded-md border border-white/10 px-2 py-1 text-[11px] text-white/60 hover:bg-white/5"
          >
            ↻
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3">
        {entries.length === 0 && (
          <p className="pt-10 text-center text-sm text-white/30">
            No audit events yet. Send a request to watch the chain grow.
          </p>
        )}
        {entries.map((e) => {
          const broken =
            verify && !verify.intact && verify.broken_at_seq === e.seq;
          return (
            <div
              key={e.seq}
              className={`group rounded-lg border p-2.5 text-xs transition ${
                broken
                  ? "border-rose-500/50 bg-rose-500/10"
                  : "border-white/10 bg-white/[0.03]"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-white/30">#{e.seq}</span>
                  <span
                    className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                      ACTOR_STYLES[e.actor] ?? ACTOR_STYLES.system
                    }`}
                  >
                    {e.actor}
                  </span>
                  <span className="font-medium text-white/80">{e.action}</span>
                </div>
                <button
                  onClick={() => onTamper(e.seq)}
                  title="Demo: tamper with this entry"
                  className="opacity-0 transition group-hover:opacity-100 text-[10px] text-rose-400/70 hover:text-rose-300"
                >
                  tamper
                </button>
              </div>
              {Object.keys(e.payload).length > 0 && (
                <pre className="mt-1.5 overflow-x-auto rounded bg-black/40 p-2 text-[10px] leading-relaxed text-white/50">
                  {JSON.stringify(e.payload, null, 2)}
                </pre>
              )}
              <div className="mt-1.5 flex items-center gap-1 font-mono text-[10px] text-white/25">
                <span title={e.prev_hash}>prev {short(e.prev_hash)}</span>
                <span className="text-white/15">→</span>
                <span title={e.hash} className="text-white/40">
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
