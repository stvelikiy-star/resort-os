import { isTrustedHotelOrigin, parseHotelAddress } from '../api/hotels';
import { getDurableItem, removeDurableItem, setDurableItem } from './storage';

const KEY = 'marina.pending-cookie-logouts.v1';
const MAX_PENDING_LOGOUTS = 20;
// Device-only list of PUBLIC HTTPS API origins; never store passwords or cookies.
let chain: Promise<void> = Promise.resolve();
let flushInFlight: Promise<void> | null = null;

function serialized<T>(work: () => Promise<T>): Promise<T> {
  const result = chain.then(work, work);
  chain = result.then(() => undefined, () => undefined);
  return result;
}
async function readUnsafe(): Promise<string[]> {
    // A storage or journal decoding failure is NOT evidence of no pending logout.
    const raw = await getDurableItem(KEY);
    const parsed: unknown = raw === null ? [] : JSON.parse(raw);
    if (!Array.isArray(parsed) || parsed.length > MAX_PENDING_LOGOUTS) {
      throw new Error('Invalid pending logout journal');
    }
    // Never silently discard an unrecognized queued logout. An invalid entry
    // means the journal cannot prove that any prior native cookie was revoked.
    for (const entry of parsed) {
      if (typeof entry !== 'string') throw new Error('Invalid pending logout journal entry');
      const origin = parseHotelAddress(entry);
      if (!origin.ok || origin.baseUrl !== entry) {
        throw new Error('Invalid pending logout journal entry');
      }
    }
    return [...new Set(parsed)];
}
async function writeUnsafe(values: string[]) {
  if (values.length > MAX_PENDING_LOGOUTS) throw new Error('Pending logout journal full');
  if (values.length) await setDurableItem(KEY, JSON.stringify(values));
  else await removeDurableItem(KEY);
}
export async function queueCookieLogout(baseUrl: string): Promise<void> {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok || parsed.baseUrl !== baseUrl || !isTrustedHotelOrigin(baseUrl)) {
    throw new Error('Cannot queue logout for untrusted hotel');
  }
  await serialized(async () => {
    const values = await readUnsafe();
    if (!values.includes(baseUrl)) {
      // Losing the oldest entry would permit login on a still-authenticated host.
      if (values.length >= MAX_PENDING_LOGOUTS) throw new Error('Pending logout journal full');
      values.push(baseUrl);
    }
    await writeUnsafe(values);
  });
}
export function hasUnrevokedCookieForHost(baseUrl: string): Promise<boolean> {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok) return Promise.resolve(true);
  const hostname = new URL(parsed.baseUrl).hostname;
  return serialized(async () => {
    try { return (await readUnsafe()).some(origin => new URL(origin).hostname === hostname); }
    catch { return true; } // Fails closed: journal unavailable is not proof of safe login.
  });
}
/**
 * Browser/native cookies are owned by the OS. Re-send the server logout only
 * for independently pinned origins; retain queue entry on any failed request.
 * A successful 204 clears it. Never claim server revocation while offline.
 */
export function flushPendingCookieLogouts(logout: (baseUrl: string) => Promise<void>): Promise<void> {
  if (flushInFlight) return flushInFlight;
  const task = (async () => {
    let origins: string[];
    try { origins = await serialized(readUnsafe); }
    catch { return; } // Do not assert revocation when persistence cannot be read.
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
