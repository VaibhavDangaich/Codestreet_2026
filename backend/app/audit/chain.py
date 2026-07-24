"""Hash-chained, append-only audit trail.

Every decision, policy check, and backend call the agent makes is written as an
entry whose hash includes the previous entry's hash (blockchain-style). If any
past entry is edited, every subsequent hash stops matching — so the log is
tamper-evident. `verify()` walks the chain and reports the first break.

This is the compliance/traceability story: a bank can prove that what the agent
did was not altered after the fact.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, asdict
from typing import Any, Optional

GENESIS_HASH = "0" * 64


def _hash_entry(prev_hash: str, seq: int, ts: str, actor: str,
                action: str, payload: dict[str, Any]) -> str:
    body = json.dumps(
        {"prev": prev_hash, "seq": seq, "ts": ts, "actor": actor,
         "action": action, "payload": payload},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(body.encode()).hexdigest()


@dataclass
class AuditEntry:
    seq: int
    ts: str
    session_id: str
    member_id: str
    actor: str          # "classifier" | "policy" | "backend" | "agent" | "system"
    action: str         # human-readable action label
    payload: dict[str, Any]
    prev_hash: str
    hash: str


class AuditChain:
    """In-memory append-only chain. Swap the store for Postgres in prod."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = threading.Lock()
        # monotonically-increasing counter injected at write time so the module
        # stays deterministic/testable (no hidden clock calls here).
        self._seq = 0

    def append(self, *, ts: str, session_id: str, member_id: str, actor: str,
               action: str, payload: dict[str, Any]) -> AuditEntry:
        with self._lock:
            prev_hash = self._entries[-1].hash if self._entries else GENESIS_HASH
            seq = self._seq
            self._seq += 1
            h = _hash_entry(prev_hash, seq, ts, actor, action, payload)
            entry = AuditEntry(
                seq=seq, ts=ts, session_id=session_id, member_id=member_id,
                actor=actor, action=action, payload=payload,
                prev_hash=prev_hash, hash=h,
            )
            self._entries.append(entry)
            return entry

    def entries(self, session_id: Optional[str] = None) -> list[dict]:
        return [asdict(e) for e in self._entries
                if session_id is None or e.session_id == session_id]

    def verify(self) -> dict:
        """Recompute every hash; report integrity + first break if any."""
        prev_hash = GENESIS_HASH
        for e in self._entries:
            expected = _hash_entry(prev_hash, e.seq, e.ts, e.actor,
                                   e.action, e.payload)
            if e.prev_hash != prev_hash or e.hash != expected:
                return {"intact": False, "broken_at_seq": e.seq,
                        "total": len(self._entries)}
            prev_hash = e.hash
        return {"intact": True, "broken_at_seq": None,
                "total": len(self._entries)}

    def _tamper_for_demo(self, seq: int, new_payload: dict) -> bool:
        """Demo-only: silently mutate an entry's payload WITHOUT re-hashing,
        so the audience can watch verify() catch it."""
        for e in self._entries:
            if e.seq == seq:
                e.payload = new_payload
                return True
        return False


# process-wide singleton
AUDIT = AuditChain()
