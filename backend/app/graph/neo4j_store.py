"""Persist the audit trail to Neo4j Aura and read it back as a graph.

Writes are incremental (only new entries) and idempotent (MERGE). Reads return
the same Cytoscape shape as app.graph.model. If Neo4j is unreachable (e.g. the
Aura instance is still provisioning), callers fall back to the in-memory model,
with a short cooldown so we don't hammer a dead endpoint on every poll.
"""
from __future__ import annotations

import os
import time
from typing import Any

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

_driver = None
_synced = 0            # highest seq already written
_cooldown_until = 0.0  # monotonic time; skip Neo4j until then after a failure

_UPSERT = """
UNWIND $rows AS row
MERGE (en:Entry {seq: row.seq})
  SET en.action = row.action, en.ts = row.ts, en.hash = row.hash,
      en.prev_hash = row.prev_hash, en.actor = row.actor
MERGE (ac:Actor {name: row.actor})
MERGE (m:Member {id: row.member})
MERGE (se:Session {id: row.session})
MERGE (en)-[:PERFORMED_BY]->(ac)
MERGE (en)-[:ON]->(m)
MERGE (en)-[:IN]->(se)
"""

_CHAIN = """
UNWIND $rows AS row
MATCH (p:Entry {hash: row.prev_hash}), (e:Entry {seq: row.seq})
MERGE (p)-[:NEXT]->(e)
"""

_READ_NODES = """
MATCH (n)
RETURN labels(n)[0] AS type,
       coalesce(toString(n.seq), n.name, n.id) AS key,
       n.action AS action
"""

_READ_RELS = """
MATCH (a)-[r]->(b)
RETURN type(r) AS rel,
       labels(a)[0] AS at, coalesce(toString(a.seq), a.name, a.id) AS ak,
       labels(b)[0] AS bt, coalesce(toString(b.seq), b.name, b.id) AS bk
"""


def configured() -> bool:
    return bool(NEO4J_URI and NEO4J_PASSWORD)


def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        _driver = GraphDatabase.driver(NEO4J_URI,
                                       auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return _driver


def _cool() -> bool:
    return time.monotonic() < _cooldown_until


def _trip():
    global _cooldown_until
    _cooldown_until = time.monotonic() + 30.0


def sync_and_read(entries: list[dict]) -> dict[str, Any] | None:
    """Push new entries, then read the whole graph. None if Neo4j is unavailable."""
    global _synced, _driver
    if not configured() or _cool():
        return None
    try:
        driver = _get_driver()
        new = [e for e in entries if e["seq"] >= _synced]
        rows = [{"seq": e["seq"], "action": e["action"], "ts": e["ts"],
                 "hash": e["hash"], "prev_hash": e["prev_hash"],
                 "actor": e["actor"], "member": e["member_id"],
                 "session": e["session_id"]} for e in new]
        with driver.session(database=NEO4J_DATABASE) as s:
            if rows:
                s.run(_UPSERT, rows=rows)
                s.run(_CHAIN, rows=rows)
            node_recs = list(s.run(_READ_NODES))
            rel_recs = list(s.run(_READ_RELS))
        if entries:
            _synced = max(e["seq"] for e in entries) + 1

        nodes = []
        for r in node_recs:
            t = (r["type"] or "").lower()
            key = r["key"]
            label = f"#{key} {r['action']}" if t == "entry" else key
            nodes.append({"data": {"id": f"{t}:{key}", "label": label, "type": t}})
        edges = []
        for r in rel_recs:
            at, bt = r["at"].lower(), r["bt"].lower()
            src, dst = f"{at}:{r['ak']}", f"{bt}:{r['bk']}"
            edges.append({"data": {"id": f"{src}->{dst}:{r['rel']}",
                                   "source": src, "target": dst, "label": r["rel"]}})
        return {"nodes": nodes, "edges": edges}
    except Exception:
        # drop a stale connection so the next call reconnects
        try:
            if _driver is not None:
                _driver.close()
        except Exception:
            pass
        _driver = None
        _trip()
        return None
