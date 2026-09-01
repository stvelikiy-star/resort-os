# THREE CROWNS — PRODUCTION MONITORING CONTRACT

Date: 2026-09-01
Status: REPOSITORY CONTRACT / REAL BEGET EVIDENCE REQUIRED

This document defines the minimum production monitoring acceptance for Resort OS. Repository CI proves the checker behavior only; it does not prove that Beget monitoring is active.

## Machine check

Run from the deployment root on the actual host after the stack and backup schedule are configured:

```bash
python3 scripts/production_monitoring_check.py \
  --compose-file compose.beget.yaml \
  --env-file .env.production \
  --backup-dir /srv/three-crowns/backups \
  --disk-path /srv/three-crowns \
  --require-offsite \
  --require-network \
  --endpoint core=https://staging.3korony.com/core/health/ready \
  --endpoint public=https://staging.3korony.com/ \
  --endpoint admin=https://admin-staging.3korony.com/ \
  --endpoint staff=https://staff-staging.3korony.com/ \
  --tls-host staging.3korony.com \
  --tls-host admin-staging.3korony.com \
  --tls-host staff-staging.3korony.com
```

Use the real accepted hostnames. Do not copy the example hostnames into production without matching DNS/TLS configuration.

Default fail-closed thresholds:

- required services: `caddy`, `api`, `web`, `admin`, `staff`, `n8n`;
- every app service except Caddy must report Docker health `healthy`;
- restart count: maximum 3 per container at the time of acceptance;
- recent API 5xx window: maximum 0 in the default 15-minute window;
- latest successful backup receipt: maximum age 24 hours;
- backup SHA-256 integrity must verify;
- when `--require-offsite` is set, receipt must say `OFFSITE_STATUS=VERIFIED_UPLOAD`;
- disk usage: maximum 85%;
- TLS certificate: minimum 14 days remaining;
- `--require-network` requires actual HTTP endpoints and TLS hosts.

Any failed condition prints `ALERT:` and ends with `RESULT: PRODUCTION MONITORING RED` and non-zero exit. A clean run ends with `RESULT: PRODUCTION MONITORING GREEN`.

## Backup evidence

`scripts/production_backup.sh` writes `/srv/three-crowns/backups/last-success.env` only after all required steps complete successfully. It contains no credentials and records:

- completion timestamp;
- exact local backup target;
- `OFFSITE_STATUS` (`VERIFIED_UPLOAD` or `LOCAL_ONLY`);
- non-secret S3 prefix when applicable.

A failed backup run does not advance the receipt. Therefore an old receipt becomes stale and the monitoring checker turns RED instead of treating a cron invocation as backup success.

The target backup directory must contain a non-empty `postgres.dump` plus a valid `SHA256SUMS`. The checker rejects a receipt whose target escapes the configured backup directory.

## 5xx visibility

FastAPI already emits privacy-conscious structured `http_request` records containing request ID, method, path, HTTP status and duration. The monitoring checker reads the API service logs for the configured window and counts only structured `http_request` records with status >=500.

The logs intentionally do not contain request bodies, authorization headers, cookies, guest contact data, message text or provider credentials.

## Alert delivery

The checker is the machine gate, not an alert transport. On the real host it must be scheduled by the chosen host monitoring/cron/systemd mechanism so a non-zero result reaches an operator. The external launch evidence must identify the actual scheduler and notification destination and include a tested RED-to-notification result.

Do not claim alerting is verified merely because this script exists in Git.

## Provider health boundary

Do not infer WhatsApp, Instagram, Telegram, OpenAI or other provider health from Core readiness. Every provider enabled at launch keeps its separate real-provider E2E/health evidence under the launch acceptance gate. Disabled providers are `NOT_REQUIRED` where allowed.

## Acceptance evidence required on Beget

Before production GO retain non-secret evidence of:

1. one GREEN monitoring run on the exact deployed SHA/image set;
2. one deliberate safe RED test that reaches the responsible operator through the real alert path;
3. current backup receipt and verified off-site upload;
4. TLS-expiry check;
5. disk check;
6. container health/restart check;
7. 5xx-window check;
8. monitoring schedule/cadence and responsible owner.

CI evidence is necessary but not sufficient for this external gate.
