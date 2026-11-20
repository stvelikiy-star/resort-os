import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { hotelConnectionId } from '../src/api/hotels';
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

test('accepts an approved live DNS hostname in the durable key', async () => {
  const hotelId = hotelConnectionId('https://mobile.rc430.example.com/core');
  await beginPendingDiningWrite(hotelId, USER, 'PRODUCTION_TARGET');
  expect(set).toHaveBeenCalledWith('marina.dining.pending.' + hotelId + '.' + USER,
    expect.stringContaining('"operation":"PRODUCTION_TARGET"'));
});

test('persists the non-secret journal in browser storage without native SecureStore', async () => {
  const previousOS = Platform.OS;
  const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  const entries = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: (key: string) => entries.get(key) ?? null,
    setItem: (key: string, value: string) => entries.set(key, value),
    removeItem: (key: string) => entries.delete(key),
  } });
  try {
    Platform.OS = 'web';
    const hotelId = hotelConnectionId('https://mobile.rc430.example.com/core');
    await beginPendingDiningWrite(hotelId, USER, 'PRODUCTION_TARGET');
    await expect(readPendingDiningWrite(hotelId, USER)).resolves.toMatchObject({ operation: 'PRODUCTION_TARGET' });
    await clearPendingDiningWrite(hotelId, USER);
    await expect(readPendingDiningWrite(hotelId, USER)).resolves.toBeNull();
    expect(get).not.toHaveBeenCalled();
    expect(set).not.toHaveBeenCalled();
    expect(del).not.toHaveBeenCalled();
  } finally {
    Platform.OS = previousOS;
    if (previousStorage) Object.defineProperty(globalThis, 'localStorage', previousStorage);
    else Reflect.deleteProperty(globalThis, 'localStorage');
  }
});
