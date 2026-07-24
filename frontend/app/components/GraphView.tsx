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
              "text-valign": "bottom",
              "text-margin-y": 4,
              width: (n: any) => (n.data("type") === "entry" ? 18 : 28),
              height: (n: any) => (n.data("type") === "entry" ? 18 : 28),
              "border-width": 3,
              "border-color": "#ffffff",
            },
          },
          {
            selector: "edge",
            style: {
              width: 1,
              "line-color": "#CBD5E1",
              "target-arrow-color": "#94A3B8",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.7,
              "curve-style": "bezier",
              label: "data(label)",
              "font-size": 7,
              color: "#94A3B8",
              "text-rotation": "autorotate",
            },
          },
          {
            selector: 'edge[label = "NEXT"]',
            style: {
              width: 2.5,
              "line-color": "#2563EB",
              "target-arrow-color": "#2563EB",
            },
          },
        ],
        layout: { name: "grid" },
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
        cy.add([...g.nodes, ...g.edges]);
        cy.layout({
          name: "cose",
          animate: false,
          nodeRepulsion: 6000,
          idealEdgeLength: 70,
          padding: 30,
        }).run();
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
