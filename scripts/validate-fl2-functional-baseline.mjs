#!/usr/bin/env node

import { readdirSync, readFileSync, statSync } from "node:fs";
import { relative, resolve, sep } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const fail = (message) => { throw new Error(`[FL2 functional baseline] ${message}`); };

const expectedAdminTabs = [
  "DASHBOARD", "PMS", "RATES", "GROUPS", "REQUESTS", "AGENTS", "RESERVATIONS",
  "SERVICES", "DINING", "SERVICE_SETTINGS", "GUESTS", "OFFERS", "MARKETING",
  "GROWTH", "FINANCE", "REPORTS", "CONTENT", "ROOM_QR", "POINT_QR", "INBOX",
  "WHATSAPP", "OPS", "STAFF", "SETTINGS", "HOTEL_RULES", "CHANNELS",
];
const shell = read("apps/admin/components/AdminShell.tsx");
const tabDeclaration = shell.match(/type Tab\s*=\s*([^;]+);/s)?.[1];
if (!tabDeclaration) fail("AdminShell Tab union is missing or no longer parseable");
const actualAdminTabs = [...tabDeclaration.matchAll(/"([A-Z_]+)"/g)].map((match) => match[1]);
const missingAdminTabs = expectedAdminTabs.filter(tab => !actualAdminTabs.includes(tab));
if (missingAdminTabs.length) {
  fail(`Baseline Admin tabs removed: ${missingAdminTabs.join(", ")}`);
}
for (const tab of expectedAdminTabs) {
  if (!shell.includes(`tab === "${tab}"`) || !shell.includes(`canAccess("${tab}")`) && tab !== "OPS") {
    fail(`Admin tab ${tab} is not represented by both selection and access-gate source`);
  }
}

function walkTsx(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    return entry.isDirectory() ? walkTsx(path) : entry.name.endsWith(".tsx") ? [path] : [];
  });
}
const mobileRoot = resolve(root, "apps/mobile/app");
const actualMobileRoutes = walkTsx(mobileRoot)
  .map((path) => relative(mobileRoot, path).split(sep).join("/"))
  .sort();
const expectedMobileRoutes = [
  "(app)/_layout.tsx", "(app)/admin.tsx", "(app)/dining.tsx", "(app)/inbox.tsx",
  "(app)/kitchen.tsx", "(app)/more.tsx", "(app)/overview.tsx", "(app)/pms.tsx",
  "(app)/profile.tsx", "(app)/reception.tsx", "(app)/requests.tsx", "(app)/rooms.tsx",
  "(app)/tasks.tsx", "(auth)/_layout.tsx", "(auth)/connect.tsx", "(auth)/login.tsx",
  "+html.tsx", "_layout.tsx", "ai.tsx", "conversation/[id].tsx", "finance.tsx",
  "holds.tsx", "index.tsx", "meal-plans.tsx", "new-booking.tsx", "new-request.tsx",
  "reservation/[id].tsx", "room/[id].tsx", "scan.tsx", "task/[id].tsx",
].sort();
const missingMobileRoutes = expectedMobileRoutes.filter(route => !actualMobileRoutes.includes(route));
if (missingMobileRoutes.length) {
  fail(`Baseline Mobile route modules removed: ${missingMobileRoutes.join(", ")}`);
}

const staffEvidence = {
  "apps/staff/app/page.tsx": ["StaffRoleGateway"],
  "apps/staff/app/kitchen/page.tsx": ["KitchenEntry"],
  "apps/staff/app/kitchen/today/page.tsx": ["DiningDayPlanner"],
  "apps/staff/app/waiter/page.tsx": ["WaiterWorkspace"],
  "apps/staff/components/StaffRoleGateway.tsx": ["StaffShiftV2", "GuestRequestShiftPanel", "SharedDiningShift"],
  "apps/staff/components/KitchenEntry.tsx": ["ChefProduction", "KitchenAdminV2"],
  "apps/staff/components/WaiterWorkspace.tsx": ["WaiterEntry", "DiningFolioActions", "DiningGuestSeatingPanel"],
  "apps/staff/components/WaiterEntry.tsx": ["DiningFloorPlan"],
};
for (const [path, symbols] of Object.entries(staffEvidence)) {
  const source = read(path);
  for (const symbol of symbols) if (!source.includes(symbol)) fail(`${path} lost key module ${symbol}`);
}

const baseline = read("docs/design/FL2_FUNCTIONAL_BASELINE.md");
const implementation = read("docs/design/FL2_IMPLEMENTATION_MAP.md");
const logo = read("docs/design/APPROVED_LOGO_MASTER.md");
for (const marker of ["LIVE NOT VERIFIED", "Android E2E NOT VERIFIED", "26 Admin tabs", "30 Mobile route modules"]) {
  if (!baseline.includes(marker)) fail(`baseline document is missing marker: ${marker}`);
}
for (const marker of ["RU/KG/EN", "light/dark", "Existing", "Proposed", "APPROVED_LOGO_MASTER.md"]) {
  if (!implementation.includes(marker)) fail(`implementation map is missing marker: ${marker}`);
}
for (const marker of [
  "flat symmetrical teal circular ring", "Outside circle truly transparent",
  "24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356",
  "CROSS-APP INSTALLATION PENDING",
]) if (!logo.includes(marker)) fail(`approved logo master constraint is missing: ${marker}`);

for (const path of ["docs/design/FL2_FUNCTIONAL_BASELINE.md", "docs/design/FL2_IMPLEMENTATION_MAP.md"]) {
  if (!statSync(resolve(root, path)).isFile()) fail(`${path} is not a file`);
}

console.log(`FL2 functional baseline OK: ${actualAdminTabs.length} Admin tabs, ${actualMobileRoutes.length} Mobile route modules, ${Object.keys(staffEvidence).length} Staff evidence files.`);
