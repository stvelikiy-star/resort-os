/**
 * An HTTP 401 may arrive AFTER the user has switched from tenant A to B.
 * Bind each protected request to the *currently verified* host session.
 * A late response from A is not allowed to revoke the newer B session.
 *
 * Never register a handler for an unverified host, a QR address or DEMO.
 * No cookies, bearer tokens, passwords or guest records are stored here.
 */
interface VerifiedHost {
  notify: () => void;
}
const verifiedHosts = new Map<string, VerifiedHost>();

function hostOf(baseUrl: string): string {
  return new URL(baseUrl).hostname.toLowerCase();
}

/** Register after a login + /auth/me identity match; cleanup on switch/logout. */
export function bindVerifiedHost(baseUrl: string, notify: () => void): () => void {
  const host = hostOf(baseUrl);
  const binding: VerifiedHost = { notify };
  verifiedHosts.set(host, binding);
  return () => {
    if (verifiedHosts.get(host) === binding) verifiedHosts.delete(host);
  };
}

/** Request-scoped snapshot: MUST be taken before fetch starts, not at 401. */
export function captureVerifiedHost(baseUrl: string): object | null {
  return verifiedHosts.get(hostOf(baseUrl)) ?? null;
}

/** Fail closed ONLY if the old request still belongs to the same session. */
export function rejectVerifiedHost(baseUrl: string, snapshot: object | null): void {
  if (!snapshot) return;
  const current = verifiedHosts.get(hostOf(baseUrl));
  if (current === snapshot) current.notify();
}
