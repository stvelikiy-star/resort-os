# MARINA SMART — One-hotel public site publishing (P0)

**Scope:** A separate customer deployment with its own `PROPERTY_CODE`, PostgreSQL and staff.
**Release:** isolated integration branch, not public production approval.

## Safety boundary

- `compose.marina-production.yaml` sets `MARINA_CUSTOMER_SITE_SAFE_MODE=true` on its API and one-shot provisioner. Existing legacy resort deployments are unaffected.
- On initial one-shot provisioning, only the optional `CONTENT` module is enabled for the hotel's OWNER; other optional modules remain disabled. The OWNER may subsequently change module settings with the existing authenticated hotel-setup API. This prevents a newly provisioned owner from being locked out of the site's editor.
- The customer Web is a separate pinned Caddy service. It does not run the frozen Three Crowns / AK BERMET public Next.js app.
- Caddy proxies only browser `GET /` to `api:8000/api/v1/site/customer-page` (query `locale=ru|kg|en` preserved).
- Until explicitly published, the homepage is a neutral multilingual preparation page with `noindex`/no cache. Other HTML paths remain neutral, while old static resources, APIs and media return 503 from the Web origin.
- Actual public API `GET /api/v1/site/content?locale=...` returns **404** without a published document. No legacy default copy, contacts or media are returned.
- The API reads the `site_content_documents` row for the current installation's `PROPERTY_CODE` and locale only. No switching hotels.

## Explicit owner/manager CMS

Existing Admin's **Сайт / Контент** section detects `mode=customer` and shows the new editor, leaving the legacy editor alone.

Each of `ru`, `kg`, `en` has its **own** draft and published version:

- `hero.title`, `hero.subtitle`
- `contacts.phone`, `contacts.whatsapp`, `contacts.email`, `contacts.address`
- `seo.title`, `seo.description`

Fields are validated and escaped. Phone/WhatsApp cannot be arbitrary links, HTML is escaped and unknown sections rejected.
Public copy changes **only after** the explicit OWNER/MANAGER publish operation; a draft does not update the homepage.
An initial publish without a draft is rejected. Unauthenticated admin CMS remains 401.
Legacy content and seeded hotel marketing claims are never used as a fallback.

**API:**
- `GET /api/v1/admin/site/content` — own locale versions
- `PUT /api/v1/admin/site/content/{locale}/draft` — save structured draft
- `POST /api/v1/admin/site/content/{locale}/publish` — explicit publish
- `GET /api/v1/site/content?locale={locale}` — own published content only
- `GET /api/v1/site/customer-page?locale={locale}` — sanitized responsive landing HTML

## Acceptance completed on synthetic single hotel

- Python contract tests: 11/11 PASS.
- Real isolated HTTPS + PostgreSQL: unpublished 404/neutral page, OWNER login, CMS view, draft, publish, second version, RU/EN separation with KG unpublished, logout.
- Exact evidence: `/home/agent/marina-release-candidates/rc-customer-site-https-e2e-20261106.log`.
- No changes to HOTEL01, DEMO or other projects.

## NOT in scope / commercial NO-GO

This is a **minimal functioning hotel-owned landing page**, not a finished resort marketing site.
No photo/gallery presentation, room catalog, site layouts, per-hotel visual themes, booking widgets or real verified client contacts are accepted yet.
The real property owner must provide/approve copy, translations and contacts for their own languages.
Do not mark commercial GO until a customer domain/HTTPS, off-host backups, provider/AI acceptance, monitored rollback, mobile Android E2E and final sign-off pass.
