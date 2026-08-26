"use client";

import PMSGridV4 from "./PMSGridV4";

// Bulk-operations source remains available for review, but the active V5
// wrapper fails closed until Resort Core enforces same-room/same-type active
// task deduplication server-side and exact-head CI proves the full flow.
export default function PMSGridV5() {
  return <PMSGridV4 />;
}
