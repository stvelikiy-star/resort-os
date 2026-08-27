"use client";

import PMSOperationsCockpitV9 from "./PMSOperationsCockpitV9";
import PMSGridV8 from "./PMSGridV8";

export default function PMSGridV9() {
  return <div className="pms-v9-stack">
    <PMSOperationsCockpitV9 />
    <PMSGridV8 />
  </div>;
}
