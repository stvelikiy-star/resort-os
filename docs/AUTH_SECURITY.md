# Three Crowns staff authentication security

## Login throttling policy

Resort Core applies a bounded failed-login window to staff username/password authentication.

Production defaults:

- window: 900 seconds;
- account + client-IP threshold: 5 failed attempts;
- client-IP spray threshold: 30 failed attempts;
- a successful login resets only the matching account + client-IP pair;
- no global account lock is created, avoiding a trivial distributed lockout/DoS against a known staff username;
- throttle state expires automatically when failure evidence ages out of the window.

Throttle state is derived from append-only `audit_logs` rows. The persisted resource identifiers are SHA-256 fingerprints only. Raw usernames, client IPs, passwords and session tokens are not written into throttle evidence.

PostgreSQL advisory locks serialize attempts sharing the same pair or client IP across API workers so concurrent failures cannot race past the threshold.

## Reverse proxy trust boundary

`AUTH_TRUST_PROXY_HEADERS=false` is the safe application default. In that mode Resort Core ignores `X-Forwarded-For` and uses the direct peer address.

The repository production topology is different: the API container has no published host port and is reachable from the public Internet only through the Caddy service on the private Docker network. For that topology `.env.production.example` and `compose.production.yaml` set `AUTH_TRUST_PROXY_HEADERS=true`, allowing Core to use the first Caddy-provided `X-Forwarded-For` client address.

Do not enable `AUTH_TRUST_PROXY_HEADERS=true` in a deployment where untrusted clients can connect directly to Resort Core or where an upstream proxy forwards spoofable client-IP headers unchanged.

If an additional CDN/load balancer is placed in front of Caddy, its trusted-proxy configuration must be reviewed before relying on forwarded client IPs.

## Configuration

```text
AUTH_TRUST_PROXY_HEADERS=true
AUTH_LOGIN_WINDOW_SECONDS=900
AUTH_LOGIN_PAIR_MAX_FAILURES=5
AUTH_LOGIN_IP_MAX_FAILURES=30
```

The IP threshold is forced by application code to remain greater than the pair threshold.

## Security acceptance

`Staff Auth Security CI` proves:

- repeated bad passwords reach the pair threshold;
- throttled requests preserve the same generic 401 response;
- a different client IP can still legitimately sign in (no global account lockout);
- successful login resets the matching pair;
- distinct usernames cannot bypass the source-IP spray threshold;
- trusted proxy client-IP separation works;
- concurrent attempts are serialized and cannot over-record past the pair threshold;
- expiry restores legitimate access;
- throttle audit evidence contains no raw username/IP/password values.

`Three Crowns Dependency Security Inspection` additionally audits the pinned Python backend requirements with a pinned `pip-audit` version and uploads machine-readable evidence.
