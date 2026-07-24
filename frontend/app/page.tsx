"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import AuditPanel from "./components/AuditPanel";
import CasesPanel from "./components/CasesPanel";
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
  "Please bump my credit limit to $50,000.",
];

const STATUS_BADGE: Record<string, string> = {
  resolved: "border-emerald-500/40 bg-emerald-500/15 text-emerald-300",
  escalated: "border-amber-500/40 bg-amber-500/15 text-amber-300",
  needs_info: "border-sky-500/40 bg-sky-500/15 text-sky-300",
  rejected: "border-rose-500/40 bg-rose-500/15 text-rose-300",
  answered: "border-violet-500/40 bg-violet-500/15 text-violet-300",
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
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // one session per browser load
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

  // Poll so durable cases advance live in the UI (Temporal workflow progressing),
  // and autonomous audit entries surface even without chatting.
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
    force_fail = false
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
        { role: "agent", text: "⚠ Could not reach the agent backend on :8010." },
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
    <div className="min-h-screen bg-[radial-gradient(120%_120%_at_80%_-10%,#12203a_0%,#070b14_55%)] text-white">
      <header className="border-b border-white/10 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">
              End-to-End Servicing Agent
            </h1>
            <p className="text-xs text-white/40">
              Resolves fee reversals · limit increases · card replacements — with
              a verifiable audit trail
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => launchCase("card_replacement", { fee: 0 })}
              title="Durable saga: block old card → charge → order → notify"
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/20"
            >
              Replace card
            </button>
            <button
              onClick={() => launchCase("card_replacement", {}, true)}
              title="Force the fulfillment step to fail — watch the saga auto-roll-back"
              className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-200 hover:bg-amber-500/20"
            >
              Replace ✕ fail → rollback
            </button>
            <button
              onClick={() => launchCase("limit_increase", { new_limit: 50000 })}
              title="Over-policy → durably waits for underwriter approval"
              className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-200 hover:bg-sky-500/20"
            >
              $50k limit → approval
            </button>
            <select
              value={memberId}
              onChange={(e) => {
                setMemberId(e.target.value);
                setMessages([]);
              }}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none"
            >
              {MEMBERS.map((m) => (
                <option key={m.id} value={m.id} className="bg-slate-900">
                  {m.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {/* Durable servicing cases — the Temporal showcase */}
      <div className="mx-auto max-w-7xl px-6 pt-4">
        <CasesPanel cases={cases} onChanged={refreshCases} />
      </div>

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-6 py-5 lg:grid-cols-2">
        {/* LEFT: chat + member */}
        <section className="flex flex-col gap-4">
          {member && (
            <div className="grid grid-cols-3 gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm">
              <div>
                <p className="text-[11px] text-white/40">Member</p>
                <p className="font-medium">{member.name}</p>
              </div>
              <div>
                <p className="text-[11px] text-white/40">Credit limit</p>
                <p className="font-medium">
                  ${member.credit_limit.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-white/40">Card status</p>
                <p className="font-medium capitalize">{member.card_status}</p>
              </div>
              <div>
                <p className="text-[11px] text-white/40">Standing</p>
                <p
                  className={
                    member.good_standing ? "text-emerald-300" : "text-rose-300"
                  }
                >
                  {member.good_standing ? "Good" : "Delinquent"}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-white/40">Open fees</p>
                <p className="font-medium">
                  {member.fees.filter((f) => !f.reversed).length}
                </p>
              </div>
              <div>
                <p className="text-[11px] text-white/40">Reversals used</p>
                <p className="font-medium">{member.fee_reversals_used}</p>
              </div>
            </div>
          )}

          <div className="flex min-h-[420px] flex-1 flex-col rounded-2xl border border-white/10 bg-black/30 backdrop-blur">
            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <div className="space-y-2 pt-6">
                  <p className="text-center text-sm text-white/40">
                    Try a request:
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {QUICK.map((q) => (
                      <button
                        key={q}
                        onClick={() => submit(q)}
                        className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 hover:bg-white/10"
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
                        ? "bg-sky-600 text-white"
                        : "border border-white/10 bg-white/5 text-white/90"
                    }`}
                  >
                    {m.role === "agent" && m.status && (
                      <div className="mb-1.5 flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                            STATUS_BADGE[m.status]
                          }`}
                        >
                          {m.status.replace("_", " ")}
                        </span>
                        {m.classification && (
                          <span className="text-[10px] text-white/40">
                            {m.classification.intent} ·{" "}
                            {(m.classification.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    )}
                    <p>{m.text}</p>
                    {m.escalation && (
                      <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-[11px] text-amber-200/90">
                        <span className="font-semibold">
                          👤 Handoff context sent to specialist:
                        </span>{" "}
                        {m.escalation}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {busy && (
                <div className="flex justify-start">
                  <div className="rounded-2xl border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white/40">
                    resolving…
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 border-t border-white/10 p-3">
              <button
                onClick={toggleVoice}
                className={`grid h-9 w-9 place-items-center rounded-lg border text-sm ${
                  listening
                    ? "animate-pulse border-rose-500/50 bg-rose-500/20 text-rose-300"
                    : "border-white/10 bg-white/5 text-white/60 hover:bg-white/10"
                }`}
                title="Voice input (Chrome)"
              >
                🎤
              </button>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit(input)}
                placeholder="Ask the servicing agent…"
                className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none placeholder:text-white/30"
              />
              <button
                onClick={() => submit(input)}
                disabled={busy}
                className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </div>
        </section>

        {/* RIGHT: audit trail */}
        <section className="h-[calc(100vh-8rem)] lg:sticky lg:top-4">
          <AuditPanel
            entries={entries}
            verify={verify}
            onTamper={onTamper}
            onRefresh={refreshAudit}
          />
        </section>
      </main>
    </div>
  );
}
