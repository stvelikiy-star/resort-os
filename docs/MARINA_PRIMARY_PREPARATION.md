# Preparing the shared MARINA platform

Status: repository preparation only. This document does not designate an existing
test stack as production and does not deploy an application.

The selected product target is a shared platform for multiple hotels, with a
common entry point and isolated hotel workspaces. This is an explicit target,
not a claim that the current deployment package already provides that product.

The existing `MARINA_DEMO` and `MARINA_HOTEL01` objects are reserved synthetic
identities. Keep their data and credentials separate. The production preflight
rejects these codes, their existing stack slugs, and synthetic seed confirmation
markers, even if the proposed configuration otherwise looks valid.

Use `compose.marina-production.yaml` and the existing
`MARINA_UBUNTU_PRODUCTION_RUNBOOK.md`. That package currently describes one
application stack and database per hotel. It does not establish a deployed
self-service multi-hotel platform. It is a per-hotel component deployment option,
not the complete shared platform release.

## Confirmed source blockers for a shared backend

An opt-in staging authentication slice is now implemented separately; see
`MARINA_SHARED_AUTH_PREVIEW.md`. It addresses login/session selection only and
blocks all workspace routes. The baseline restrictions described below still
explain why the default per-hotel deployment cannot simply become a shared PMS.

In the inspected baseline, `services/api/app/auth.py` still resolves login using
the deployment-global `PROPERTY_CODE`. `current_user` also rejects a session
whose property differs from that global code. `trusted_property_id` has a
database-derived tenant branch, but enabling its flag does not remove these
separate login/session restrictions. The WhatsApp connector also binds to the
runtime's single property. Do not enable a tenant flag and call that a completed
multi-hotel deployment.

The next implementation must establish the trusted hotel selection and login
flow, then carry the authenticated property/tenant through every protected
route and provider binding. A browser-provided property header is not authority.
The architecture must also specify how a hotel is created and its first owner
receives access; the existing one-shot empty-database provisioner is not a
verified shared-platform onboarding flow.

Acceptance must include two hotels with the same staff username, a user and
session from each hotel, invalid/disabled tenant state, cross-property IDs,
guessed hotel selectors, revoked staff access and per-hotel WhatsApp secrets.
Both allowed work and forbidden cross-hotel access must be verified on the
selected deployment topology before shared-platform production approval.

## Deployment inputs

Before generating an applicable environment file, record these real inputs:

1. The intended first production hotel/object and a new, unique identity.
2. Its permanent hostnames, certificate contact, and the verified HTTPS ingress
   available on the target server. Do not redirect the marketing website or
   public demo as a side effect.
3. The selected release commit and the source-to-image identity of all four
   application services. A successful workflow is not evidence of a deployment.
4. Available host memory, port ownership and capacity alongside existing services.
5. A working private off-host backup destination with a dedicated prefix.
6. Whether any existing test data is approved for migration. Until decided,
   preserve it and initialise no production database from synthetic seed scripts.

Unknown values must remain explicitly unresolved. Do not fill them with example
hostnames, arbitrary property names, guessed credentials or success flags. Do not
disable an existing production gate merely to make its output say PASS.

Sequence: validate the explicit target and release; prepare backups and prove a
separate restore; provision the new database with the guarded production
provisioner; verify PMS and roles; then connect messaging and AI in separate
acceptance steps. Persistent data, migrations, application rollback and provider
authorisation each need their own evidence.

The preflight guards are a static boundary only. They do not establish server
capacity, DNS ownership, database contents, absence of symlinks or the identity of
currently running images. Host acceptance remains necessary.
