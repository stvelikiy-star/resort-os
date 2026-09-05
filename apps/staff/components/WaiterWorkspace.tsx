"use client";

import { useEffect, useState } from "react";

import DiningGuestSeatingPanel from "./DiningGuestSeatingPanel";
import WaiterEntry from "./WaiterEntry";

const ALLOWED = new Set(["OWNER", "MANAGER", "DINING_STAFF"]);

export default function WaiterWorkspace() {
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      fetch("/core/api/v1/auth/me", { cache: "no-store" })
        .then(async (response) => response.ok ? response.json() : null)
        .then((body) => { if (!cancelled) setAuthorized(Boolean(body && ALLOWED.has(body.role))); })
        .catch(() => { if (!cancelled) setAuthorized(false); });
    };
    check();
    const timer = window.setInterval(check, 3000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);

  return <>
    <WaiterEntry />
    {authorized && <DiningGuestSeatingPanel />}
  </>;
}
