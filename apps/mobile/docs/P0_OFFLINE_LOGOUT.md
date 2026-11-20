# Cookie-session revocation retry (mobile-side interim)

Current backend uses 12-hour HTTP-only cookie sessions, not revocable mobile device tokens. This mobile update provides **local logout immediately**, persists a **non-secret list of verified hotel API origins** for which the server did not yet acknowledge logout, and retries `POST /auth/logout` when the app returns to foreground or at startup. When signing in to a host with pending revocation, the app first tries remote logout and **blocks new credentials** until the pending request is acknowledged.

- Queue contains public canonical HTTPS origins only; **no cookies, passwords, token or guest data** are stored.
- Only trusted app-build allowlisted origins can be contacted on retry; old untrusted origins remain pending without contacting the domain.
- On success 204 the entry is cleared; on failure it stays queued. It is safe to repeat logout against the existing server.
- Switching hotel from profile also initiates a logout, not only client-side removal.
- This does **NOT** revoke an offline server cookie until connectivity is restored, does **NOT** prevent browser access to a cookie shared by the OS, and is **NOT** a replacement for backend device bound rotating refresh tokens / server-side revocation. Backend request: #295.
- Retention is at most 20 origins and relies on best-effort platform secure storage; it must be verified on physical Android and iOS, including process kill, reboot, and offline transitions.
- Read-only tests cover queue survival, replay, host aliases and untrusted origins. Physical-device acceptance is NOT RUN.

Keep this in a draft PR; do not deploy or release on this feature alone.
