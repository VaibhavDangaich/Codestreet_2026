"use client";

import { useEffect, useRef, useState } from "react";
import { GraphData, getGraph } from "../lib/api";

const TYPE_COLOR: Record<string, string> = {
  entry: "#2E8BF0",
  actor: "#A68BF0",
  member: "#3FD08A",
  session: "#F2B04B",
};

const LEGEND = [
  ["entry", "Audit entry"],
  ["actor", "Actor"],
  ["member", "Member"],
  ["session", "Session"],
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
              "background-color": (n: any) => TYPE_COLOR[n.data("type")] ?? "#888",
              label: "data(label)",
              color: "#dbe4f0",
              "font-size": 9,
              "text-valign": "bottom",
              "text-margin-y": 3,
              width: (n: any) => (n.data("type") === "entry" ? 20 : 30),
              height: (n: any) => (n.data("type") === "entry" ? 20 : 30),
              "border-width": 2,
              "border-color": (n: any) =>
                TYPE_COLOR[n.data("type")] ?? "#888",
              "border-opacity": 0.4,
            },
          },
          {
            selector: "edge",
            style: {
              width: 1,
              "line-color": "rgba(255,255,255,0.15)",
              "target-arrow-color": "rgba(255,255,255,0.25)",
              "target-arrow-shape": "triangle",
              "arrow-scale": 0.7,
              "curve-style": "bezier",
              label: "data(label)",
              "font-size": 7,
              color: "rgba(255,255,255,0.35)",
              "text-rotation": "autorotate",
            },
          },
          {
            // highlight the hash chain (the immutable ledger)
            selector: 'edge[label = "NEXT"]',
            style: {
              width: 2.5,
              "line-color": "#2E8BF0",
              "target-arrow-color": "#2E8BF0",
              "line-style": "solid",
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
        if (!first && total === countRef.current) return; // no change, avoid jitter
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
    <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-black/30 backdrop-blur">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-white">Audit Graph</h2>
          <p className="text-[11px] text-white/40">
            Analyst view · chain-of-custody as a graph
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-2 text-[10px]">
            {LEGEND.map(([t, label]) => (
              <span key={t} className="flex items-center gap-1 text-white/50">
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
                  ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/15 text-amber-300"
              }`}
              title={source === "neo4j" ? "Backed by Neo4j Aura" : "Neo4j unavailable — memory fallback"}
            >
              {source === "neo4j" ? "● Neo4j" : "● memory"}
            </span>
          )}
        </div>
      </div>
      <div ref={boxRef} className="min-h-[520px] flex-1" />
      {error && (
        <p className="px-4 py-2 text-[11px] text-rose-300/70">{error}</p>
      )}
    </div>
  );
}
