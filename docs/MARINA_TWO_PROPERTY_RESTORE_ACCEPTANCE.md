# MARINA two-property isolation and restore acceptance

The automated workflow creates two synthetic tenants, two properties and two
owners with the same username but different passwords in a disposable local
PostgreSQL database. It starts two API processes from the candidate, each pinned
to its own PROPERTY_CODE with tenant context enabled.

The test checks each owner's grid, reception and CRM records; foreign reservation
detail/schedule and quote denial; header spoofing in both directions; foreign
password rejection and foreign session-cookie rejection. No AI provider call is
made. Both processes are stopped before the database snapshot and pg_dump.

The dump is restored into a separate empty disposable database. Every public
table's canonical row hash and row count, plus all public constraint definitions,
must match. The full API isolation test then runs against the restored database.

The runner requires CREATE_SYNTHETIC_LOCAL_ONLY, a localhost PostgreSQL host and
database names beginning with marina_isolation_. It refuses a populated source
or target and never drops a database. The workflow uses no external account,
production data, domain, customer credentials or provider secrets.

Passing this workflow proves the property-pinned two-runtime deployment mode in
CI. It does not prove a single shared API can authenticate every tenant, browser
acceptance for every role, external staging, target customer backup/restore or
production readiness. Those remain separate gates.
