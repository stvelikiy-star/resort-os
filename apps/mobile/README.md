# MARINA STAFF (mobile) — v0.2 first version

One Android + iOS app (React Native + Expo + TypeScript, expo-router) for staff of **all hotels connected to MARINA SMART**.
It is a **client** of the existing MARINA SMART API — no own PMS, no own staff database, no secrets in the app.

## Structure
```
app/                 expo-router routes
  (auth)/connect     hotel connection (list + add by https address, per-hotel)
  (auth)/login       staff sign-in (+ demo roles in demo hotels)
  (app)/tasks|rooms|requests|admin|profile   role-gated tabs
  task/[id]          task card + housekeeping checklist
  room/[id]          room card (+ status for allowed roles)
  new-request        maintenance request
src/theme            design tokens, light/dark ThemeProvider
src/i18n             ru / kg / en / kz (typed against ru → key parity at compile time)
src/api              StaffApi interface; demoApi (in-memory) and realApi (existing endpoints)
src/roles            role → workspace registry (UI gating only; server stays the authority)
src/state            per-hotel session (one api instance + session per hotel)
src/components       UI kit (Button, Card, Badge, FadeIn, PressScale…)
__tests__            i18n, roles, API contract, navigation/guards
```

## Data modes (strictly separated)
* **Demo hotels** (`demo://…`): in-memory data, never touches the network, red/amber `DEMO` banner on every screen.
* **Real hotel** (added by `https://` address): `realApi` calls the existing routes of that hotel's own host:
  `POST /api/v1/auth/login|logout`, `GET /auth/me`, `GET/POST /api/v1/ops/tasks`, `POST …/claim`, `PATCH …/status`,
  `PATCH …/assignee`, `POST …/complete-report`, `PATCH /ops/rooms/{id}/state`, `GET /api/v1/admin/staff/overview`.
  Only HTTPS is accepted. Interim auth is the server's httpOnly cookie session; bearer/refresh tokens need backend work.
  **Not yet verified against a running server** (no test environment was available).

## Run
```
cd apps/mobile
npm install
npm run check        # typecheck + lint + tests
npm start            # Expo dev server; press "a" for Android emulator or scan QR with Expo Go
npm run web:export   # static web build (used for screenshots)
```
Demo login: open a demo hotel → tap a role chip (password `demo`).
Android emulator reaching a local API: use `https` host or an HTTPS tunnel (`10.0.2.2` is the emulator's alias for the host machine; plain http is rejected by design).

## Not implemented yet
Push notifications; photo capture/upload (needs attachments API); QR scanner (button present, camera flow not built);
offline queue / sync / idempotency; bearer+refresh tokens and device registry (backend B1/B2); rooms list and day summary
endpoints for staff (derived from tasks / unavailable in real mode); biometric unlock; kitchen/waiter/store/beach workspaces;
guest-request actions; production signing/EAS builds. Do not deploy to production without separate approval.
