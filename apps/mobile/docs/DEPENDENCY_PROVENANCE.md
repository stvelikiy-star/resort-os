# Dependency vulnerability provenance — diagnostics, NOT a release exception

This app uses Expo SDK 58, Jest 30 and related mobile build tools. The pinned
security candidate in PR #297 resolves Expo-side glob/minimatch transitive
versions and brings `npm audit --omit=dev` from 27 to 19 advisory package
reports (18 moderate + 1 low at the verified commit).

## Why `--omit=dev` still reports Jest

The npm lock marks some transitive Jest dependencies `devOptional: true`.
npm audit can nevertheless report their advisory chains when invoked with
`--omit=dev`. Thus `npm audit` output cannot, by itself, establish which
JavaScript libraries are bundled into Android/iOS, nor is counting transitive
advisories equivalent to counting independently exploitable vulnerabilities.

`scripts/audit-provenance.mjs` checks each reported affected node against
the **same checked-in lockfile** and classifies the complete advisory as
`devOrDevOptionalOnly`, `potentialRuntimeOrBuild`, or `unverified`.
Its Node tests exercise all three outcomes, including failures for missing
node metadata. CI publishes the raw audit and classification JSON for
independent review, without changing the underlying full audit gate.

This diagnostic **must not be used to make a red audit green**. A devOptional
classification is not proof of exclusion from the signed native artifact,
and a transitive dependency can be loaded in tooling at build time.
`npm audit --omit=dev --audit-level=moderate` continues to fail while
moderate-or-higher advisories remain.

## Outstanding release gates

1. Security-owner decision on remaining Jest/toolchain findings, severity,
   exploitability and expiry; evaluate compatible upstream updates, avoid
   blindly applying `--force` to the Expo SDK.
2. Native APK/iOS software bill of materials, signed-artifact inspection,
   physical-device E2E and release signing review.
3. Real hotel tenant/auth/booking idempotency E2E and backend issue #295.
4. Issue #296 tracks all unclosed findings; this report alone closes none.

No PMS backend, demo, app store distribution, financial data or hotel database
changes are part of this work.
