import { SVGProps } from "react";

const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function IconMark(p: SVGProps<SVGSVGElement>) {
  // a card + check — the servicing mark
  return (
    <svg viewBox="0 0 24 24" width={20} height={20} {...base} {...p}>
      <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
      <path d="M2.5 9.5h19" />
      <path d="M6.5 15.5l2 2 4-4.5" />
    </svg>
  );
}

export function IconMic(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} {...base} {...p}>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </svg>
  );
}

export function IconSend(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} {...base} {...p}>
      <path d="M4 12l16-7-7 16-2.5-6.5L4 12z" />
    </svg>
  );
}

export function IconRefresh(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} {...base} {...p}>
      <path d="M20 11a8 8 0 1 0-.8 4.5" />
      <path d="M20 5v6h-6" />
    </svg>
  );
}

export function IconShield(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={16} height={16} {...base} {...p}>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

export function IconLink(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} {...base} {...p}>
      <path d="M9 15l6-6" />
      <path d="M8 12l-2 2a3 3 0 1 0 4 4l2-2" />
      <path d="M16 12l2-2a3 3 0 1 0-4-4l-2 2" />
    </svg>
  );
}

export function IconPlus(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width={15} height={15} {...base} {...p}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
