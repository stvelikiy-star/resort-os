"use client";

import PMSGridV4 from "./PMSGridV4";

export default function PMSGridV8() {
  // V8 source is retained for review, but the active PMS surface stays on V4
  // until the operational-task dedup (#33), reception completeness (#34),
  // and exact-head mutation CI gates are actually proven.
  return <div className="pms-v8-stack">
    <PMSGridV4 />
  </div>;
}
