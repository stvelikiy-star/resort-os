"use client";

/**
 * MARINA SMART Future Luxury 2.0 — shared Web primitives (Admin).
 * Presentation only: no fetching, no business logic, no invented values. Styles: app/fl2-foundation.css.
 * Every number rendered through these components must come from the caller's real API data.
 */
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "info" | "neutral";
const rise = (i = 0): CSSProperties => ({ "--i": Math.min(i, 8) } as CSSProperties);

/** true one frame after mount: lets CSS transitions play once from 0 to the real value. Reduced motion skips the transition in CSS. */
export function useReady(): boolean {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, []);
  return ready;
}

export function Card({ title, eyebrow, action, children, span = 12, i = 0, interactive = false, label }: {
  title?: string; eyebrow?: string; action?: ReactNode; children: ReactNode; span?: 3 | 4 | 6 | 8 | 12; i?: number; interactive?: boolean; label?: string;
}) {
  return (
    <section className={`mx-card mx-reveal mx-span-${span}${interactive ? " mx-card--interactive" : ""}`} style={rise(i)} aria-label={label ?? title}>
      {(title || action) && <header className="mx-card__head">
        <div>{eyebrow && <p className="mx-eyebrow">{eyebrow}</p>}{title && <h2 className="mx-card__title">{title}</h2>}</div>
        {action}
      </header>}
      {children}
    </section>
  );
}

export function Kpi({ icon: Icon, label, value, hint, tone, span = 3, i = 0, full = false, children }: {
  icon: LucideIcon; label: string; value: ReactNode; hint?: ReactNode; tone?: Exclude<Tone, "info" | "neutral">; span?: 3 | 4 | 6; i?: number; /** full width on phones (long values such as money) */ full?: boolean; children?: ReactNode;
}) {
  return (
    <article className={`mx-card mx-kpi-card mx-reveal mx-span-${span}${full ? " mx-kpi-card--full" : ""}`} style={rise(i)}>
      <div className="mx-kpi" data-tone={tone}>
        <span className="mx-kpi__icon" aria-hidden="true"><Icon size={22} strokeWidth={1.9} /></span>
        <span className="mx-kpi__label">{label}</span>
        <strong className="mx-kpi__value">{value}</strong>
        {hint ? <span className="mx-kpi__hint">{hint}</span> : <span />}
      </div>
      {children}
    </article>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className="mx-badge" data-tone={tone}>{children}</span>;
}

export function Meter({ percent, label }: { percent: number; label: string }) {
  const ready = useReady();
  const p = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  return <div className="mx-meter" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(p)}>
    <span style={{ "--p": ready ? p / 100 : 0 } as CSSProperties} />
  </div>;
}

export function Ring({ percent, caption }: { percent: number; caption: string }) {
  const ready = useReady();
  const p = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  const c = 2 * Math.PI * 52;
  return <div className="mx-ring" role="img" aria-label={`${caption}: ${Math.round(p)}%`}>
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <circle className="mx-ring__track" cx="60" cy="60" r="52" />
      <circle className="mx-ring__value" cx="60" cy="60" r="52" strokeDasharray={c} strokeDashoffset={ready ? c * (1 - p / 100) : c} />
    </svg>
    <div className="mx-ring__label"><strong>{Math.round(p)}%</strong><span>{caption}</span></div>
  </div>;
}

export function StackedBar({ segments, label }: { segments: Array<{ value: number; color: string; name: string }>; label: string }) {
  const ready = useReady();
  const shown = segments.filter((s) => s.value > 0);
  return <div className="mx-stack" role="img" aria-label={label}>
    {shown.map((s) => <span key={s.name} title={`${s.name}: ${s.value}`} style={{ flex: s.value, background: s.color, "--p": ready ? 1 : 0 } as CSSProperties} />)}
  </div>;
}

export function Skeleton({ count = 6 }: { count?: number }) {
  return <div className="mx-grid" aria-busy="true" aria-label="Загрузка">
    {Array.from({ length: count }, (_, i) => <div key={i} className={`mx-skel ${i < 4 ? "mx-span-3" : "mx-span-6"}`} />)}
  </div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="mx-error" role="alert"><p style={{ margin: "0 0 10px" }}>{message}</p><button className="mx-btn" onClick={onRetry}>Повторить</button></div>;
}

/** Real series only. y is a percentage 0..100; the caller supplies verified points or nothing. */
export function AreaChart({ points, ariaLabel, unit = "%" }: { points: Array<{ label: string; y: number }>; ariaLabel: string; unit?: string }) {
  const ready = useReady();
  const [active, setActive] = useState<number | null>(null);
  const W = 720, H = 220, L = 34, B = 26, T = 10, R = 8;
  const n = points.length;
  const x = (k: number) => L + (n <= 1 ? 0 : (k / (n - 1)) * (W - L - R));
  const y = (v: number) => T + (1 - Math.max(0, Math.min(100, v)) / 100) * (H - T - B);
  const line = points.map((p, k) => `${k ? "L" : "M"}${x(k).toFixed(1)} ${y(p.y).toFixed(1)}`).join(" ");
  const area = `${line} L${x(n - 1).toFixed(1)} ${H - B} L${x(0).toFixed(1)} ${H - B} Z`;
  const shownIndex = active ?? 0;
  const current = points[shownIndex];
  const move = (clientX: number, rect: DOMRect) => {
    const ratio = (clientX - rect.left) / rect.width;
    const k = Math.round(((ratio * W - L) / (W - L - R)) * (n - 1));
    setActive(Math.max(0, Math.min(n - 1, k)));
  };
  if (n === 0) return null;
  return <div className="mx-chart">
    <p className="mx-chart__readout" aria-live="polite">{current.label} · <b>{current.y.toFixed(1)}{unit}</b></p>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} tabIndex={0}
      onPointerMove={(e) => move(e.clientX, e.currentTarget.getBoundingClientRect())} onPointerLeave={() => setActive(null)}
      onKeyDown={(e) => { if (e.key === "ArrowRight") setActive(Math.min(n - 1, shownIndex + 1)); if (e.key === "ArrowLeft") setActive(Math.max(0, shownIndex - 1)); if (e.key === "Escape") setActive(null); }}
      onBlur={() => setActive(null)}>
      <defs><linearGradient id="mx-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--mx-chart-fill-a)" /><stop offset="1" stopColor="var(--mx-chart-fill-b)" /></linearGradient></defs>
      {[0, 25, 50, 75, 100].map((g) => <g key={g}><line className="mx-chart__grid" x1={L} x2={W - R} y1={y(g)} y2={y(g)} /><text className="mx-chart__axis" x={L - 6} y={y(g) + 4} textAnchor="end">{g}%</text></g>)}
      <g className="mx-chart__reveal" style={{ "--p": ready ? 1 : 0 } as CSSProperties}>
        <path d={area} fill="url(#mx-area)" /><path className="mx-chart__line" d={line} />
      </g>
      <text className="mx-chart__axis" x={x(0)} y={H - 6}>{points[0].label}</text>
      <text className="mx-chart__axis" x={x(n - 1)} y={H - 6} textAnchor="end">{points[n - 1].label}</text>
      <circle className="mx-chart__dot" cx={x(shownIndex)} cy={y(current.y)} r="5" />
    </svg>
  </div>;
}
