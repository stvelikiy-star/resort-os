## Connecting an existing MARINA SMART API

The hotel's HTTPS address may be the API origin (`https://hotel.example`) or the existing reverse-proxy base path (`https://hotel.example/core`). In the latter case requests use `/core/api/v1/...`; otherwise they use `/api/v1/...`.

The QR/manual input deliberately rejects other URL paths, query strings, fragments, credentials, IP addresses and nonstandard ports. The app verifies the server's cookie-based session with `auth/me` after login. Availability of the mobile API from an Android device, reverse-proxy cookie behavior and the server's role policies must be checked on a dedicated test hotel before production use.

# MARINA SMART STAFF — mobile client

An isolated Expo / React Native application for staff of hotels using MARINA SMART.
**The application is a PMS client, not a replacement PMS and not a marketing site.**

## Current state (3 November 2026)

- Visual system: approved MARINA SMART compass/ship emblem, navy/blue/silver, light/dark mode, reduced-motion-aware transitions and animated task progress.
- RU, KG, EN, KZ interfaces with typed translation dictionaries.
- Offline **demo** hotels are clearly labelled; demo data cannot write to the live PMS.
- Real mode: HTTPS hotel connection by entered address or QR scan, username/password, `/auth/me` identity and hotel confirmation before access, task list/status/claim/report, maintenance requests, manager task assignment.
- QR contains **only** an HTTPS origin, never an access token/password. Local/private IP origins and nonstandard ports are not accepted.
- Existing permissions: OWNER/MANAGER manager workspace; MAID housekeeping; TECHNICIAN maintenance; roles without a verified backend workflow show their profile only. Server RBAC remains authoritative.
- The live room catalogue is **partial**: only rooms present in visible operational tasks, not a full inventory or verified occupancy. Day summary is unavailable in the existing mobile API contract.
- Live staff overview maps `active_tasks` to mobile workload and excludes inactive/incompatible staff from task assignment.

## Run / checks

```bash
cd apps/mobile
npm install
npm run check
npm run web:export
npm start
```

CI additionally runs Expo dependency alignment, TypeScript, ESLint, Jest, Expo web export, and Expo config validation.

## Native branding status

The repository includes the **original 512×512 MARINA SMART ship/compass emblem** as `assets/marina-staff-app-icon.png`. Git blob SHA `73250f43d351de12c05e5aeb6bb59fabf1cff488` was independently checked against the source PNG. The bundled emblem is used by the UI and Expo's app icon, Android adaptive foreground, splash and web favicon. The earlier low-resolution 72px seal is no longer referenced by the runtime.

This is an authentic 512px source rather than a fabricated 1024px image. A 1024px master/vector export is still preferable before public app-store submission; physical-device icon and splash inspection remain required.

## Android build preparation

The `eas.json` profiles are **configuration only**, not evidence of an APK or AAB:

```bash
# Requires a connected Expo/EAS project, Android app identifier, approved
# high-resolution native icons/splash, and authorized signing credentials.
npx eas-cli build --platform android --profile preview
# Store delivery, after device QA:
npx eas-cli build --platform android --profile production
```

Never commit signing keys, backend credentials, service-account JSON, or live PMS data.

## Blocking production acceptance

1. Bundle the original high-resolution native app icon and splash assets; verify both device themes.
2. Perform Android device QA (permissions, camera, navigation, reconnect, no-network, session handling).
3. Verify HTTPS reverse proxy + cookie/CORS behavior against a **dedicated test hotel** on the actual target origin, not only mocked fetch.
4. End-to-end: per-role login/logout/revocation, claim → report → inspection, repair → room block, manager assignee restrictions, isolation between test properties.
5. Add server-supported full room listing, aggregate day summary, attachment upload, notifications, and offline mutation idempotency **only after** their actual API contracts are available. Do not fabricate these screens.
6. Build signed preview APK and perform rollout/rollback QA. No production publication based on CI alone.

All application work remains separate from MARINA SMART PMS core and public marketing site.
