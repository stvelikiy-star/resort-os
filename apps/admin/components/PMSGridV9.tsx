"use client";

import PMSBulkGuardV9 from "./PMSBulkGuardV9";
import PMSOperationsCockpitV9 from "./PMSOperationsCockpitV9";
import PMSGridV8 from "./PMSGridV8";

export default function PMSGridV9() {
  return <div className="pms-v9-stack">
    <PMSOperationsCockpitV9 />
    <PMSBulkGuardV9 />
    <PMSGridV8 />
  </div>;
}
