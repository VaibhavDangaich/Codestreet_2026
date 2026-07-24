const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8010";

export type Resolution = {
  status: "resolved" | "escalated" | "needs_info" | "rejected";
  message: string;
  intent: string;
  details: Record<string, unknown>;
  escalation_summary: string | null;
};

export type Classification = {
  intent: string;
  confidence: number;
  extracted_fields: Record<string, unknown>;
  rationale: string;
};

export type ChatResponse = {
  resolution: Resolution;
  classification: Classification | null;
};

export type AuditEntry = {
  seq: number;
  ts: string;
  session_id: string;
  member_id: string;
  actor: string;
  action: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
};

export type Member = {
  member_id: string;
  name: string;
  credit_limit: number;
  good_standing: boolean;
  fee_reversals_used: number;
  fees: { fee_id: string; kind: string; amount: number; reversed: boolean }[];
  card_status: string;
};

export type Verify = { intact: boolean; broken_at_seq: number | null; total: number };

export async function sendChat(member_id: string, message: string, session_id: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id, message, session_id }),
  });
  return (await r.json()) as ChatResponse;
}

export async function getAudit(session_id?: string) {
  const q = session_id ? `?session_id=${session_id}` : "";
  const r = await fetch(`${BASE}/audit${q}`);
  return ((await r.json()).entries ?? []) as AuditEntry[];
}

export async function verifyAudit() {
  const r = await fetch(`${BASE}/audit/verify`);
  return (await r.json()) as Verify;
}

export async function tamperAudit(seq: number) {
  const r = await fetch(`${BASE}/audit/tamper`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ seq }),
  });
  return (await r.json()) as { tampered: boolean; verify: Verify };
}

export async function getMember(member_id: string) {
  const r = await fetch(`${BASE}/member/${member_id}`);
  return (await r.json()) as Member;
}

export type Alert = {
  id: string;
  member_id: string;
  ts: string;
  reason: string;
  txn: { id: string; merchant: string; amount: number; city: string };
  action: string;
};

export async function getAlerts(member_id?: string) {
  const q = member_id ? `?member_id=${member_id}` : "";
  const r = await fetch(`${BASE}/alerts${q}`);
  return ((await r.json()).alerts ?? []) as Alert[];
}

export async function simulateSuspicious(member_id: string) {
  const r = await fetch(`${BASE}/simulate/suspicious/${member_id}`, {
    method: "POST",
  });
  return (await r.json()) as { injected?: Record<string, unknown> };
}
