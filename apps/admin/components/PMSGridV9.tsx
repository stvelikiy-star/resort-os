"use client";

import PMSBulkGuardV9 from "./PMSBulkGuardV9";
import { PMSControlSnapshotProviderV9 } from "./PMSControlSnapshotV9";
import PMSGuestServicesV9 from "./PMSGuestServicesV9";
import PMSOperationsCockpitV9 from "./PMSOperationsCockpitV9";
import PMSUniversalBoard from "./PMSUniversalBoard";

export default function PMSGridV9() {
  return (
    <PMSControlSnapshotProviderV9>
      <div className="pms-v9-stack">
        <PMSOperationsCockpitV9 />
        <PMSGuestServicesV9 />
        <PMSBulkGuardV9 />
        <PMSUniversalBoard />
      </div>
    </PMSControlSnapshotProviderV9>
  );
}
