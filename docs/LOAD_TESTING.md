# Three Crowns Resort OS load/stress testing

This harness is for **CI/test/staging only**. It must not target the public production hostname or a live hotel database without a separately approved production performance plan.

## Scope

`tests/load/resort_core_read.k6.js` exercises read-heavy paths that are safe for staging pressure testing:

- `GET /ready`;
- `GET /api/v1/booking/check-availability`;
- optional authenticated `GET /api/v1/pms/grid`.

It intentionally does **not** create reservations, confirm payments, check guests in/out, mutate room state, create kitchen orders, or invoke provider integrations.

## Safety boundary

The script fails closed unless:

- `LOAD_TEST_ENV` is exactly `ci`, `test`, or `staging`;
- `LOAD_BASE_URL` is provided;
- the target is loopback or clearly marked as staging/test; or
- under `test`/`staging`, the target hostname exactly matches `LOAD_EXPLICIT_TEST_HOST`.

`3korony.com` and `www.3korony.com` are always rejected and cannot be re-enabled through `LOAD_EXPLICIT_TEST_HOST`.

`LOAD_EXPLICIT_TEST_HOST` exists only for externally hosted integration environments whose generated provider hostname does not contain `test` or `staging`. It must be the exact hostname from `LOAD_BASE_URL`; it is not a suffix, wildcard or domain pattern.

Authorized PMS-grid pressure is off by default. To enable it, set `LOAD_AUTH_GRID=true` plus staging-only owner credentials. Never commit those credentials.

## Default pressure profile

The default profile ramps:

- 10 VUs for 30 seconds;
- 25 VUs for 60 seconds;
- 50 VUs for 60 seconds;
- ramp down for 30 seconds.

Thresholds:

- request failure rate < 1%;
- overall p95 < 1000 ms;
- overall p99 < 2000 ms;
- availability p95 < 1000 ms;
- PMS grid p95 < 1200 ms when enabled.

These are initial acceptance thresholds, not permanent SLOs. After the first real Beget/VPS staging run, record CPU, RAM, PostgreSQL connections, Caddy latency, error rates, and WSS behavior before increasing concurrency.

## Run

From repository root on a Linux staging host or CI runner with Docker:

```bash
export LOAD_TEST_ENV=staging
export LOAD_BASE_URL=https://staging.example.invalid
bash scripts/run_load_test.sh
```

For the verified Railway **Three Crowns Full Test** API only, the generated hostname contains the word `production` even though the project is an integration/test environment. Authorize it by exact hostname, not by weakening the global guard:

```bash
export LOAD_TEST_ENV=test
export LOAD_BASE_URL=https://api-production-f1171.up.railway.app
export LOAD_EXPLICIT_TEST_HOST=api-production-f1171.up.railway.app
bash scripts/run_load_test.sh
```

The repository workflow `.github/workflows/fulltest-load-baseline-ci.yml` runs this exact Full Test target with the default 10 -> 25 -> 50 VU read-only profile. No PMS credentials are supplied, so it exercises only readiness and public availability reads.

Optional authenticated PMS-grid pressure:

```bash
export LOAD_AUTH_GRID=true
export LOAD_OWNER_USERNAME='staging-owner'
export LOAD_OWNER_PASSWORD='set-outside-repo'
bash scripts/run_load_test.sh
```

## Higher pressure after baseline passes

Example 25 -> 100 -> 250 VUs:

```bash
export LOAD_VUS_1=25
export LOAD_VUS_2=100
export LOAD_VUS_3=250
export LOAD_STAGE_1=60s
export LOAD_STAGE_2=120s
export LOAD_STAGE_3=180s
export LOAD_STAGE_4=60s
bash scripts/run_load_test.sh
```

Do not raise concurrency on an unobserved server. First confirm resource headroom, PostgreSQL pool behavior, application error rate, and recovery after the test.

## Required launch evidence

A production-cutover performance record should include:

1. exact tested Resort OS commit/image digest;
2. target staging hostname and server specification;
3. k6 summary and thresholds;
4. CPU/RAM/disk/network observations;
5. PostgreSQL connection and slow-query observations;
6. Caddy/Core/Admin/Staff logs during pressure;
7. restart/recovery health after the test;
8. confirmation that no production data or provider side effects were used.
