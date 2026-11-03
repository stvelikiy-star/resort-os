export interface HotelConnection {
  id: string;
  name: string;
  city: string;
  /** https base URL of THIS hotel's own API host. Never shared between hotels. */
  baseUrl: string;
  demo: boolean;
  accent: string;
}

/** Demo catalogue — never contacts a network. */
export const DEMO_HOTELS: HotelConnection[] = [
  { id: 'demo-marina-issykkul', name: 'MARINA Issyk-Kul', city: 'Cholpon-Ata', baseUrl: 'demo://marina-issykkul', demo: true, accent: '#245E9A' },
  { id: 'demo-sunrise-bishkek', name: 'Sunrise Bishkek', city: 'Bishkek', baseUrl: 'demo://sunrise-bishkek', demo: true, accent: '#BBCFE6' },
];

/** A hotel may expose API at its origin or behind the known /core reverse-proxy prefix. */
export function hotelConnectionId(baseUrl: string): string {
  const url = new URL(baseUrl);
  return `live-${url.hostname}${url.pathname === '/core' ? '-core' : ''}`;
}

/** HTTPS only, one explicitly approved API prefix and no credentials/ports tricks. */
export function parseHotelAddress(input: string): { ok: true; baseUrl: string } | { ok: false; reason: 'secureOnly' | 'invalid' } {
  const raw = input.trim();
  if (!raw) return { ok: false, reason: 'invalid' };
  if (/^http:\/\//i.test(raw)) return { ok: false, reason: 'secureOnly' };
  const candidate = /^https:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const u = new URL(candidate);
    const hostname = u.hostname.toLowerCase();
    const prefix = u.pathname.replace(/\/+$/, '');
    // Hotel connections carry authenticated cookies: reject IP literals, internal
    // names, alternate ports and ambiguous hostnames from untrusted QR codes.
    const labels = hostname.split('.');
    const validDns = labels.length >= 2 && labels.every((part) =>
      part.length > 0 && part.length <= 63 && /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(part));
    const ipAddress = /^\d+\.\d+\.\d+\.\d+$/.test(hostname) || hostname.includes(':');
    const internal = ['local', 'localhost', 'internal', 'test', 'invalid'].includes(labels[labels.length - 1]);
    if (u.protocol !== 'https:' || u.username || u.password || u.port ||
        !validDns || ipAddress || internal || hostname.length > 253 ||
        (prefix !== '' && prefix !== '/core') || u.search || u.hash) {
      return { ok: false, reason: 'invalid' };
    }
    return { ok: true, baseUrl: `https://${hostname}${prefix}` };
  } catch {
    return { ok: false, reason: 'invalid' };
  }
}

/**
 * Compiled-in trust anchors. This is public configuration, NOT a secret and
 * must be provisioned from independently verified hotel onboarding records.
 * A QR, hostname similarity or a remote self-issued /.well-known file is NOT
 * a trust anchor. No configured origins => LIVE sign-in fails closed.
 *
 * e.g. EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS=https://hotel.example/core
 * No wildcard, suffix, scheme downgrade or untrusted API redirect is allowed.
 */
export function approvedHotelOrigins(configured = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS ?? ''): readonly string[] {
  const origins = new Set<string>();
  for (const entry of configured.split(',')) {
    const candidate = entry.trim();
    if (!candidate || candidate.includes('*')) continue;
    const parsed = parseHotelAddress(candidate);
    // Exact canonical HTTPS URL only; no hidden normalization of trusted config.
    if (parsed.ok && parsed.baseUrl === candidate) origins.add(parsed.baseUrl);
  }
  return [...origins];
}
export function isTrustedHotelOrigin(
  candidate: string,
  configured?: string,
): boolean {
  const parsed = parseHotelAddress(candidate);
  if (!parsed.ok) return false;
  return approvedHotelOrigins(configured).includes(parsed.baseUrl);
}
