"use client";

import { useEffect, useRef, useState } from "react";
import { GraphData, getGraph } from "../lib/api";

const TYPE_COLOR: Record<string, string> = {
  entry: "#2563EB",
  actor: "#7C3AED",
  member: "#059669",
  session: "#D97706",
  rule: "#DB2777",
};

const LEGEND = [
  ["entry", "Audit entry"],
  ["actor", "Actor"],
  ["member", "Member"],
  ["session", "Session"],
  ["rule", "Policy rule"],
];

export default function GraphView() {
  const boxRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const countRef = useRef(0);
  const [source, setSource] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    let timer: any;

    async function boot() {
      const cytoscape: any = (await import("cytoscape")).default;
      if (cancelled || !boxRef.current) return;

      cyRef.current = cytoscape({
        container: boxRef.current,
        wheelSensitivity: 0.2,
        style: [
          {
            selector: "node",
            style: {
              "background-color": (n: any) => TYPE_COLOR[n.data("type")] ?? "#94A3B8",
              label: "data(label)",
              color: "#334155",
              "font-size": 9,
              "font-weight": 500,
              // entries read like log lines beside the spine; other nodes label below
              "text-valign": (n: any) =>
                n.data("type") === "entry" ? "center" : "bottom",
              "text-halign": (n: any) =>
                n.data("type") === "entry" ? "right" : "center",
              "text-margin-x": (n: any) => (n.data("type") === "entry" ? 6 : 0),
              "text-margin-y": (n: any) => (n.data("type") === "entry" ? 0 : 4),
              width: (n: any) => (n.data("type") === "entry" ? 18 : 28),
              height: (n: any) => (n.data("type") === "entry" ? 18 : 28),
              "border-width": 3,
              "border-color": "#ffffff",
            },
          },
          {
            selector: "edge",
            style: {
              width: 1.2,
              "line-color": "#93A5BC",
              "line-opacity": 0.75,
              "target-arrow-color": "#64748B",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.6,
              "curve-style": "straight",
              // only APPLIED_RULE gets a label — the spine's arrows already read
              // as sequence, and column position implies IN / ON / PERFORMED_BY
              label: (e: any) =>
                e.data("label") === "APPLIED_RULE" ? "APPLIED_RULE" : "",
              "font-size": 7,
              color: "#DB2777",
              "text-rotation": "autorotate",
              "text-background-color": "#ffffff",
              "text-background-opacity": 0.85,
              "text-background-padding": "1px",
            },
          },
          {
            selector: 'edge[label = "NEXT"]',
            style: {
              width: 2.5,
              "line-color": "#2563EB",
              "target-arrow-color": "#2563EB",
              "line-opacity": 1,
            },
          },
          {
            selector: 'edge[label = "APPLIED_RULE"]',
            style: {
              width: 1.8,
              "line-color": "#DB2777",
              "target-arrow-color": "#DB2777",
              "line-style": "dashed",
              "line-opacity": 1,
              color: "#DB2777",
            },
          },
        ],
        layout: { name: "preset" },
      });
      refresh(true);
      timer = setInterval(() => refresh(false), 4000);
    }

    async function refresh(first: boolean) {
      try {
        const g: GraphData = await getGraph();
        if (cancelled || !cyRef.current) return;
        setSource(g.source);
        const total = g.nodes.length + g.edges.length;
        if (!first && total === countRef.current) return;
        countRef.current = total;
        const cy = cyRef.current;
        cy.elements().remove();

        // --- timeline layout: entries top->bottom in seq order (the spine),
        // supporting nodes in columns, aligned to the entries they touch ---
        const seqOf = (id: string) => parseInt(id.split(":")[1] ?? "0", 10);
        const entryIds = g.nodes
          .filter((n) => n.data.type === "entry")
          .map((n) => n.data.id)
          .sort((a, b) => seqOf(a) - seqOf(b));
        const pos: Record<string, { x: number; y: number }> = {};
        entryIds.forEach((id, i) => (pos[id] = { x: 0, y: i * 90 }));

        // column x per supporting type
        const colX: Record<string, number> = {
          actor: -320,
          session: -520,
          member: -700,
          rule: 340,
        };
        // avg y of the entries each supporting node connects to
        const touch: Record<string, number[]> = {};
        for (const e of g.edges) {
          const { source, target } = e.data;
          const [ent, other] =
            source.startsWith("entry:") && !target.startsWith("entry:")
              ? [source, target]
              : target.startsWith("entry:") && !source.startsWith("entry:")
              ? [target, source]
              : [null, null];
          if (ent && other && pos[ent]) {
            (touch[other] ??= []).push(pos[ent].y);
          }
        }
        // place each column, avoiding overlaps within it
        for (const type of Object.keys(colX)) {
          const nodes = g.nodes
            .filter((n) => n.data.type === type)
            .map((n) => ({
              id: n.data.id,
              y: touch[n.data.id]?.length
                ? touch[n.data.id].reduce((a, b) => a + b, 0) /
                  touch[n.data.id].length
                : 0,
            }))
            .sort((a, b) => a.y - b.y);
          let prev = -Infinity;
          for (const n of nodes) {
            const y = Math.max(n.y, prev + 70);
            pos[n.id] = { x: colX[type], y };
            prev = y;
          }
        }

        cy.add([
          ...g.nodes.map((n) => ({ ...n, position: pos[n.data.id] })),
          ...g.edges,
        ]);
        cy.layout({ name: "preset", animate: false }).run();
        cy.fit(undefined, 30);
      } catch (e: any) {
        setError(String(e?.message ?? e));
      }
    }

    boot();
    return () => {
      cancelled = true;
      clearInterval(timer);
      cyRef.current?.destroy?.();
    };
  }, []);

  return (
    <div className="glass-panel flex h-full flex-col overflow-hidden rounded-2xl">
      <div className="flex items-center justify-between border-b border-white/50 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Audit Graph</h2>
          <p className="text-[11px] font-medium text-slate-500">
            Analyst view · chain-of-custody as a graph
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden gap-2.5 text-[10px] sm:flex">
            {LEGEND.map(([t, label]) => (
              <span key={t} className="flex items-center gap-1 font-medium text-slate-600">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: TYPE_COLOR[t] }}
                />
                {label}
              </span>
            ))}
          </div>
          {source && (
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${
                source === "neo4j"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-amber-200 bg-amber-50 text-amber-700"
              }`}
              title={source === "neo4j" ? "Backed by Neo4j Aura" : "Neo4j unavailable — memory fallback"}
            >
              {source === "neo4j" ? "Neo4j" : "memory"}
            </span>
          )}
        </div>
      </div>
      <div ref={boxRef} className="min-h-[520px] flex-1 bg-white/20" />
      {error && <p className="px-4 py-2 text-[11px] text-rose-500">{error}</p>}
    </div>
  );
}
