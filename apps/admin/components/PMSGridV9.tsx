"use client";

import { useState } from "react";
import PMSBulkGuardV9 from "./PMSBulkGuardV9";
import { PMSControlSnapshotProviderV9 } from "./PMSControlSnapshotV9";
import PMSGuestServicesV9 from "./PMSGuestServicesV9";
import PMSIntegrationRailV10 from "./PMSIntegrationRailV10";
import PMSOperationsCockpitV9 from "./PMSOperationsCockpitV9";
import PMSOwnerGrid from "./PMSOwnerGrid";
import PMSUniversalBoard from "./PMSUniversalBoard";

export default function PMSGridV9() {
  const [operationsOpen, setOperationsOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  return (
    <PMSControlSnapshotProviderV9>
      <div className="pms-v9-stack owner-pms-stack">
        <div className="owner-pms-switches">
          <button className={operationsOpen ? "active" : ""} onClick={() => setOperationsOpen((value) => !value)}>
            {operationsOpen ? "Скрыть операционный центр" : "Операционный центр"}
          </button>
          <button className={advancedOpen ? "active" : ""} onClick={() => setAdvancedOpen((value) => !value)}>
            {advancedOpen ? "Скрыть расширенную V9" : "Перенос / разрез / расширенная V9"}
          </button>
        </div>

        <PMSOwnerGrid />

        {operationsOpen && <div className="owner-pms-tools-panel">
          <PMSIntegrationRailV10 />
          <PMSOperationsCockpitV9 />
          <PMSGuestServicesV9 />
          <PMSBulkGuardV9 />
        </div>}

        {advancedOpen && <div className="owner-pms-advanced-panel">
          <div className="owner-pms-panel-head">
            <div><strong>Расширенная шахматка V9</strong><span>Drag & drop, resize, Split Stay и полный фильтр остаются доступны здесь.</span></div>
            <button onClick={() => setAdvancedOpen(false)}>Закрыть</button>
          </div>
          <PMSUniversalBoard />
        </div>}
      </div>
    </PMSControlSnapshotProviderV9>
  );
}
