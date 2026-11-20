# MARINA SMART — Future Luxury 2.0 component contract

**State:** initial reusable UI primitives, staged Draft PR, not production acceptance.

## Live Mobile component integration

Mobile shared `apps/mobile/src/components/ui.tsx` provides the existing `Card`, `Badge`, `Button`, `Field`, `Screen`, `PressScale` APIs. Their props and business callbacks stay unchanged.

All colored `Badge` statuses now carry both their **original translated text** and a **Lucide semantic icon**, without modifying permission gates or business-state mapping:

| Existing badge tone | Added redundant icon | Text/status source |
|---|---|---|
| primary | CircleDot | unchanged caller text |
| success | CheckCircle2 | unchanged caller text |
| warning | AlertTriangle | unchanged caller text |
| danger | XCircle | unchanged caller text |
| info | Info | unchanged caller text |
| neutral | none | unchanged caller text |
| caller icon supplied | supplied icon wins | unchanged |

This is **presentation only**, not proof that the underlying status was validated by the server. Long RU/KG/EN labels must be checked on 320px screens with increased system font sizes.

## Web Admin optional skin

`apps/admin/app/fl2-ui-kit.css` contains opt-in classes `fl2-card`, `fl2-badge`, `fl2-button`, scoped to `html[data-marina-ui="future-luxury"]` only. They are ready for future scoped per-module integration. **No existing chessboard/table/finance selectors are overridden**, no existing Admin actions are changed.

Real working screens have not been replaced. When using these classes later, preserve the existing server-sourced data, role grants, actions, keyboard operation, screenshots, denial/offline/loading/errors, and native/expo performance.

## Visual and functional acceptance

- Light and dark must be tested independently. Web UI kit is opt-in and currently scoped only to Future Luxury; full light Web rollout is a separate reviewed stage.
- Mobile status icons and text are redundant, never color-only.
- Keep approved flat circular logo unchanged; exact PNG binaries still pending cross-app installation.
- Motion follows existing Reduced Motion preferences, no mandatory blur.
- At every visual PR: 26 Admin tab guards, 30 Mobile routes, Staff operational checks, API contract tests, and physical Android E2E before release.
- Current result: **LOCAL STATIC PASS** only. **CI PENDING / Android E2E NOT VERIFIED / LIVE NOT VERIFIED**.
