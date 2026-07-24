"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AuditPanel from "./components/AuditPanel";
import CasesPanel from "./components/CasesPanel";
import GraphView from "./components/GraphView";
import {
  IconClose,
  IconExpand,
  IconMark,
  IconMic,
  IconMinimize,
  IconSend,
} from "./components/icons";
import {
  AuditEntry,
  Case,
  ChatResponse,
  Member,
  Verify,
  getAudit,
  getMember,
  listCases,
  sendChat,
  startCase,
  tamperAudit,
  verifyAudit,
} from "./lib/api";

type Msg = {
  role: "user" | "agent";
  text: string;
  status?: ChatResponse["resolution"]["status"];
  classification?: ChatResponse["classification"];
  escalation?: string | null;
};

type Tab = "cases" | "audit" | "graph";

const MEMBERS = [
  { id: "M-1001", label: "Priya Sharma — good standing" },
  { id: "M-2002", label: "Alex Chen — delinquent" },
];

const QUICK = [
  "Please waive my $39 late fee, I paid a day late.",
  "I've been loyal for years — can I get a higher credit limit?",
  "I lost my card at the airport, I need a new one asap.",
  "Why is my statement so high this month?",
];

const CASE_ACTIONS: {
  label: string;
  dot: string;
  run: () => [string, Record<string, unknown>, boolean];
}[] = [
  { label: "New card", dot: "bg-emerald-500", run: () => ["card_replacement", { fee: 0 }, false] },
  { label: "Card → rollback", dot: "bg-amber-500", run: () => ["card_replacement", {}, true] },
  { label: "$50k limit → approval", dot: "bg-sky-500", run: () => ["limit_increase", { new_limit: 50000 }, false] },
];

const STATUS_BADGE: Record<string, string> = {
  resolved: "border-emerald-200 bg-emerald-50 text-emerald-700",
  escalated: "border-amber-200 bg-amber-50 text-amber-700",
  needs_info: "border-sky-200 bg-sky-50 text-sky-700",
  rejected: "border-rose-200 bg-rose-50 text-rose-700",
  answered: "border-violet-200 bg-violet-50 text-violet-700",
};

const TABS: [Tab, string][] = [
  ["cases", "Cases"],
  ["audit", "Audit trail"],
  ["graph", "Audit graph"],
];

