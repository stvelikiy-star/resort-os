# APPROVED FUTURE LUXURY · implementation contract

Stage 3 is a small mobile motion foundation, not a completed platform redesign. Public
marketing is frozen. Admin, staff and web runtime are unchanged until separately approved.

## Visual contract

- Mobile is the reference: navy `#073B70`, cyan (`#00D8FF` dark / accessible `#007E9B`
  light), and champagne (`#E6BD70` dark / `#D5A64B` light). The light counterpart uses
  `#F5FAFF` background, white surfaces and navy primary; semantic status colors retain meaning.
- Use one transparent **ORIGINAL MARINA SMART PNG** master across admin, staff and mobile.
  See [APPROVED_LOGO_MASTER.md](APPROVED_LOGO_MASTER.md) for the newly approved flat circular master and SHA-256. The verified binary is NOT YET INSTALLED in the repository.
  The source asset is **UNVERIFIED**. Do not replace it with existing different artwork,
  redraw it, or ship a logo change until provenance and pixel-level approval are recorded.
- Lucide vocabulary and sizes are defined in `ICONS.md`; icons communicate functions, never
  authorization. Status needs text as well as color/icon.
- Deterministic spacing is `4, 8, 12, 16, 24, 32, 40`; radii are `12, 18, 24, 30, 999`.
  Mobile type is display `34/800`, title `27/800`, h2 `19/700`, body `16/500/24`, small
  `13/500/19`, label `12/700`, metric `30/800`. Do not substitute unapproved fonts.
- Motion is finite and functional: press `125ms`, tab `220ms`, card `320ms`, modal `340ms`,
  chart `700ms`, stagger `55ms` capped at six. Use the existing React Native `Animated` stack.
  Reduced Motion, unresolved preference, read failure, or background app state must show the
  final content without animation. Stop animations/listeners on cleanup; no ambient loops.

## Non-removal invariant

Every existing feature, API field, translated string, callback semantic, accessibility label,
metric, route and server-authoritative RBAC/property/module gate is preserved. UI visibility is
not authorization. Kitchen, payments/finance, PMS actions and Guest OS remain first-class.

Existing mobile routes — checklist; **NEVER remove, hide, fake, or silently redirect**:

- [ ] Root/layout: `/_layout`, `/+html`, `/index`
- [ ] Auth: `/(auth)/_layout`, `/(auth)/connect`, `/(auth)/login`
- [ ] App shell: `/(app)/_layout`, `/(app)/overview`, `/(app)/more`, `/(app)/profile`
- [ ] PMS/operations: `/(app)/pms`, `/(app)/reception`, `/(app)/rooms`, `/(app)/tasks`,
  `/(app)/requests`, `/reservation/[id]`, `/room/[id]`, `/task/[id]`, `/holds`,
  `/new-booking`, `/new-request`, `/scan`
- [ ] Communications/Guest OS: `/(app)/inbox`, `/conversation/[id]`, `/ai`
- [ ] Hotel service: `/(app)/dining`, `/(app)/kitchen`, `/meal-plans`
- [ ] Management/payments: `/(app)/admin`, `/finance`

Existing function families — checklist; **NEVER remove or weaken**:

- [ ] Authentication, logout/revocation, single-property session binding and hotel data isolation
- [ ] Role, single-property and module grants; OWNER/MANAGER/RECEPTION/AGENT/MAID/TECHNICIAN/
  COOK/WAITER/DINING_STAFF/STORE_STAFF and legacy role handling
- [ ] Dashboard metrics exactly as supplied: occupancy, rooms, arrivals/departures, inbox,
  housekeeping, maintenance, attention tasks and permission-gated confirmed payments/debt
- [ ] PMS grid, holds/conflicts/blocks, reservation details, guest contact, call, booking,
  check-in/check-out and room operational actions
- [ ] Tasks, requests, rooms, housekeeping, maintenance and urgent workflows
- [ ] Inbox/conversations, translated copy, Guest OS/AI surfaces and outbound communication
- [ ] Dining, meal plans, kitchen forecasts/operations, payments/finance and admin/staff overview
- [ ] Loading, empty, error, offline, demo/showroom and accessibility states
- [ ] All current API response/write fields, validation, mutation acknowledgements and retries

Any future proposal must diff this checklist, prove parity with tests and receive explicit user
approval before removal or replacement. No API, migration, Docker, secret, dependency, lockfile,
deployment or public-site change belongs to this stage.
