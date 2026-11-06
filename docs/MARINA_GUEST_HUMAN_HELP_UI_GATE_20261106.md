# MARINA SMART — Guest AI request-to-reception UI gate (P0)

Date: 2026-11-06. Separate Draft PR layered on #387.
**No customer site has been switched, no production guest request has been sent.**

## Scope and release safety

- Only existing `apps/web` Guest AI component + its parent request-list callback
  and CSS, narrow CI tests, documentation. **Do not merge or deploy automatically.**
- Default build behavior unchanged: button appears ONLY if build-time
  `NEXT_PUBLIC_MARINA_GUEST_HANDOFF_ENABLED=true` **AND** the server supplies
  the exact reviewed `human_handoff` read-only contract.
- The site-specific flag is intentionally **absent** from production Compose and
  existing DEMO / hotel01. Keep it disabled until real guest and reception acceptance.
- The existing guest AI response remains read-only; the server does not perform
  implicit guest request writes.

## Guest user journey

1. Guest signs in with the real room QR + valid stay PIN.
2. Guest asks MARINA AI a question; response proposes an optional
   `human_handoff` object with `status=NOT_REQUESTED` and `task_created=false`.
3. Only then can the UI show **Ask reception for help** in the correct locale.
4. Guest clicks the option, sees their exact question and an explicit
   **Confirm request** button (and Cancel). No write on initial click.
5. After confirmation the UI sends a single credentialed `POST` to the
   **fixed existing** `/core/api/v1/guest-os/rooms/{token}/requests` endpoint,
   body `{request_code:"ADMIN", description: <user question <=1200 chars>}`.
   It never uses arbitrary endpoint text or request code returned by the AI.
6. Only HTTP 201 with a returned task `id` is shown as **created**.
   HTTP 409 with `GUEST_REQUEST_DUPLICATE_ACTIVE` shows an already-open task,
   without resubmitting. If the network outcome is unknown, there is NO
   automatic retry: guest is told to inspect requests before trying again.
   Expired QR/PIN session closes the guest AI view.
7. Parent `GuestConciergeRuntime` reloads the guest request list. The same
   canonical staff queue supports RECEPTION/MANAGER/OWNER claim and completion;
   MAID/TECH cannot claim ADMIN.

## Local tests and limitations

- `npm run typecheck --prefix apps/web` **PASS** with Next.js 15.5.28.
- `python3 -m unittest scripts.test_marina_guest_handoff_ui_contract` **5/5 PASS**
  (static safety/regression assertions, not browser E2E).
- Existing server guest AI route/permission contract 11/11 PASS on parent #387.
- The temporary local Next QA route used to try browser interaction has been
  removed. Browser UI E2E was **not accepted**: the QA fixture encountered
  routing/import errors, and the Ubuntu host was near memory limits. Do not
  treat the attempted Chromium test as successful.
- Full guest QR/PIN → UI confirm → canonical DB task → reception claim →
  completion → guest observes DONE must run on a dedicated disposable
  single-hotel environment, plus mobile 390px viewport and RU/KG/EN.
- No real WhatsApp delivered status, AI inference, public DNS/TLS or offsite
  recovery has been accepted. **Commercial production remains NO-GO.**
