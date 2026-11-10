# Mobile roles × workspaces

Source of truth: `src/roles/registry.ts` plus backend `services/api/app/auth.py`, `section_permissions.py`. The table below is a **UI routing and verified API scope** inventory, not blanket server authorization.

| Role | Current LIVE mobile screens | Write scope | Status |
|---|---|---|---|
| OWNER | Overview, PMS, Inbox, Team, Profile; AI modal | PMS preview/commit/HOLD, ops status, Inbox status/notes | PARTIAL |
| MANAGER | Overview, PMS, Inbox, Tasks, Profile; AI modal | PMS preview/commit/HOLD, ops, Inbox | PARTIAL |
| RECEPTION | Reception, PMS, Inbox, Profile; AI modal | Check-in/out and new booking (preview → commit, published core rate only; server-enforced 403 RECEPTION_* codes) within server roles/grants, Inbox notes. Cancel and date changes stay OWNER/MANAGER; LIVE NOT VERIFIED | PARTIAL |
| MAID | Tasks, Rooms, Profile | task claim, checklist, inspection handoff | PARTIAL, photo API missing |
| TECHNICIAN | Tasks, Requests (repair), Rooms, Profile | maintenance task states and creation where authorized | PARTIAL |
| COOK | Dining, Profile | kitchen order state (server-authorized) | PARTIAL |
| WAITER | Dining, Profile | claim assigned waiter, read floor | PARTIAL |
| AGENT | PMS, Profile | preview/commit only for own linked agent scope; no HOLD | PARTIAL |
| STORE_STAFF | Profile | none until confirmed API | BLOCKED |
| CONTENT_MANAGER | Profile | none until confirmed API | BLOCKED |
| BEACH_PARTNER | Profile | none until confirmed API | BLOCKED |
| GUEST | separate pending auth/guest workspace | none in staff app | BLOCKED |

In every case backend trusted property, staff role, permission scopes, feature flags and linked agent ID remain authoritative. Direct route/deep-link security and live cross-tenant E2E are separate release gates. Synthetic demo data is shown only with a DEMO label; the new AI modal never connects to demo data.
