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
  { id: 'demo-marina-issykkul', name: 'MARINA Issyk-Kul', city: 'Cholpon-Ata', baseUrl: 'demo://marina-issykkul', demo: true, accent: '#0A9996' },
  { id: 'demo-sunrise-bishkek', name: 'Sunrise Bishkek', city: 'Bishkek', baseUrl: 'demo://sunrise-bishkek', demo: true, accent: '#E9B872' },
];

/** Only https hosts (and demo://) are accepted; no credentials/ports tricks, no http. */
export function parseHotelAddress(input: string): { ok: true; baseUrl: string } | { ok: false; reason: 'secureOnly' | 'invalid' } {
  const raw = input.trim();
  if (!raw) return { ok: false, reason: 'invalid' };
  if (/^http:\/\//i.test(raw)) return { ok: false, reason: 'secureOnly' };
  const candidate = /^https:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const u = new URL(candidate);
    if (u.protocol !== 'https:' || u.username || u.password || !u.hostname.includes('.')) return { ok: false, reason: 'invalid' };
    return { ok: true, baseUrl: `https://${u.host}` };
  } catch {
    return { ok: false, reason: 'invalid' };
  }
}
