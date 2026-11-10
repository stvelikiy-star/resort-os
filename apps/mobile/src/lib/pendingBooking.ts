import { getDurableItem, removeDurableItem, setDurableItem } from './storage';

export interface PendingBooking {
  recorded_at: number;
  room_id: string;
  check_in: string;
  check_out: string;
}

const claiming = new Set<string>();

export async function readPendingBooking(key: string): Promise<PendingBooking | null> {
  const raw = await getDurableItem(key);
  if (raw === null) return null;
  const value: PendingBooking = JSON.parse(raw);
  if (!value || typeof value.room_id !== 'string' || !Number.isSafeInteger(value.recorded_at) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(value.check_in) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(value.check_out) || value.check_in >= value.check_out) {
    throw new Error('Invalid pending booking');
  }
  return value;
}

export async function recordPendingBooking(key: string, pending: Omit<PendingBooking, 'recorded_at'>): Promise<boolean> {
  if (claiming.has(key)) return false;
  claiming.add(key);
  let recorded = false;
  try {
    if (await readPendingBooking(key)) return false;
    await setDurableItem(key, JSON.stringify({ ...pending, recorded_at: Date.now() }));
    recorded = true;
    return true;
  } finally {
    if (!recorded) claiming.delete(key);
  }
}

export async function clearPendingBooking(key: string): Promise<void> {
  await removeDurableItem(key);
}

export function finishPendingBooking(key: string): void {
  claiming.delete(key);
}

export async function acknowledgePendingBooking(key: string, reviewed: PendingBooking): Promise<boolean> {
  if (claiming.has(key)) return false;
  claiming.add(key);
  try {
    const current = await readPendingBooking(key);
    if (JSON.stringify(current) !== JSON.stringify(reviewed)) return false;
    await clearPendingBooking(key);
    return true;
  } finally {
    claiming.delete(key);
  }
}
