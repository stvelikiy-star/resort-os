import { isTrustedHotelOrigin, parseHotelAddress } from '../api/hotels';
import { getItem, removeItem, setItem } from './storage';

const KEY = 'marina.pending-cookie-logouts.v1';
// Device-only list of PUBLIC HTTPS API origins; never store passwords or cookies.
let chain: Promise<void> = Promise.resolve();
let flushInFlight: Promise<void> | null = null;

function serialized<T>(work: () => Promise<T>): Promise<T> {
  const result = chain.then(work, work);
  chain = result.then(() => undefined, () => undefined);
  return result;
}
async function readUnsafe(): Promise<string[]> {
  try {
    const raw = await getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return [...new Set(parsed
      .filter((s): s is string => typeof s === 'string')
      .filter(s => {
        const origin = parseHotelAddress(s);
        return origin.ok && origin.baseUrl === s;
      }))].slice(-20);
  } catch { return []; }
}
async function writeUnsafe(values: string[]) {
  if (values.length) await setItem(KEY, JSON.stringify(values.slice(-20)));
  else await removeItem(KEY);
}
export async function queueCookieLogout(baseUrl: string): Promise<void> {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok || parsed.baseUrl !== baseUrl || !isTrustedHotelOrigin(baseUrl)) {
    throw new Error('Cannot queue logout for untrusted hotel');
  }
  await serialized(async () => {
    const values = await readUnsafe();
    if (!values.includes(baseUrl)) values.push(baseUrl);
    await writeUnsafe(values);
  });
}
export function hasUnrevokedCookieForHost(baseUrl: string): Promise<boolean> {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok) return Promise.resolve(true);
  const hostname = new URL(parsed.baseUrl).hostname;
  return serialized(async () => (await readUnsafe()).some(origin => new URL(origin).hostname === hostname));
}
/**
 * Browser/native cookies are owned by the OS. Re-send the server logout only
 * for independently pinned origins; retain queue entry on any failed request.
 * A successful 204 clears it. Never claim server revocation while offline.
 */
export function flushPendingCookieLogouts(logout: (baseUrl: string) => Promise<void>): Promise<void> {
  if (flushInFlight) return flushInFlight;
  const task = (async () => {
    const origins = await serialized(readUnsafe);
    for (const origin of origins) {
      if (!isTrustedHotelOrigin(origin)) continue; // do not contact an untrusted old host
      try {
        await logout(origin);
        await serialized(async () => {
          await writeUnsafe((await readUnsafe()).filter(item => item !== origin));
        });
      } catch {
        // Offline, request timeout and 5xx all remain pending for next foreground.
      }
    }
  })();
  flushInFlight = task;
  void task.finally(() => { if (flushInFlight === task) flushInFlight = null; }).catch(() => {});
  return task;
}
