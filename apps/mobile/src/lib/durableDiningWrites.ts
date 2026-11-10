import { getDurableItem, removeDurableItem, setDurableItem } from './storage';

/** A pending POST is not evidence of failure. Keep the lock across app restarts. */
export type PendingDiningWrite = { operation: 'CREATE_TABLE' | 'CREATE_ORDER' | 'CREATE_MENU_DRAFT' | 'PRODUCTION_TARGET'; startedAt: string };

function key(hotelId: string, userId: string): string {
  // Live connection IDs contain the approved DNS hostname, including its dots.
  const validHotelId = hotelId.length <= 263 && /^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(hotelId);
  if (!validHotelId || !/^[A-Za-z0-9_-]{1,100}$/.test(userId)) {
    throw new Error('Unverified dining write identity');
  }
  return 'marina.dining.pending.' + hotelId + '.' + userId;
}

export async function readPendingDiningWrite(hotelId: string, userId: string): Promise<PendingDiningWrite | null> {
  const raw = await getDurableItem(key(hotelId, userId));
  if (!raw) return null;
  const value: unknown = JSON.parse(raw);
  if (!value || typeof value !== 'object') throw new Error('Invalid pending dining write');
  const record = value as Record<string, unknown>;
  if (!['CREATE_TABLE', 'CREATE_ORDER', 'CREATE_MENU_DRAFT', 'PRODUCTION_TARGET'].includes(String(record.operation)) ||
      typeof record.startedAt !== 'string') throw new Error('Invalid pending dining write');
  return record as PendingDiningWrite;
}

export async function beginPendingDiningWrite(hotelId: string, userId: string, operation: PendingDiningWrite['operation']): Promise<void> {
  // A second write must never overwrite a previous ambiguous outcome.
  if (await readPendingDiningWrite(hotelId, userId)) throw new Error('Pending dining write requires reconciliation');
  await setDurableItem(key(hotelId, userId), JSON.stringify({ operation, startedAt: new Date().toISOString() }));
}

export async function clearPendingDiningWrite(hotelId: string, userId: string): Promise<void> {
  await removeDurableItem(key(hotelId, userId));
}
