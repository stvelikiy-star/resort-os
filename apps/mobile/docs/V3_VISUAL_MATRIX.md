# MARINA SMART MOBILE · FUTURE LUXURY V3 — visual QA acceptance matrix

**Scope:** `apps/mobile` only · Draft PR #342 and follow-up Draft PR #368. The matrix now tracks **23 named routes** including `/finance`.

## Evidence basis and strict distinctions

The genuine screenshots below were captured from the **running Expo Web export** in headless Google Chrome, with a built-in **DEMO-only fixture** at localhost. They are **NOT Android**, not generated illustrations and not substituted for native visual evidence. The screen source was `1b55a5a48a4ca5c616d4b0d8aa179591882d82ef`, GitHub Actions [run 41875555127](https://github.com/stvelikiy-star/resort-os/actions/runs/41875555127), mobile-check job 126734622122. The screenshot assets and this report only add documentation, not executable UI changes.

**Expo Web route QA (actual screenshot evidence):** 0 PASS / 0 FAIL / **19 PARTIAL** / **4 NOT TESTED** (23 routes). Extended run: 170 authentic Expo Web JPEGs, including 135 named route/locale/theme/viewport matrix shots.
**Android native visual QA:** 0 PASS / 0 FAIL / 0 PARTIAL / **23 NOT TESTED**.
**Screenshots:** 21 authentic Expo Web JPEGs, at 320 / 375 / 430 viewport widths, RU / KG / EN / KZ and light / dark where noted.

**PARTIAL** means a screen was really rendered and captured in the safe DEMO context but the complete cross-product of viewport/font scale/locale/theme/data states/accessibility was not checked. **NOT TESTED** means the route was not actually rendered; source analysis and Jest never count as a visual PASS.

## Route-by-route status

| Route | Purpose / access | Expo Web visual | Android visual | Screenshot evidence |
| --- | --- | --- | --- | --- |
| `/connect` | Select demo/trusted hotel | PARTIAL | NOT TESTED | [Web 1](qa-evidence/connect_ru_light_375.jpg) |
| `/login` | All server-supported roles | PARTIAL | NOT TESTED | [Web 1](qa-evidence/login_en_dark_375.jpg) |
| `/scan` | Hotel QR connection | PARTIAL (Web permission-state only, no camera E2E) | NOT TESTED | [9 actual `matrix_scan_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709); RU/KG/EN dark, 320/375/430 |
| `/overview` | OWNER/MANAGER | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web owner overview artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `owner_overview_ru_light_375.jpg` · [18 actual `matrix_overview_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/reception` | RECEPTION | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web reception artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `reception_en_dark_375.jpg` · [18 actual `matrix_reception_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/pms` | OWNER/MANAGER/AGENT | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web PMS artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `owner_pms_ru_light_375.jpg` · [18 actual `matrix_pms_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/new-booking` | Permitted booking creator | NOT TESTED | NOT TESTED | No safely accessible built-in DEMO screen |
| `/reservation/[id]` | Permitted booking detail | NOT TESTED | NOT TESTED | No safely accessible built-in DEMO screen |
| `/holds` | OWNER/MANAGER where server supported | NOT TESTED | NOT TESTED | No safely accessible built-in DEMO screen |
| `/finance` | OWNER/MANAGER with FINANCE grant, LIVE only | NOT TESTED | NOT TESTED | New route in PR #368; no physical Android or LIVE screenshots |
| `/inbox` | Permitted OWNER/MANAGER/RECEPTION | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web Inbox artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `owner_inbox_ru_light_375.jpg` · [18 actual `matrix_inbox_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/conversation/[id]` | Permitted inbox users | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web chat artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `owner_conversation_ru_light_375.jpg` · [18 actual `matrix_conversation_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/ai` | Permitted OWNER/MANAGER/RECEPTION | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web unavailable AI artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `owner_ai_unavailable_ru_light_375.jpg` (offline, not LIVE) · [18 actual `matrix_ai_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/tasks` | MAID/TECHNICIAN and other permitted staff | PARTIAL | NOT TESTED | [Web 1](qa-evidence/manager_tasks_ru_light_375_after_tab_fix.jpg) · [Web 2](qa-evidence/maid_tasks_en_dark_375.jpg) · [Web 3](qa-evidence/tech_tasks_en_dark_375.jpg) |
| `/task/[id]` | Permitted task detail | PARTIAL | NOT TESTED | [Web 1](qa-evidence/maid_housekeeping_detail_en_dark_375.jpg) |
| `/rooms` | Permitted staff | PARTIAL | NOT TESTED | [Web 1](qa-evidence/maid_rooms_en_dark_375_after_wrap_fix.jpg) |
| `/room/[id]` | Permitted staff | PARTIAL | NOT TESTED | [Web 1](qa-evidence/maid_room_detail_en_dark_375.jpg) |
| `/requests` | TECHNICIAN and permitted maintenance staff | PARTIAL | NOT TESTED | [Web 1](qa-evidence/tech_repairs_en_dark_375.jpg) |
| `/new-request` | Maintenance creator | PARTIAL | NOT TESTED | [Web 1](qa-evidence/tech_new_request_en_dark_320.jpg) · [Web 2](qa-evidence/tech_new_request_en_dark_375.jpg) · [After 320](qa-evidence/tech_new_request_en_dark_320_verified.jpg) |
| `/admin` | OWNER/MANAGER if authorized | PARTIAL | NOT TESTED | [Web 1](qa-evidence/manager_team_en_dark_320_after_nav_fix.jpg) · [Web 2](qa-evidence/manager_team_en_dark_375.jpg) · [Web 3](qa-evidence/manager_team_en_dark_430.jpg) · [Assign picker](qa-evidence/manager_assign_picker_en_dark_430_verified.jpg) |
| `/dining` | COOK/WAITER/authorized management | PARTIAL (prior SHA) | NOT TESTED | [Real Expo Web kitchen artifact](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914) · `cook_orders_en_dark_375.jpg` · [18 actual `matrix_dining_*` captures](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709) |
| `/profile` | All authenticated staff | PARTIAL | NOT TESTED | [Web 1](qa-evidence/manager_profile_ru_light_375.jpg) · [Web 2](qa-evidence/manager_profile_ru_dark_375.jpg) · [Web 3](qa-evidence/manager_profile_kg_dark_375.jpg) · [Web 4](qa-evidence/manager_profile_kz_dark_375.jpg) · [Web 5](qa-evidence/manager_profile_en_dark_375.jpg) · [After sign-out](qa-evidence/manager_profile_ru_dark_375_verified.jpg) |
| `/more` | Roles with >4 allowed navigation tabs | PARTIAL | NOT TESTED | [Web 1](qa-evidence/manager_more_ru_light_375.jpg) |

## PR #368 — P1 matrix provenance and acceptance (5 November 2026)

**Verified prior-commit evidence:** 35 genuine Expo Web screenshot interactions from source SHA `b01bbcf6e14208dfd9aba0ad428fd89ed1063aec`, [workflow 41975002638](https://github.com/stvelikiy-star/resort-os/actions/runs/41975002638/artifacts/13391511914), synthetic local DEMO only. These images justify **PARTIAL**, not PASS, for seven formerly untested routes (overview/reception/pms/inbox/conversation/ai/dining). Exact filenames are named above; no LIVE/PMS data was accessed.

**New matrix runner executed successfully on SHA `8edaaf9`:** `apps/mobile/scripts/qa-web-visual.mjs` records an exact-source `matrix-manifest.json` and individual JPEGs for reachable routes. Target combinations: 320/375/430 dp × light/dark × RU/KG/EN for overview, reception, pms, inbox, conversation, AI and dining; QR scan is attempted at 320/375/430 in RU/KG/EN with **dark only**. A successful Expo Web screenshot is never evidence of a native camera scan.

**Remaining NOT TESTED:** `/new-booking`, `/reservation/[id]`, `/holds` have no safe authenticated DEMO flow that would prove operation; `/finance` requires a real FINANCE-authorized server session. QR permission-state screenshots are **CONFIRMED (9 files)**; no real camera scan is claimed. Do not assume those screenshots exist from configured test code alone.

**Acceptance rule:** only mark new matrix items PARTIAL after a CI log confirms `WEB_VISUAL_CAPTURE` with exact route+locale+theme+width and the corresponding nonempty JPEG artifact. Historical and current artifacts must not be conflated. **All Android routes remain NOT TESTED** until actual-device screenshots and E2E checks.

## PR #368 — CONFIRMED EXTENDED WEB MATRIX

**Exact executable SHA:** `8edaaf9ed810370350b41005d68a0fa5a2bb5b9b`. [GitHub Actions run 41982562743](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743): `mobile-check` **SUCCESS**, Jest **34 suites / 228 tests PASS**, `WEB_VISUAL_QA_END captured=170 actual=ExpoWeb not=Android`.

[Verified screenshots and machine-readable matrix-manifest.json](https://github.com/stvelikiy-star/resort-os/actions/runs/41982562743/artifacts/13394124709). All 170 images were captured from the actual running Expo Web app on isolated local DEMO data (35 standard screen shots + 135 matrix captures). No real hotel, native device or simulated proof was used.

| Route | Captures | Actual locale/theme/width | Expo Web |
| --- | ---: | --- | --- |
| `/overview` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/reception` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/pms` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/inbox` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/conversation/[id]` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/ai` | 18 | RU/KG/EN × light/dark × 320/375/430; offline/unavailable state only | PARTIAL |
| `/dining` | 18 | RU/KG/EN × light/dark × 320/375/430 | PARTIAL |
| `/scan` | 9 | RU/KG/EN × dark only × 320/375/430; camera permission state, **not camera scan** | PARTIAL |
| `/new-booking` | 0 | No safe DEMO booking-write scenario | NOT TESTED |
| `/reservation/[id]` | 0 | No safe DEMO reservation-detail auth context | NOT TESTED |
| `/holds` | 0 | Server-backed feature gate remains false | NOT TESTED |
| `/finance` | 0 | LIVE FINANCE-permitted account required | NOT TESTED |

**No native Android screenshots or LIVE E2E were taken:** all 23 Android routes remain **NOT TESTED**. Screenshot PARTIAL describes only browser-rendered UI at specified conditions, not production-ready functionality or human translation certification. The follow-up documentation commit changes no executable UI but still requires CI acceptance on the final SHA.

## Confirmed UI fixes — same-condition before / after

Every comparison pairs **the same viewport, role, language, theme and DEMO data**.

| Observed defect | BEFORE: real Expo Web | AFTER: real Expo Web |
| --- | --- | --- |
| RU MANAGER 375px: clipped team tab | ![Before: RU MANAGER 375px: clipped team tab](qa-evidence/before_manager_tasks_ru_light_375.jpg) | ![After: RU MANAGER 375px: clipped team tab](qa-evidence/manager_tasks_ru_light_375_after_tab_fix.jpg) |
| EN MANAGER 320px: clipped Repairs tab | ![Before: EN MANAGER 320px: clipped Repairs tab](qa-evidence/before_manager_team_en_dark_320.jpg) | ![After: EN MANAGER 320px: clipped Repairs tab](qa-evidence/manager_team_en_dark_320_after_nav_fix.jpg) |
| EN MAID 375px: clipped arrival text | ![Before: EN MAID 375px: clipped arrival text](qa-evidence/before_maid_rooms_en_dark_375.jpg) | ![After: EN MAID 375px: clipped arrival text](qa-evidence/maid_rooms_en_dark_375_after_wrap_fix.jpg) |
| KG MANAGER 375px: clipped task/room tabs | ![Before: KG MANAGER 375px: clipped task/room tabs](qa-evidence/before_manager_profile_kg_dark_375.jpg) | ![After: KG MANAGER 375px: clipped task/room tabs](qa-evidence/manager_profile_kg_dark_375.jpg) |
| KZ MANAGER 375px: clipped task/room/repair tabs | ![Before: KZ MANAGER 375px: clipped task/room/repair tabs](qa-evidence/before_manager_profile_kz_dark_375.jpg) | ![After: KZ MANAGER 375px: clipped task/room/repair tabs](qa-evidence/manager_profile_kz_dark_375.jpg) |

## Additional screenshot coverage

MANAGER: task queue RU/light and EN/dark, team EN/dark at 320/375/430, profile RU/light+dark and KG/KZ/EN dark, More menu. MAID: tasks, room cards, room detail and housekeeping checklist EN/dark. TECHNICIAN: task queue, repair queue and new-request form EN/dark 375 and 320. Connect RU/light; login EN/dark. No business writes were performed.

[Authentic screenshot provenance](qa-evidence/PROVENANCE.json) includes the exact source SHA, GitHub Actions run, DEMO fixture and files.

## Follow-up polish — source-verified, awaiting fresh real visual evidence

| Surface | Proven code-level issue | Minimal correction | Evidence status |
| --- | --- | --- | --- |
| MARINA AI Orb (offline / read-only) | `AIOrb` passed `disabled={!onPress}` into `PressScale`, which automatically reduced its opacity to 0.5. This muted a visual status indicator that should not signify an inaccessible button. | `dimWhenDisabled={false}` on `AIOrb`; no new action or API capability. | SOURCE FIX; Android visual NOT TESTED, LIVE AI route Web NOT TESTED |
| OWNER/MANAGER financial KPI | At 375 dp the previous `MetricCard` forced even long values into a 46%-width column, one line, as low as 55% font scaling. Risk of unreadable KGS figures on narrow devices was confirmed by source inspection, **not** an OWNER screenshot. | Full-width card for formatted values >10 characters, <350 dp phones or >150% system font. Two-line value allowed, minimum scale now 70%. Pure layout regression tests added. | SOURCE FIX; OWNER Web/Android visual NOT TESTED |
| TECHNICIAN repair-request form at 320 px | Genuine Expo Web screenshot [before](qa-evidence/tech_new_request_en_dark_320.jpg) shows the close control moved to its own row beneath the title, consuming scarce vertical space. | Only this form opts into `PremiumHeader.inlineCompactRight`; the title can wrap while the close action stays on the same row. Other headers retain their previous behavior. | WEB BEFORE + [AFTER Web screenshot](qa-evidence/tech_new_request_en_dark_320_verified.jpg) CONFIRMED (source SHA `4f6ce9d`) |
| Dark profile danger button | Genuine Expo Web screenshot [before](qa-evidence/manager_profile_ru_dark_375.jpg) shows low-contrast white text on a pale pink sign-out button. Confirmed code contrast ratio **1.99:1** for `#FFFFFF` on `#FF9CA4`. | Use existing theme-aware `primaryText` on danger button, achieving calculated ratio **9.41:1** in dark mode, preserving **6.58:1** in light mode. Added a WCAG contrast regression assertion. | WEB BEFORE + [AFTER Web screenshot](qa-evidence/manager_profile_ru_dark_375_verified.jpg) CONFIRMED (source SHA `4f6ce9d`) |

| MANAGER assignment action | Genuine Expo Web screenshot [manager_team_en_dark_430](qa-evidence/manager_team_en_dark_430.jpg) showed a tiny `Assign` label beneath an unassigned task. Source audit verified the label was a passive `Badge`; only the task card itself opened staff selection. | Replaced passive badge with a labelled `PressScale` button, minimum 48 dp. Added a real Expo Web interaction assertion: tap `open-assign-t8`, require eligible `assign-u-maid`, then capture `manager_assign_picker_en_dark_430`. This does not submit a staff write. | WEB BEFORE + [AFTER picker screenshot](qa-evidence/manager_assign_picker_en_dark_430_verified.jpg) CONFIRMED (source SHA `4f6ce9d`) |

| Light-theme bottom navigation | Direct WCAG calculation found `navInactive #64798F` on `surface #FFFFFF` measured **4.49:1** (<4.5:1 AA text criterion); screenshots show these labels in normal use. | Adjusted only the existing light theme `navInactive` token to `#63788D`, yielding **4.56:1**. Added both-theme contrast assertion in `future-design.test.tsx`. | SOURCE VERIFIED; updated Expo Web screenshot and Android native QA pending |

This polish does not expand permissions, seed fake platform metrics or modify any backend API. The previously captured 21 Expo Web screenshots predate these two changes and do not evidence their final appearance; their route statuses above remain unchanged.


## Desktop browser preview — user-reported defect

**Evidence:** user-supplied 1728 px browser screenshot of the actual Expo Web staff login, showing an edge-to-edge login form with disproportionate inputs, header and CTA. This is a real **Web** bug; it is not evidence of a native Android issue.

**Fix:** `app/_layout.tsx` now renders the existing navigation inside a centered, maximum **440 px** mobile viewport on desktop Web (`>=700 px`), while Web phones, native Android and iOS retain fluid full width. No new UI routes, screen rewrites or platform changes. `app/+html.tsx` additionally opts out of browser auto-translation, since the screenshot showed the branded `MARINA SMART` wordmark incorrectly translated to `МАРИНА УМНЫЙ` despite the source `Brand.tsx` rendering English.

**Acceptance:** CI must capture actual Expo Web `connect_ru_desktop_1440_after_mobile_frame.jpg` and `login_en_dark_desktop_1440_after_mobile_frame.jpg`, verify the rendered frame is **300–444 px** and horizontally centered, then recheck mobile at 375 px. **AFTER screenshots: PENDING** until a successful run on the updated SHA. Android native remains **NOT TESTED**.

## Verified fresh Expo Web evidence after V3 fixes

Three screenshots were captured from the **real running Expo Web UI** in headless Chrome at GitHub Actions [run 41880546889](https://github.com/stvelikiy-star/resort-os/actions/runs/41880546889), job 126752023955, source SHA `4f6ce9dd5d58ab6ad16463059e114a405ce3f28c`, built-in synthetic DEMO fixture, no live hotel and no staff write. **The workflow was subsequently canceled by a newer commit after logging the images.** This does not imply a CI PASS for that commit. Screenshot authenticity is supported by the `WEB_VISUAL_JPEG:` job log records and [provenance](qa-evidence/PROVENANCE_V3_POLISH.json).

- [TECHNICIAN: corrected repair header at 320 px](qa-evidence/tech_new_request_en_dark_320_verified.jpg) — close action stays aligned with wrapped title; compare [before](qa-evidence/tech_new_request_en_dark_320.jpg).
- [MANAGER: corrected dark sign-out contrast at 375 px](qa-evidence/manager_profile_ru_dark_375_verified.jpg) — dark foreground on danger button; compare [before](qa-evidence/manager_profile_ru_dark_375.jpg).
- [MANAGER: assignment picker opened by the new 48 dp CTA at 430 px](qa-evidence/manager_assign_picker_en_dark_430_verified.jpg) — two eligible employees visible, **no assignment submitted**; compare [before action](qa-evidence/manager_team_en_dark_430.jpg).

The later minor `navInactive` light-theme token fix and the navigation Jest regression were not part of these captured images. Await fresh same-SHA verification. All Web route statuses remain **PARTIAL**; all Android visual statuses remain **NOT TESTED**.

## Explicitly unverified or blocked

- **Android visual QA remains NOT TESTED for all 22 routes.** This review container has no Android SDK, ADB or emulator; the available GitHub workflow only builds and signs the APK. An APK build PASS is **not** a native UI PASS.
- OWNER LIVE overview, RECEPTION LIVE operations, PMS grid, booking/hold editing, WhatsApp and AI states, Dining, and QR camera were not opened with a safe authenticated server-backed fixture. No fake API responses or hotel data were injected.
- Android font scaling 150/200%, keyboard overlays, native modals, accessibility TalkBack, reduced-motion animations and safe area variants require actual-device tests.
- Some pre-existing DEMO task titles and notes are written in Russian even when the app UI is EN/KG/KZ. These are raw seed **data fields**, not app chrome; they were not silently translated.
- Full brand master comparison remains **PENDING BRAND APPROVAL**. Existing MARINA SMART original mobile raster/logo/icons were not changed.
- Backend dependencies remain unchanged: shared-auth preview 503 for Inbox/Dining/AI, no WhatsApp outbound API, AI read-only, no verified historical chart data and HOLD endpoint still blocked by existing feature checks.

**Status:** WEB VISUAL PARTIAL, ANDROID VISUAL NOT TESTED. PR remains Draft and must not be merged as an approved Android UI release without real native screenshots and manual role acceptance.
