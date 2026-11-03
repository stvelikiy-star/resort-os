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

/** Only https hosts (and demo://) are accepted; no credentials/ports tricks, no http. */
export function parseHotelAddress(input: string): { ok: true; baseUrl: string } | { ok: false; reason: 'secureOnly' | 'invalid' } {
  const raw = input.trim();
  if (!raw) return { ok: false, reason: 'invalid' };
  if (/^http:\/\//i.test(raw)) return { ok: false, reason: 'secureOnly' };
  const candidate = /^https:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const u = new URL(candidate);
    const hostname = u.hostname.toLowerCase();
    // Hotel connections carry authenticated cookies: reject IP literals, internal
    // names, alternate ports and ambiguous hostnames from untrusted QR codes.
    const labels = hostname.split('.');
    const validDns = labels.length >= 2 && labels.every((part) =>
      part.length > 0 && part.length <= 63 && /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(part));
    const ipAddress = /^\\d+\\.\\d+\\.\\d+\\.\\d+$/.test(hostname) || hostname.includes(':');
    const internal = ['local', 'localhost', 'internal', 'test', 'invalid'].includes(labels[labels.length - 1]);
    if (u.protocol !== 'https:' || u.username || u.password || u.port ||
        !validDns || ipAddress || internal || hostname.length > 253) {
      return { ok: false, reason: 'invalid' };
    }
    return { ok: true, baseUrl: `https://${hostname}` };
  } catch {
    return { ok: false, reason: 'invalid' };
  }
}
