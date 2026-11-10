import { acknowledgePendingBooking, finishPendingBooking, readPendingBooking, recordPendingBooking } from '../src/lib/pendingBooking';

const mockRecords = new Map<string, string>();
jest.mock('../src/lib/storage', () => ({
  getDurableItem: async (key: string) => mockRecords.get(key) ?? null,
  setDurableItem: async (key: string, value: string) => { mockRecords.set(key, value); },
  removeDurableItem: async (key: string) => { mockRecords.delete(key); },
}));

it('retains the scoped journal after a lost response and blocks another commit until reconciliation', async () => {
  const pending = { room_id: 'room-a', check_in: '2026-11-05', check_out: '2026-11-06' };
  await expect(Promise.all([recordPendingBooking('A', pending), recordPendingBooking('A', pending)])).resolves.toEqual([true, false]);
  const stored = (await readPendingBooking('A'))!;
  expect(stored).toMatchObject(pending);
  await expect(readPendingBooking('B')).resolves.toBeNull();
  await expect(acknowledgePendingBooking('A', stored)).resolves.toBe(false);
  finishPendingBooking('A');
  await expect(recordPendingBooking('A', pending)).resolves.toBe(false);
  await expect(acknowledgePendingBooking('A', { ...stored, recorded_at: stored.recorded_at - 1 })).resolves.toBe(false);
  await expect(acknowledgePendingBooking('A', stored)).resolves.toBe(true);
  await expect(readPendingBooking('A')).resolves.toBeNull();
});
