# Future Luxury 2.0 — Typography and accessibility acceptance

**Status: technical source baseline, not UI/Android acceptance.**

## Type stack and languages

- Web: maintain `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`. Before approving the visual font, test the **actual served WOFF/TTF file and its codepoints**, not a font-family name.
- Mobile: keep the platform native/system font until a licensed, bundled font proves visually consistent and includes all six Kyrgyz characters **Ң ң Ө ө Ү ү**.
- Screen tests: `Бронирование / Брондоо / Reservation`, `Үй-бүлө`, `Жаңы бронь`, `Өзгөртүү`; avoid fixed-width labels and clipping on narrow screens and increased accessibility font sizes.
- Numeric typography: tabular figures for KGS, balances, room counts, dates; don't turn money values into decorative counters that obscure precision.
- Language baseline: **RU/KG/EN**, no silent fourth locale addition without separate approval.

## WCAG verified source color pairs

| Theme | Required pair | Expected |
|---|---|---|
| Light | main text and muted text on white | >= 4.5:1 |
| Light | inactive navigation on background | >= 4.5:1, remediated `#586D80` |
| Dark | main, muted, inactive navigation on navy | >= 4.5:1 |
| Both | text on primary buttons | >= 4.5:1 |

The existing `#D5A64B` champagne on white is 2.24:1, so champagne is **decorative/non-text only** until a separately verified accessible label/background combination is approved. Status chips must also include text or icons and be tested in all semantic states.

## Non-removal / motion

Visual refactors must keep 26 Admin tabs, 30 Mobile routes and all Staff operations, server RBAC/property scope and route-to-Core API integration. Motion must not block interactions, must honor Reduced Motion, and must not show completion before server acknowledgement. Android physical device E2E and browser visual screenshots remain **PENDING**.

## Self-check

Run `npm run design:fl2:accessibility`, `npm run design:fl2:brand` and `npm run design:fl2:audit` before every staged design PR; full CI and Android visual checks are separate release gates.
