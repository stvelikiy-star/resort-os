"use client";

import { useEffect, useRef } from "react";

/** Visual-only: reveal a newly rendered schedule preview inside its existing scrollable PMS dialog. */
export default function PmsPreviewScrollAnchor() {
  const anchorRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      anchorRef.current?.closest(".v8-preview")?.scrollIntoView({ block: "nearest", behavior: "auto" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return <span ref={anchorRef} aria-hidden="true" style={{ display: "none" }} />;
}
