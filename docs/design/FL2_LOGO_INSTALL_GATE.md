# MARINA SMART — exact approved PNG cross-app installation gate

The user strictly approved **only** the flat teal ring / ship / compass `MARINA_SMART_APPROVED_FLAT_1024.png` (SHA-256 `24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356`). This is the only admissible source binary, not an earlier mobile icon or WebP.

**Current candidate status (2026-11-14): INSTALLED AND VERIFIED.** PR #448 installed the exact approved PNG in Admin, Staff and Expo. The installation verifier passed again on candidate `b3bcf042`; the approved master hash above matches all three installed copies. This is source/candidate verification, not proof of production deployment or visual acceptance on a phone. Do NOT fabricate or convert other images as a substitute.

## Safe local installation after transferring the exact bytes

1. Put the approved 1024 PNG on Ubuntu (outside the worktree), preserving its SHA-256.
2. Check out a clean isolated `design/*` worktree containing this installer.
3. Run `node scripts/install-approved-marina-logo.mjs --plan` (no changes).
4. Run `node scripts/install-approved-marina-logo.mjs --apply /absolute/path/MARINA_SMART_APPROVED_FLAT_1024.png`.
5. The installer checks SHA-256, 1024x1024 RGBA, clean branch, all original references and writes three **byte-identical** copies, then swaps references in Admin login/nav, Staff waiter and Expo app icon/adaptive icon/splash/favicon + shared Brand component.
6. Run `node scripts/install-approved-marina-logo.mjs --verify-installed` and inspect all three apps visually. Run TypeScript/Next builds, physical Android E2E, and functional parity CI before PR approval.
7. Remove obsolete non-canonical assets only in a separately audited change, after no runtime references remain.

**State:** installer READY; exact logo installed in the design candidate. The instructions above remain available for clean installations and recovery. No repeated `--apply` is required for the verified current candidate. The installer does not merge, upload, or deploy.
