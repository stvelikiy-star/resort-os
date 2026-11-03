# Shared authentication: isolated staging slice

Status: implementation and test preparation, not production approval.

The default single-property login is unchanged. The new mode is opt-in with
`MARINA_SHARED_AUTH_PREVIEW_ENABLED=true`, `APP_ENV=staging` and
`MARINA_TENANT_CONTEXT_ENABLED=true`. Existing MARINA_DEMO/MARINA_HOTEL01 runtimes
are refused. It belongs in a separate synthetic staging database.

The login accepts `tenant_code`, `property_code`, `username` and `password`. Codes
are selectors, not authority: the database must resolve that active tenant and
property, then verify the staff account in that property. No public list of
hotels/accounts or trust in X-Tenant-Id/X-Property-Id/X-Role is introduced.

Sessions use the existing auth_sessions table without a schema migration. The
entire random contextual token is hashed for the DB lookup. Embedded tenant and
property UUIDs are compared with the currently authenticated staff membership
after the DB lookup; they cannot grant authority on their own. Changed tenant
membership, revoked/expired session, inactive user or inactive tenant is refused.
The preview and legacy session formats cannot be used interchangeably.

The ASGI boundary permits auth login/logout/me/mode and health endpoints.
In an isolated staging-only review branch, it additionally permits the tenant-scoped
read-only GET `/api/v1/admin/dashboard` and GET `/api/v1/pms/grid` endpoints.
All other HTTP routes return 503 and WebSockets are closed before their handlers
run. PMS writes, staff administration, shared onboarding and provider operations
remain blocked. These two read-only endpoints do NOT constitute a usable shared
PMS rollout or production approval. The gate is installed in the canonical app;
real PostgreSQL + canonical ASGI route acceptance is required before integration.

The new `/shared-auth-preview` Admin page checks the server's explicit auth mode
before offering the form. It displays the verified session, without opening PMS.
The regular demo/Admin/Staff login forms and deployment files are not modified.

Known-workspace attempts retain database-backed throttling, scoped by the hotel
selector. A bounded per-process IP limiter covers all attempts, including unknown
selectors. It is not a production-wide distributed limiter. Tenant onboarding,
member selection across multiple hotels, recovery, remaining route isolation,
per-hotel provider secrets and operational workspaces remain separate steps.

Validation consists of local API tests with simulated DB state, legacy regression
tests, and a dedicated real PostgreSQL CI scenario against committed migrations.
The CI runner requires an explicit confirmation and only accepts the disposable
localhost database marina_shared_auth_ci. Until its result is observed, do not
claim that PostgreSQL acceptance passed or that the platform is deployed.
