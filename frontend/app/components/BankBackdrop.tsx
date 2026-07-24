"use client";

import { useEffect, useRef } from "react";

/**
 * Very subtle, banking-themed animated backdrop:
 *  - faint "decrypting" digit/currency streams (numbers scramble then settle)
 *  - a few translucent drifting credit cards
 * Kept deliberately low-contrast and blurred so any text above stays readable.
 */
export default function BankBackdrop() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;
    let dpr = 1;
    const GLYPHS = "0123456789$€£₹•".split("");

    type Col = { x: number; y: number; speed: number; glyphs: string[]; flip: number[] };
    let cols: Col[] = [];
    type Card = { x: number; y: number; vx: number; vy: number; rot: number; vr: number; hue: number };
    let cards: Card[] = [];

    function rand(a: number, b: number) {
      return a + Math.random() * (b - a);
    }

    function build() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      canvas!.style.width = w + "px";
      canvas!.style.height = h + "px";
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

      const spacing = 34;
      const n = Math.floor(w / spacing);
      cols = Array.from({ length: n }, (_, i) => {
        const rows = Math.floor(h / 22) + 2;
        return {
          x: i * spacing + spacing / 2,
          y: rand(-h, 0),
          speed: rand(8, 22),
          glyphs: Array.from({ length: rows }, () => GLYPHS[(Math.random() * GLYPHS.length) | 0]),
          flip: Array.from({ length: rows }, () => Math.random()),
        };
      });

      const cardCount = w < 900 ? 2 : 4;
      cards = Array.from({ length: cardCount }, () => ({
        x: rand(0, w),
        y: rand(0, h),
        vx: rand(-6, 6),
        vy: rand(-4, 4),
        rot: rand(-0.3, 0.3),
        vr: rand(-0.02, 0.02),
        hue: rand(210, 250),
      }));
    }

    function drawCard(c: Card) {
      const cw = 210;
      const ch = 132;
      ctx!.save();
      ctx!.translate(c.x, c.y);
      ctx!.rotate(c.rot);
      ctx!.globalAlpha = 0.1;
      const g = ctx!.createLinearGradient(-cw / 2, -ch / 2, cw / 2, ch / 2);
      g.addColorStop(0, `hsl(${c.hue}, 70%, 55%)`);
      g.addColorStop(1, `hsl(${c.hue + 30}, 70%, 60%)`);
      ctx!.fillStyle = g;
      const r = 16;
      ctx!.beginPath();
      ctx!.roundRect(-cw / 2, -ch / 2, cw, ch, r);
      ctx!.fill();
      // chip
      ctx!.globalAlpha = 0.09;
      ctx!.fillStyle = "#c9a227";
      ctx!.beginPath();
      ctx!.roundRect(-cw / 2 + 22, -ch / 2 + 30, 34, 26, 5);
      ctx!.fill();
      // masked number
      ctx!.globalAlpha = 0.08;
      ctx!.fillStyle = "#0f172a";
      ctx!.font = "600 15px ui-monospace, monospace";
      ctx!.fillText("••••  ••••  ••••  4242", -cw / 2 + 20, ch / 2 - 26);
      ctx!.restore();
    }

    let last = 0;
    let raf = 0;
    function frame(t: number) {
      raf = requestAnimationFrame(frame);
      const dt = Math.min((t - last) / 1000, 0.05);
      if (t - last < 33) return; // ~30fps cap
      last = t;
      ctx!.clearRect(0, 0, w, h);

      // digit streams
      ctx!.font = "13px ui-monospace, SFMono-Regular, monospace";
      for (const col of cols) {
        col.y += col.speed * dt;
        if (col.y > h + 40) col.y = rand(-h * 0.6, -20);
        for (let i = 0; i < col.glyphs.length; i++) {
          const gy = col.y + i * 22;
          if (gy < -20 || gy > h + 20) continue;
          // occasionally "decrypt" (swap the glyph)
          col.flip[i] -= dt;
          if (col.flip[i] <= 0) {
            col.glyphs[i] = GLYPHS[(Math.random() * GLYPHS.length) | 0];
            col.flip[i] = rand(0.4, 2.2);
          }
          const head = i === col.glyphs.length - 1;
          ctx!.fillStyle = head
            ? "rgba(37,99,235,0.5)"
            : `rgba(51,65,85,${0.1 + (i / col.glyphs.length) * 0.22})`;
          ctx!.fillText(col.glyphs[i], col.x, gy);
        }
      }

      // drifting cards
      for (const c of cards) {
        c.x += c.vx * dt;
        c.y += c.vy * dt;
        c.rot += c.vr * dt;
        if (c.x < -140) c.x = w + 140;
        if (c.x > w + 140) c.x = -140;
        if (c.y < -120) c.y = h + 120;
        if (c.y > h + 120) c.y = -120;
        drawCard(c);
      }
    }

    build();
    raf = requestAnimationFrame(frame);
    const onResize = () => build();
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10"
      style={{ filter: "blur(0.4px)" }}
    />
  );
}
