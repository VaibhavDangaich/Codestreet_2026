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

// --- Durable servicing cases (Temporal) ---
export type CaseState = {
  phase: string;
  intent: string | null;
  steps: string[];
  completed: string[];
  compensated: string[];
  current: string | null;
  failed: string | null;
  final: string | null;
  note: string | null;
};

export type Case = {
  case_id: string;
  member_id: string;
  intent: string;
  requires_approval: boolean;
  force_fail?: boolean;
  state: CaseState | null;
};

export async function startCase(
  member_id: string,
  intent: string,
  params: Record<string, unknown> = {},
  force_fail = false
) {
  const r = await fetch(`${BASE}/cases/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ member_id, intent, params, force_fail }),
  });
  return (await r.json()) as { case_id?: string; requires_approval?: boolean; error?: string };
}

export async function caseDecision(case_id: string, approved: boolean, note = "") {
  const r = await fetch(`${BASE}/cases/${case_id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, note }),
  });
  return (await r.json()) as { ok?: boolean };
}

export async function listCases() {
  const r = await fetch(`${BASE}/cases`);
  return ((await r.json()).cases ?? []) as Case[];
}

// --- audit graph (Neo4j) ---
export type GraphElement = { data: Record<string, string> };
export type GraphData = {
  nodes: GraphElement[];
  edges: GraphElement[];
  source: "neo4j" | "memory";
};

export async function getGraph() {
  const r = await fetch(`${BASE}/graph`);
  return (await r.json()) as GraphData;
}
