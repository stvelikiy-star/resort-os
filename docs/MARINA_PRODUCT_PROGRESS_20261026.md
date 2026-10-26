# MARINA SMART: product completion, 2026-10-26

## Approved scope

Complete the existing product without changing the approved architecture, roles,
navigation or compact chessboard. Do not access or update the owner's Ubuntu.
The marketing website will link to the actual isolated demo platform in a new
tab; an embedded/reimplemented chessboard is no longer the delivery target.

## Source reconciliation

Working branch: `fix/marina-staging-preflight-20261020`, starting at
`f8aa2ca22199e6b12128c6b72014b137dd0f26ff`. All 269 remote branch heads were
fetched and inventoried. 135 are ancestors of that starting commit. A branch
not being an ancestor does not prove missing work: rebased and squash-merged
changes have different history. Direct blob comparisons confirm the candidate
contains the CSV batch intake, CSV UI and channel mappings from the relevant
channel branches. Do not blindly merge all old branches or import Three Crowns
configuration into MARINA.

The guest-marketplace presentation changes on
`fix/marina-staging-guest-marketplace-ux-20261022` still differ from this
candidate. Review that existing work separately; this patch does not include
its imagery or redesign. No extra remote branches were created.

## Completed in this change

- Guest QR context loads hotel identity from the resolved QR's property ID.
  Product settings, hotel policy and published RU CMS contacts are joined using
  that same ID. Only name is returned before PIN authentication; authenticated
  guests receive the selected guest-facing contact/checkout fields, never the
  full hotel policy or draft CMS content.
- Guest UI uses that hotel name, configured checkout time and contact details.
  It no longer directs every hotel to the AK BERMET phone/WhatsApp number or
  claims a fixed check-in/checkout time. Telephone links require phone-shaped
  values; WhatsApp links require configured digits or an exact HTTPS wa.me URL.
  The existing contact buttons remain available when the hotel configures them.
- Guest document metadata describes MARINA SMART generically rather than
  identifying every hotel as AK BERMET.
- The MARINA production package supplies GUEST_OS_PUBLIC_BASE_URL from its
  configured public hostname. This is a repository fix, not a host deployment.
- Added property isolation/unknown-settings tests, a synthetic HTTP stay lifecycle
  and a focused guest browser fixture. Wired the new checks into existing CI.
- Updated stale concierge/marketplace contracts to verify the current hotel
  settings, waiter workspace, role dependencies and folio-charge semantics.
  Assertions still distinguish a charge from a received payment.

## Validation and its limits

Local builds of Web, Admin and Staff passed. The final Web build includes the
guest identity changes. Locale guards, Python/JS syntax, workflow/Compose YAML
parsing and diff whitespace checks passed. The focused suite passed 34 tests
plus 25 subtests.

Native PostgreSQL cannot start under this workspace's mapped-root-only runtime.
An auxiliary PGlite wire-protocol process applied the 36 committed SQL migrations
and exercised the actual FastAPI endpoints. It is not a product dependency and
is not committed. Local runtime evidence covers:

- owner authentication and availability;
- booking preview/commit and overlap rejection (409);
- check-in, QR issuance, PIN authentication, configured hotel contact/checkout;
- guest request creation and access revocation after checkout;
- owner chessboard month/year, 31-day view and mobile layout over HTTP;
- browser guest identity in RU/KG/KZ/EN, contact-link validation and switching
  between two mocked hotel settings without retaining the previous identity.

The auxiliary engine requires a single connection. Therefore the local owner
browser run disables WebSocket and proves HTTP fallback only. It does not prove
native PostgreSQL concurrency, WSS, backup/restore or public hosting. The
committed GitHub workflow retains native PostgreSQL and the normal application
pool/WebSocket configuration. Wait for those native checks before marking this
change CI-verified.

## Remaining stages (not complete)

| Stage | Remaining acceptance |
| --- | --- |
| Core PMS | Full edit/cancel/HOLD/relocation, financial reconciliation and concurrent booking checks |
| Staff | Browser acceptance of each role, task completion and session revocation |
| Guest | Service pricing, kitchen ordering, reviews and navigation with configured hotel data |
| Interface | Screen-by-screen mobile, language, error and usability review |
| Integrations | Actual WhatsApp provider, AI credentials, OTA provider, payment merchant and locks E2E |
| Public demo | Approved existing non-Ubuntu host/database, disposable data lifecycle, role entry and public HTTPS |
| Website | Link to a verified public demo URL; no invented URL and no embedded chessboard |

Read-only inventory found no MARINA-named Vercel project in the queried scope
and no active MARINA database in the connected Supabase project list. This does
not prove no other hosting exists. Do not repurpose the KÖL database or resume
another hotel's inactive project. Railway is not the selected deployment target.

The overall product and public demo are **not finished**. External integrations
remain disconnected until their actual access and end-to-end results exist.
