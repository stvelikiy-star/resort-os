"use client";

import PMSGridV6 from "./PMSGridV6";
import PMSShiftControl from "./PMSShiftControl";

export default function PMSGridV7() {
  return <div className="pms-v7-stack">
    <PMSShiftControl />
    <PMSGridV6 />
  </div>;
}