export default function Home() {
  const [memberId, setMemberId] = useState("M-1001");
  const [member, setMember] = useState<Member | null>(null);
  const [sessionId, setSessionId] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [tab, setTab] = useState<Tab>("cases");
  const [expanded, setExpanded] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId("web-" + Math.random().toString(36).slice(2, 9));
  }, []);

  const refreshAudit = useCallback(async () => {
    try {
      const [e, v] = await Promise.all([getAudit(), verifyAudit()]);
      setEntries(e);
      setVerify(v);
    } catch {}
  }, []);

  const refreshMember = useCallback(async (id: string) => {
    try {
      setMember(await getMember(id));
    } catch {}
  }, []);

  const refreshCases = useCallback(async () => {
    try {
      setCases(await listCases());
    } catch {}
  }, []);

  useEffect(() => {
    refreshAudit();
    refreshMember(memberId);
  }, [refreshAudit, refreshMember, memberId]);

  useEffect(() => {
    refreshCases();
    const t = setInterval(() => {
      refreshCases();
      refreshAudit();
      refreshMember(memberId);
    }, 2000);
    return () => clearInterval(t);
  }, [refreshCases, refreshAudit, refreshMember, memberId]);

  async function launchCase(
    intent: string,
    params: Record<string, unknown>,
    force_fail: boolean
  ) {
    setTab("cases");
    await startCase(memberId, intent, params, force_fail);
    refreshCases();
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 9e9, behavior: "smooth" });
  }, [messages]);

  // close fullscreen on Escape
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && setExpanded(false);
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  async function submit(text: string) {
    if (!text.trim() || busy || !sessionId) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const res = await sendChat(memberId, text, sessionId);
      setMessages((m) => [
        ...m,
        {
          role: "agent",
          text: res.resolution.message,
          status: res.resolution.status,
          classification: res.classification,
          escalation: res.resolution.escalation_summary,
        },
      ]);
      await refreshAudit();
      await refreshMember(memberId);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Could not reach the agent backend on :8010." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function onTamper(seq: number) {
    await tamperAudit(seq);
    await refreshAudit();
  }

  function toggleVoice() {
    const SR =
      (typeof window !== "undefined" &&
        ((window as any).SpeechRecognition ||
          (window as any).webkitSpeechRecognition)) ||
      null;
    if (!SR) {
      alert("Voice input needs Chrome (Web Speech API).");
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.onresult = (ev: any) => {
      const t = ev.results[0][0].transcript;
      setInput(t);
      submit(t);
    };
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }

  function DockContent({ full }: { full: boolean }) {
    return (
      <div className="min-h-0 flex-1 overflow-hidden">
        <div key={tab} className="tab-anim h-full">
          {tab === "cases" && (
            <div className="h-full overflow-auto">
              <CasesPanel cases={cases} onChanged={refreshCases} />
            </div>
          )}
          {tab === "audit" && (
            <AuditPanel
              entries={entries}
              verify={verify}
              onTamper={onTamper}
              onRefresh={refreshAudit}
            />
          )}
          {tab === "graph" && <GraphView key={`graph-${full ? "full" : "dock"}`} />}
        </div>
      </div>
    );
  }

  function DockBar({ full }: { full: boolean }) {
    const idx = TABS.findIndex(([t]) => t === tab);
    return (
      <div className="flex items-center gap-2">
        <div className="glass relative flex flex-1 rounded-2xl p-1">
          {/* sliding frosted indicator */}
          <span
            className="pointer-events-none absolute top-1 bottom-1 rounded-xl border border-white/80 bg-white shadow-[0_6px_16px_-6px_rgba(37,99,235,0.35)]"
            style={{
              left: `calc(0.25rem + ${idx} * ((100% - 0.5rem) / 3))`,
              width: "calc((100% - 0.5rem) / 3)",
              transition:
                "left 0.42s cubic-bezier(0.22,1,0.36,1), width 0.42s cubic-bezier(0.22,1,0.36,1)",
            }}
          />
          {TABS.map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`relative z-10 flex-1 rounded-xl px-3 py-2 text-xs font-semibold transition-colors duration-300 ${
                tab === t ? "text-blue-700" : "text-slate-500 hover:text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setExpanded(!full)}
          className="glass grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:text-slate-800"
          title={full ? "Exit fullscreen (Esc)" : "Expand"}
        >
          {full ? <IconMinimize /> : <IconExpand />}
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Top bar */}
      <header className="z-10 shrink-0 border-b border-white/60 bg-white/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-6 py-2.5">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-lg bg-blue-600 text-white">
              <IconMark />
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-blue-700">
                American Express · CodeStreet 2026
              </p>
              <h1 className="text-[15px] font-semibold leading-tight text-slate-900">
                End-to-End Servicing Agent
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden items-center gap-1 rounded-lg border border-slate-200 bg-white p-1 md:flex">
              {CASE_ACTIONS.map((a) => (
                <button
                  key={a.label}
                  onClick={() => launchCase(...a.run())}
                  className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${a.dot}`} />
                  {a.label}
                </button>
              ))}
            </div>
            <select
              value={memberId}
              onChange={(e) => {
                setMemberId(e.target.value);
                setMessages([]);
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-400"
            >
              {MEMBERS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full min-h-0 max-w-[1600px] flex-1 grid-cols-1 gap-4 px-6 py-4 lg:grid-cols-[1.5fr_1fr]">
        {/* LEFT: member + big chat */}
        <section className="flex min-h-0 flex-col gap-3">
          {member && (
            <div className="glass-panel grid shrink-0 grid-cols-3 gap-px overflow-hidden rounded-2xl text-sm sm:grid-cols-6">
              {[
                ["Member", member.name],
                ["Credit limit", `$${member.credit_limit.toLocaleString()}`],
                ["Card status", member.card_status],
                [
                  "Standing",
                  member.good_standing ? "Good" : "Delinquent",
                  member.good_standing ? "text-emerald-600" : "text-rose-600",
                ],
                ["Open fees", String(member.fees.filter((f) => !f.reversed).length)],
                ["Reversals", String(member.fee_reversals_used)],
              ].map(([label, value, cls]) => (
                <div key={label} className="bg-white/55 px-3 py-2.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    {label}
                  </p>
                  <p className={`truncate text-sm font-semibold capitalize text-slate-900 ${cls ?? ""}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="glass-panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl">
            <div className="shrink-0 border-b border-white/50 px-4 py-2.5">
              <h2 className="text-sm font-semibold text-slate-900">Conversation</h2>
            </div>
            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <div className="space-y-2 pt-6">
                  <p className="text-center text-xs font-medium text-slate-500">Try a request</p>
                  <div className="mx-auto flex max-w-xl flex-wrap justify-center gap-2">
                    {QUICK.map((q) => (
                      <button
                        key={q}
                        onClick={() => submit(q)}
                        className="rounded-full border border-white/70 bg-white/80 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                      m.role === "user"
                        ? "bg-blue-600 text-white shadow-sm"
                        : "border border-white/70 bg-white/90 text-slate-800 shadow-sm"
                    }`}
                  >
                    {m.role === "agent" && m.status && (
                      <div className="mb-1.5 flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize ${
                            STATUS_BADGE[m.status]
                          }`}
                        >
                          {m.status.replace("_", " ")}
                        </span>
                        {m.classification && (
                          <span className="text-[10px] font-medium text-slate-500">
                            {m.classification.intent} ·{" "}
                            {(m.classification.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    )}
                    <p className="leading-relaxed">{m.text}</p>
                    {m.escalation && (
                      <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-800">
                        <span className="font-semibold">
                          Handoff context sent to specialist:
                        </span>{" "}
                        {m.escalation}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="flex justify-start">
                  <div className="rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-400">
                    resolving…
                  </div>
                </div>
              )}
            </div>

            <div className="flex shrink-0 items-center gap-2 border-t border-white/50 p-3">
              <button
                onClick={toggleVoice}
                className={`grid h-9 w-9 place-items-center rounded-lg border text-sm transition ${
                  listening
                    ? "animate-pulse border-rose-300 bg-rose-50 text-rose-600"
                    : "border-slate-200 bg-white text-slate-500 hover:bg-slate-50"
                }`}
                title="Voice input (Chrome)"
              >
                <IconMic />
              </button>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit(input)}
                placeholder="Ask the servicing agent…"
                className="flex-1 rounded-lg border border-white/60 bg-white/70 px-3.5 py-2.5 text-sm text-slate-800 outline-none backdrop-blur-sm placeholder:text-slate-400 focus:border-blue-400"
              />
              <button
                onClick={() => submit(input)}
                disabled={busy}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
              >
                <IconSend /> Send
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT: dock */}
        <section className="flex min-h-0 flex-col gap-2">
          {DockBar({ full: false })}
          {expanded ? (
            <div className="grid flex-1 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white/70 text-sm text-slate-400 backdrop-blur-md">
              Panel opened in fullscreen — press Esc to return
            </div>
          ) : (
            DockContent({ full: false })
          )}
        </section>
      </main>

      {/* Fullscreen overlay */}
      {expanded && (
        <div className="fixed inset-0 z-50 bg-slate-900/30 p-4 backdrop-blur-sm">
          <div className="mx-auto flex h-full max-w-[1500px] flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="flex-1">{DockBar({ full: true })}</div>
              <button
                onClick={() => setExpanded(false)}
                className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 shadow-sm hover:bg-slate-50"
                title="Close (Esc)"
              >
                <IconClose />
              </button>
            </div>
            {DockContent({ full: true })}
          </div>
        </div>
      )}
    </div>
  );
}
