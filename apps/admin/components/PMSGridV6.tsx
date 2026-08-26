"use client";

import PMSGridV5 from "./PMSGridV5";

// Reception Cockpit source remains available for review, but the active V6
// wrapper fails closed until the reception list can prove completeness for
// arrival/departure/overdue KPIs and exact-head CI executes successfully.
export default function PMSGridV6() {
  return <PMSGridV5 />;
}
