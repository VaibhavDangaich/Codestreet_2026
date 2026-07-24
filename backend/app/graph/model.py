"""Build a Cytoscape-ready graph from audit entries.

Graph model (an analyst view of the audit trail):
  (Session)  --IN--   (Entry)  --BY--   (Actor)
                         |  --ON--       (Member)
  (Entry) --NEXT--> (Entry)   # the SHA-256 hash chain, in order

The same shape is produced whether we read from Neo4j or fall back to memory,
so the frontend renders identically either way.
"""
from __future__ import annotations

from typing import Any

GENESIS = "0" * 64


def build_graph_from_entries(entries: list[dict]) -> dict[str, Any]:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(nid: str, label: str, ntype: str, **extra):
        if nid not in nodes:
            nodes[nid] = {"data": {"id": nid, "label": label, "type": ntype, **extra}}

    for e in entries:
        eid = f"entry:{e['seq']}"
        add_node(eid, f"#{e['seq']} {e['action']}", "entry",
                 actor=e["actor"], ts=e["ts"])
        aid = f"actor:{e['actor']}"
        add_node(aid, e["actor"], "actor")
        mid = f"member:{e['member_id']}"
        add_node(mid, e["member_id"], "member")
        sid = f"session:{e['session_id']}"
        add_node(sid, e["session_id"], "session")
        edges.append({"data": {"id": f"{eid}-by", "source": eid, "target": aid,
                               "label": "BY"}})
        edges.append({"data": {"id": f"{eid}-on", "source": eid, "target": mid,
                               "label": "ON"}})
        edges.append({"data": {"id": f"{eid}-in", "source": eid, "target": sid,
                               "label": "IN"}})

    by_hash = {e["hash"]: e["seq"] for e in entries}
    for e in entries:
        if e["prev_hash"] in by_hash:
            edges.append({"data": {
                "id": f"chain-{e['seq']}",
                "source": f"entry:{by_hash[e['prev_hash']]}",
                "target": f"entry:{e['seq']}", "label": "NEXT"}})

    return {"nodes": list(nodes.values()), "edges": edges}
