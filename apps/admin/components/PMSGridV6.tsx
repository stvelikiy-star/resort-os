"use client";

import PMSGridV5 from "./PMSGridV5";
import PMSReceptionCockpit from "./PMSReceptionCockpit";

export default function PMSGridV6() {
  return <div className="pms-v6-stack">
    <PMSReceptionCockpit />
    <PMSGridV5 />
  </div>;
}
