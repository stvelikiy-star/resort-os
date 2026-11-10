import * as SecureStore from 'expo-secure-store';
import { beginPendingDiningWrite, clearPendingDiningWrite, readPendingDiningWrite } from '../src/lib/durableDiningWrites';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(), setItemAsync: jest.fn(), deleteItemAsync: jest.fn(),
}));

const get = jest.mocked(SecureStore.getItemAsync);
const set = jest.mocked(SecureStore.setItemAsync);
const del = jest.mocked(SecureStore.deleteItemAsync);
const HOTEL = '11111111-1111-4111-8111-111111111111';
const USER = '22222222-2222-4222-8222-222222222222';

beforeEach(() => {
  jest.clearAllMocks();
  get.mockResolvedValue(null);
  set.mockResolvedValue(undefined);
  del.mockResolvedValue(undefined);
});

test('records a hotel/operator scoped pending waiter write before the network mutation', async () => {
  await beginPendingDiningWrite(HOTEL, USER, 'CREATE_ORDER');
  expect(set).toHaveBeenCalledWith('marina.dining.pending.' + HOTEL + '.' + USER,
    expect.stringContaining('"operation":"CREATE_ORDER"'));
});

test('rejects a second mutation when a previous write is pending', async () => {
  get.mockResolvedValue(JSON.stringify({ operation: 'CREATE_TABLE', startedAt: new Date().toISOString() }));
  await expect(beginPendingDiningWrite(HOTEL, USER, 'CREATE_MENU_DRAFT')).rejects.toThrow(/reconciliation/);
  expect(set).not.toHaveBeenCalled();
});

test('storage-read failure rejects instead of permitting a duplicate', async () => {
  get.mockRejectedValue(new Error('storage unavailable'));
  await expect(beginPendingDiningWrite(HOTEL, USER, 'CREATE_ORDER')).rejects.toThrow(/storage unavailable/);
  expect(set).not.toHaveBeenCalled();
});

test('a malformed journal fails closed', async () => {
  get.mockResolvedValue('invalid-json');
  await expect(readPendingDiningWrite(HOTEL, USER)).rejects.toThrow();
});

test('clears journal only when caller explicitly confirms write outcome', async () => {
  await clearPendingDiningWrite(HOTEL, USER);
  expect(del).toHaveBeenCalledWith('marina.dining.pending.' + HOTEL + '.' + USER);
});

test('rejects untrusted hotel or user key', async () => {
  await expect(beginPendingDiningWrite('../hotel', USER, 'CREATE_ORDER')).rejects.toThrow(/identity/);
  expect(set).not.toHaveBeenCalled();
});
