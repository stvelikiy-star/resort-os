# MARINA SMART — five-role LIVE native QA gate (test-only)
The existing CI proves four **DEMO** roles on both Android and iOS. This
harness is a separate, fail-closed LIVE smoke scenario and is **not yet
executed**. It does not authorize a release.

## Prerequisites
- Build a *separate* QA APK or unsigned iOS Simulator .app with
  `EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS=https://agent-vivobook-asuslaptop-x412ua.tail2066a4.ts.net/core`.
  Confirm the compiled origin on the build. Do not reuse DEMO artifact.
- Use a secure runner with Maestro and temporary synthetic MARINA_FINAL_QA
  users only, named `marina_nativeqa_*` (or `marina_qa_*`).
- Inject `MARINA_QA_ORIGIN`, `MARINA_NATIVE_QA_BUILD_ORIGIN`,
  `MARINA_QA_ROLE`, `MARINA_QA_USERNAME`, `MARINA_QA_PASSWORD` as runner
  secrets/environment variables. Never commit a password or put one in
  workflow_dispatch inputs, job arguments, screenshot captions, or logs.
- Independently check the backend APP_ENV=staging, property=MARINA_FINAL_QA,
  database=marina_final_a8830db before provisioning temporary users. Delete
  them after testing and assert none remain.

`bash scripts/design/fl2-native-live-role.sh` tests one role per run.
Run OWNER, RECEPTION, COOK, WAITER, STORE_STAFF separately, clearing app state
and iOS Keychain each time. The script verifies the exact QA origin and
rejects arbitrary or non-synthetic credentials, redirects Maestro logs to an
unpublished temporary file, and reports only PASS/FAIL + role.

This proves **native TLS auth + role landing screen** only, not live booking,
check-in/out, stock postings, restaurant folio, actual device performance,
or full mobile parity. Run separate guarded operational E2E and SQL
reconciliation before claiming mobile release readiness.

No public GitHub Action may receive accounts via plaintext workflow inputs.
GitHub CLI on the Ubuntu host is not authenticated for managing repository
secrets; secret creation is currently an external prerequisite, not DONE.
