"use client";

import PMSBulkOps from "./PMSBulkOps";
import PMSGridV4 from "./PMSGridV4";

export default function PMSGridV5() {
  return <div className="pms-v5-stack">
    <PMSBulkOps />
    <PMSGridV4 />
  </div>;
}
