# MARINA SMART — Future Luxury 2.0 brand and token contract

**Status:** reference-only, staged for review. No runtime appearance, feature, API, RBAC, or user-role changes are authorized by this file.

## Immutable logo

The user-approved original is the **flat teal circular seal** with compass, ship and “MARINA SMART” inside, white disc, transparent outside. No glow, shadows, gradients, substitutes or distortion. Only the 1024/512 RGBA PNGs whose SHA-256 values match `APPROVED_LOGO_MASTER.md` can be installed. Binary rollout to Web Admin, Staff and Mobile is **PENDING**, and any generated splash/icon rendition must retain the original artwork and be checked visually.

## Canonical visual language

- Dark: deep navy surfaces and cyan/teal controls; legible light text; champagne only as rare premium/VIP emphasis.
- Light: accessible white/near-white surfaces, navy text; same semantic states. Theme parity is mandatory.
- The exact 29 light/dark mobile color tokens already in `apps/mobile/src/theme/tokens.ts` are the **existing baseline**. Do **not** blindly overwrite legacy Admin/Staff CSS: controlled per-module migration and visual QA are required.
- Status colors convey meaning **together with a label and icon**, never color alone; avoid using “success” for HOLD, debt or error.
- Preserve compact typography and **tabular numerals** for financial values. Verify real runtime font glyphs for Кыргызча: **Ң ң Ө ө Ү ү**, RU and EN, not just CSS family names.
- All money in the product follows server currency; for Kyrgyzstan use som/KGS and locale-appropriate formatting, not ₸.
- Light/dark must cover loading, error, offline, empty, denied and partial/unknown data; no fake revenue, bookings or AI status.
- PMS chessboard/tables avoid excessive translucent glass; keep data visible. Mobile uses native-safe surfaces, no mandatory native blur.

## Contrast audit — mandatory pre-rollout fix

Measured from the **existing baseline**, not new guessed colors:
- Light body text on white: 15.65:1; light muted text: 5.37:1 — pass AA normal text.
- Dark body text on surface: 15.09:1; muted: 9.20:1 — pass AA.
- **RESOLVED in FL2 accessibility PR:** light inactive nav text now uses existing muted-text `#586D80` against `#F5FAFF`; contrast is checked in CI. Original baseline was `#63788D`, **4.35:1** (<4.5:1).
- **Do not use champagne as text on white:** `#D5A64B` on white yields **2.24:1**; use decoration, badge backgrounds with separately verified dark text, or a reviewed darker accessible text variant.

Keep runtime values untouched until reviewed visual fix, and enforce these color-pair checks during implementation.

## Layout & motion

Existing spacing, radius, typography and motion values remain canonical until reviewed and changed via an approved visual PR. For Motion use finite entry/exit animations, reduced-motion and accessibility gates, no infinite pulse or speculative success. All touch and focus affordances remain accessible.

## Files and ownership

- Canonical recorded inventory: `marina-smart.tokens.json`.
- Generated reference bridge (new): `FL2_BRAND_TOKENS.json` — **not imported by runtime apps**.
- Validated implementation map: `FL2_IMPLEMENTATION_MAP.md`.
- Actual runtime sources: `apps/mobile/src/theme/tokens.ts`, `apps/admin/app/globals.css`, `apps/staff/app/globals.css`.
- Protected functional inventory: `FL2_FUNCTIONAL_BASELINE.md`.

## Gates before visual rollout

1. Check approved logo binary hash, transparent corners, exact mark and consistent sizing across clients.
2. Verify semantic token parity and WCAG contrast in light/dark, including small labels and disabled states.
3. Check font glyphs and line wrapping for RU/KG/EN, currency and large numbers.
4. Visual compare 320/375/768/1440 px and Android physical device.
5. Preserve Admin's 26 baseline tabs, Mobile's 30 baseline routes, Staff operations, roles and full API operations.
6. Maintain draft PR chain, no merge/deploy until tests and approval. **LIVE NOT VERIFIED; Android E2E NOT VERIFIED**.
