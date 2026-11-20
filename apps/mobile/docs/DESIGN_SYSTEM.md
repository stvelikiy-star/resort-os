# MARINA Future Luxury · Design system v1

The new design preserves the **existing MARINA SMART compass-and-ship raster asset** in `assets/marina-staff-app-icon.png`. PR #289 used an M-shaped vector from a marketing site and was not adopted because it is not a confirmed replacement for the supplied sea emblem. Branding sign-off is **PARTIAL**, pending original master-file comparison.

## Colors and composition

Source: `src/theme/tokens.ts`. Tokens retain compatibility with existing screens and use semantic roles instead of freehand theme-specific style per feature.

| Token | MARINA LIGHT | MARINA DARK |
|---|---|---|
| background | `#F5FAFF` | `#061225` |
| surface | `#FFFFFF` | `#10213D` |
| elevated | `#EEF7FC` | `#172A49` |
| primary/button | `#073B70` | `#00D8FF` |
| primary text | `#FFFFFF` | `#061225` |
| body text | `#10243D` | `#F4F8FF` |
| secondary text | `#586D80` | `#B3C6DC` |
| champagne accent | `#D5A64B` | `#E6BD70` |
| semantic danger | `#AA303A` | `#FF9CA4` |

Font scale and touch targets in `font` and `TOUCH=56`; radius `12/18/24/30`. Champagne is a decorative accent, not low-contrast body text. Hero uses a lightweight SVG ocean gradient with abstract navigation arcs: it is not a substitute logo.

## Components implemented

- `PremiumHeader`: approved existing seal + one-line role/hotel context.
- `GlassCard`/`MetricCard`: subtle glass-like elevated surfaces, no native blur memory cost, true server-derived values only.
- `StatusPill`, `QuickAction`, `PermissionDenied`, `ErrorState`, `OfflineBanner`.
- `LoadingShimmer`: reduced-motion and foreground-aware.
- `AIOrb`: controlled `idle/processing/error/offline`; it never simulates voice availability.
- `StaggerItem`: capped entrance with motion fallback.
- Role-specific lower bar maintains a maximum of five visible module tabs. Exact roles and grants remain server-authoritative.

## Accessibility and review

Current unit tests assert AA text/semantic contrast for both palettes, 56-point primary touch targets, motion preset bounds and persistence. Real-world checks on 320/375/430px screens, font scaling, TalkBack, VoiceOver, landscape and screenshot/pixel review remain **NOT RUN** until device access. This document does not claim completed visual acceptance.

Language copy is from existing RU/KG/EN/KZ i18n for app surfaces; the new assistant supports all four. Legacy mobileCopy Kazakh text still falls back to Russian and requires full KZ translation pass.
