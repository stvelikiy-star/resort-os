"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState, type ButtonHTMLAttributes } from "react";
import { createPortal } from "react-dom";

/** Read-only presentation of data already shown by the grid's native title.
 * No requests, writes or role decisions live in this component. Legacy keeps its native title. */
export default function PmsBookingPreviewButton({ bookingNumber, title, children, onClick, onFocus, onBlur, onMouseEnter, onMouseLeave, onKeyDown, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { bookingNumber?: string | null }) {
  const id = useId();
  const tooltip = useRef<HTMLDivElement>(null);
  const [anchor, setAnchor] = useState<{ left: number; top: number } | null>(null);
  const show = (element: HTMLButtonElement) => {
    if (document.documentElement.dataset.marinaUi !== "future-luxury" || !title) return;
    const rect = element.getBoundingClientRect();
    setAnchor({ left: Math.max(12, Math.min(rect.left, window.innerWidth - Math.min(320, window.innerWidth - 24) - 12)), top: rect.bottom + 8 });
  };
  useLayoutEffect(() => {
    if (!anchor || !tooltip.current) return;
    const height = tooltip.current.getBoundingClientRect().height;
    const top = Math.max(12, Math.min(anchor.top, window.innerHeight - height - 12));
    if (top !== anchor.top) setAnchor({ ...anchor, top });
  }, [anchor]);
  useEffect(() => {
    if (!anchor) return;
    const close = () => setAnchor(null);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    return () => { window.removeEventListener("scroll", close, true); window.removeEventListener("resize", close); };
  }, [anchor]);
  return <>
    <button {...props} title={anchor ? undefined : title} aria-describedby={anchor ? id : props["aria-describedby"]}
      onMouseEnter={event => { show(event.currentTarget); onMouseEnter?.(event); }}
      onMouseLeave={event => { setAnchor(null); onMouseLeave?.(event); }}
      onFocus={event => { show(event.currentTarget); onFocus?.(event); }}
      onBlur={event => { setAnchor(null); onBlur?.(event); }}
      onKeyDown={event => { if (event.key === "Escape") setAnchor(null); onKeyDown?.(event); }}
      onClick={event => { setAnchor(null); onClick?.(event); }}>
      {children}
    </button>
    {anchor && createPortal(<div ref={tooltip} id={id} role="tooltip" className="fl2-booking-preview" style={anchor}>
      {bookingNumber && <strong>{bookingNumber}</strong>}
      <p>{title}</p>
    </div>, document.body)}
  </>;
}
