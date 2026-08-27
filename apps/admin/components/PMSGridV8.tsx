"use client";

import PMSBulkOps from "./PMSBulkOps";
import PMSReceptionCockpit from "./PMSReceptionCockpit";
import PMSShiftControl from "./PMSShiftControl";
import PMSUniversalBoard from "./PMSUniversalBoard";

export default function PMSGridV8() {
  return <div className="pms-v8-stack">
    <PMSShiftControl />
    <PMSReceptionCockpit />
    <PMSBulkOps />
    <PMSUniversalBoard />
  </div>;
}
