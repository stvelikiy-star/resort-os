import * as SecureStore from 'expo-secure-store';
import { beginPendingAgentService, clearPendingAgentService, readPendingAgentService } from '../src/lib/pendingAgentService';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(), setItemAsync: jest.fn(), deleteItemAsync: jest.fn(),
}));

const get = jest.mocked(SecureStore.getItemAsync);
const set = jest.mocked(SecureStore.setItemAsync);
const del = jest.mocked(SecureStore.deleteItemAsync);
const HOTEL = '11111111-1111-4111-8111-111111111111';
const USER = '22222222-2222-4222-8222-222222222222';
const RESERVATION = '33333333-3333-4333-8333-333333333333';

beforeEach(() => {
  jest.clearAllMocks();
  get.mockResolvedValue(null);
  set.mockResolvedValue(undefined);
  del.mockResolvedValue(undefined);
});

test('records reservation and service for scoped pending mutation', async () => {
  await beginPendingAgentService(HOTEL, USER, RESERVATION, 'TRANSFER');
  expect(set).toHaveBeenCalledWith('marina.agent-service.pending.' + HOTEL + '.' + USER,
    expect.stringContaining('"reservationId":"' + RESERVATION + '"'));
  expect(set.mock.calls[0][1]).toContain('"serviceCode":"TRANSFER"');
});

test('persistent pending journal prevents repeating service after remount', async () => {
  get.mockResolvedValue(JSON.stringify({ reservationId: RESERVATION, serviceCode: 'MEALS', startedAt: new Date().toISOString() }));
  expect((await readPendingAgentService(HOTEL, USER))?.serviceCode).toBe('MEALS');
  await expect(beginPendingAgentService(HOTEL, USER, RESERVATION, 'MEALS')).rejects.toThrow(/reconciliation/);
  expect(set).not.toHaveBeenCalled();
});

test('secure storage failure fails closed', async () => {
  get.mockRejectedValue(new Error('unavailable'));
  await expect(beginPendingAgentService(HOTEL, USER, RESERVATION, 'SAUNA')).rejects.toThrow('unavailable');
  expect(set).not.toHaveBeenCalled();
});

test('malformed persisted record fails closed', async () => {
  get.mockResolvedValue('{');
  await expect(readPendingAgentService(HOTEL, USER)).rejects.toThrow();
});

test('does not accept invalid identities or reservation references', async () => {
  await expect(beginPendingAgentService('../hotel', USER, RESERVATION, 'TRANSFER')).rejects.toThrow();
  await expect(beginPendingAgentService(HOTEL, USER, 'invalid', 'TRANSFER')).rejects.toThrow();
  expect(set).not.toHaveBeenCalled();
});

test('only explicit clearing deletes persisted pending journal', async () => {
  await clearPendingAgentService(HOTEL, USER);
  expect(del).toHaveBeenCalledWith('marina.agent-service.pending.' + HOTEL + '.' + USER);
});
