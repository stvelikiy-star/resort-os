# MARINA SMART guest AI provider-outage human fallback — 2026-11-06

Scope: guest portal staging only, layered on PR #390.
**Not deployed, default feature flag OFF, never changes DEMO or HOTEL01.**

## Observed failure

Actual isolated single-property HTTPS API and PostgreSQL test confirmed QR/PIN
and Guest OS ADMIN request → RECEPTION claim → DONE work end-to-end.
However, MARINA AI had no real OpenAI provider configuration and returned
HTTP 503. Before this patch the Guest AI panel exposed no way to request staff
assistance from within that panel because the optional handoff was displayed
only after a successful AI answer.

## Narrow behavior

When the active guest's AI chat returns exactly HTTP **503**, show the
localized *assistant temporarily unavailable* message, and **only when**
`NEXT_PUBLIC_MARINA_GUEST_HANDOFF_ENABLED=true` show the option to contact
reception. Guest must first choose the option and independently press
**Confirm request**; no task or provider message is created automatically.

The confirmation reuses the *existing*, authenticated
`POST /core/api/v1/guest-os/rooms/{token}/requests` with a fixed
`request_code=ADMIN`, never a URL or instruction produced by AI.
The server verifies the QR/PIN cookie and active stay before any write.
HTTP 401 and 404 do NOT present the fallback; unauthenticated guests cannot
create an ADMIN task. Network ambiguity and duplicate protection remain.

The AI endpoint still responds with **503** when provider is absent.
No fake model response, no suppression of real provider errors, no weakening
of trust or role gates. The admin request is explicitly human-initiated.

## Targeted acceptance

- 6/6 local regression tests PASS.
- Browser CI on GitHub must show 503 fallback creates 0 requests before
  explicit guest confirmation, exactly 1 afterward, and 401 creates 0 tasks.
- Existing successful AI-answer handoff, cancellation, duplicate 409,
  network failure and invalid handoff metadata tests remain mandatory.
- End-to-end real synthetic QR/PIN → PostgreSQL task → RECEPTION DONE was
  already verified separately on running staging API with real DB.
- Browser QA still uses a synthetic API; full deployed UI+real API E2E,
  real OpenAI inference and genuine Green API delivery are **not accepted**.

Commercial status: NO-GO pending external provider UAT, off-host backup,
public TLS, external alerts, full rollback and physical Android E2E.
