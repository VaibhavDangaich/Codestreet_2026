"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AuditPanel from "./components/AuditPanel";
import CasesPanel from "./components/CasesPanel";
import GraphView from "./components/GraphView";
import { IconMark, IconMic, IconSend } from "./components/icons";
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

const CASE_ACTIONS: { label: string; dot: string; run: () => [string, Record<string, unknown>, boolean] }[] = [
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
  const [rightTab, setRightTab] = useState<"audit" | "graph">("audit");
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
    } catch {
      /* backend not up yet */
    }
  }, []);

  const refreshMember = useCallback(async (id: string) => {
    try {
      setMember(await getMember(id));
    } catch {
      /* ignore */
    }
  }, []);

  const refreshCases = useCallback(async () => {
    try {
      setCases(await listCases());
    } catch {
      /* ignore */
    }
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
    await startCase(memberId, intent, params, force_fail);
    refreshCases();
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 9e9, behavior: "smooth" });
  }, [messages]);

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

  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-3">
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

      <div className="mx-auto max-w-7xl px-6 pt-4">
        <CasesPanel cases={cases} onChanged={refreshCases} />
      </div>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-6 py-4 lg:grid-cols-2">
        {/* LEFT: member + chat */}
        <section className="flex flex-col gap-4">
          {member && (
            <div className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-slate-200 bg-slate-200 text-sm shadow-sm">
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
                ["Reversals used", String(member.fee_reversals_used)],
              ].map(([label, value, cls]) => (
                <div key={label} className="bg-white px-4 py-3">
                  <p className="text-[11px] text-slate-400">{label}</p>
                  <p className={`font-medium capitalize text-slate-800 ${cls ?? ""}`}>
                    {value}
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="flex min-h-[440px] flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-4 py-2.5">
              <h2 className="text-sm font-semibold text-slate-900">Conversation</h2>
            </div>
            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <div className="space-y-2 pt-6">
                  <p className="text-center text-xs text-slate-400">
                    Try a request
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {QUICK.map((q) => (
                      <button
                        key={q}
                        onClick={() => submit(q)}
                        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700"
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
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
                      m.role === "user"
                        ? "bg-blue-600 text-white"
                        : "border border-slate-200 bg-white text-slate-700"
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
                          <span className="text-[10px] text-slate-400">
                            {m.classification.intent} ·{" "}
                            {(m.classification.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    )}
                    <p>{m.text}</p>
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
                  <div className="rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-400">
                    resolving…
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 border-t border-slate-200 p-3">
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
                className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 focus:border-blue-400"
              />
              <button
                onClick={() => submit(input)}
                disabled={busy}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
              >
                <IconSend /> Send
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT: audit trail / graph */}
        <section className="flex h-[calc(100vh-8rem)] flex-col gap-2 lg:sticky lg:top-[4.5rem]">
          <div className="flex gap-1 rounded-lg border border-slate-200 bg-white p-1 text-xs shadow-sm">
            {(["audit", "graph"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setRightTab(t)}
                className={`flex-1 rounded-md px-3 py-1.5 font-medium transition ${
                  rightTab === t
                    ? "bg-blue-600 text-white"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {t === "audit" ? "Audit trail" : "Audit graph"}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1">
            {rightTab === "audit" ? (
              <AuditPanel
                entries={entries}
                verify={verify}
                onTamper={onTamper}
                onRefresh={refreshAudit}
              />
            ) : (
              <GraphView />
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
