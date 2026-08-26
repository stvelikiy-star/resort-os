"use client";

import PMSGridV6 from "./PMSGridV6";

// V7 Control Tower source is retained in the branch for review, but the live
// admin entrypoint fails closed to the audited V6 surface until V7 proves
// complete reception/task semantics and exact-head CI executes successfully.
export default function PMSGridV7() {
  return <PMSGridV6 />;
}
