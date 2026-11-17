/// <reference types="node" />
/**
 * Isolated P0: REAL React Native STORE_STAFF screen, REAL authenticated Core,
 * and ONE disposable PostgreSQL instance.
 * Opt-in only; never calls a remote hotel or production.
 *
 * This is screen-component E2E in Jest, NOT a physical Android/Expo Go E2E.
 */
import React from 'react';
import { request as nodeHttpRequest } from 'node:http';
import { Alert } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import StoreWorkspace from '../app/(app)/store';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { AuthUser } from '../src/api/types';
import type { createLiveModules } from '../src/api/liveModules';

const API_ORIGIN = 'https://marina-ci.example';
const mockStorage = new Map<string, string>();
type LiveApi = ReturnType<typeof createLiveModules>;
let mockLive: LiveApi | null = null;
let mockUser: AuthUser | null = null;
const mockSession = {
  get user() { return mockUser; },
  hotel: { id: 'marina-disposable-test-hotel', name: 'Disposable CI', demo: false },
  api: { mode: 'LIVE' as const },
  locale: 'en' as const,
  serverAuthMode: 'single_property' as const,
};

jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));
jest.mock('../src/api/liveModules', () => ({
  ...jest.requireActual('../src/api/liveModules'),
  useLiveModules: () => mockLive,
}));
jest.mock('../src/lib/storage', () => ({
  getDurableItem: async (key: string) => mockStorage.get(key) ?? null,
  setDurableItem: async (key: string, value: string) => { mockStorage.set(key, value); },
  removeDurableItem: async (key: string) => { mockStorage.delete(key); },
}));
jest.mock('../src/components/KitchenProcurement', () => ({ KitchenProcurement: () => null }));
jest.mock('../src/components/KitchenLosses', () => ({ KitchenLosses: () => null }));
jest.mock('expo-router', () => ({ useFocusEffect: jest.fn() }));
jest.mock('react-native-safe-area-context', () => ({
  useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }),
}));

interface HttpSession {
  me: AuthUser;
  live: LiveApi;
  request(path: string, method?: string, payload?: unknown): Promise<{ status: number; data: any }>;
}
function localCore(): string {
  const base = process.env.CORE_API_URL ?? '';
  const db = new URL(process.env.DATABASE_URL ?? 'http://missing.invalid');
  if (process.env.RUN_MARINA_REAL_SCREEN_E2E !== '1' ||
      base !== 'http://127.0.0.1:8000' ||
      !['localhost', '127.0.0.1'].includes(db.hostname)) {
    throw new Error('Refusing non-disposable Core/PostgreSQL or missing explicit opt-in');
  }
  return base;
}
// Jest/React Native replaces global fetch. Use Node's actual loopback HTTP
// client so a mocked network can NEVER produce a false-positive PASS.
async function localFetch(address: string, init: RequestInit = {}): Promise<{
  status: number; ok: boolean; headers: { get: (key: string) => string | null };
  json: () => Promise<any>;
}> {
  const u = new URL(address);
  if (u.protocol !== 'http:' || u.hostname !== '127.0.0.1' || u.port !== '8000') {
    throw new Error('Blocked non-loopback screen E2E network target');
  }
  const rawHeaders = init.headers instanceof Headers
    ? Object.fromEntries(init.headers.entries())
    : (init.headers as Record<string, string> | undefined) ?? {};
  return await new Promise((resolve, reject) => {
    const req = nodeHttpRequest({
      protocol: u.protocol, hostname: u.hostname, port: u.port,
      path: u.pathname + u.search, method: init.method ?? 'GET',
      headers: rawHeaders, timeout: 16000,
    }, res => {
      const chunks: Buffer[] = [];
      res.on('data', (chunk: Buffer) => chunks.push(chunk));
      res.on('error', reject);
      res.on('end', () => {
        const text = Buffer.concat(chunks).toString('utf8');
        const cookies = res.headers['set-cookie'];
        const cookieHeader = Array.isArray(cookies) ? cookies.join(', ') : cookies ?? '';
        const status = res.statusCode ?? 0;
        resolve({
          status, ok: status >= 200 && status < 300,
          headers: { get: (key: string) => key.toLowerCase() === 'set-cookie' ? cookieHeader : String(res.headers[key.toLowerCase()] ?? '') },
          json: async () => text ? JSON.parse(text) : null,
        });
      });
    });
    req.on('timeout', () => req.destroy(new Error('Local test request timeout')));
    req.on('error', reject);
    if (init.body !== undefined && init.body !== null) req.write(String(init.body));
    req.end();
  });
}

async function login(usernameEnv: string, passwordEnv: string): Promise<HttpSession> {
  const base = localCore();
  const username = process.env[usernameEnv];
  const password = process.env[passwordEnv];
  if (!username || !password) throw new Error('Missing synthetic CI credential: ' + usernameEnv);
  const signed = await localFetch(base + '/api/v1/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }), redirect: 'error',
  });
  if (signed.status !== 200) throw new Error('Synthetic role login refused: ' + usernameEnv + ' / ' + signed.status);
  const cookie = signed.headers.get('set-cookie')?.match(/(?:^|,\s*)(resort_session=[^;,]+)/)?.[1];
  if (!cookie) throw new Error('Synthetic role authentication issued no session cookie');
  const request = async (path: string, method = 'GET', payload?: unknown) => {
    if (!path.startsWith('/api/v1/') || path.includes('..')) throw new Error('Unsafe local path');
    const res = await localFetch(base + path, {
      method, headers: { Cookie: cookie, Accept: 'application/json',
        ...(payload === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      redirect: 'error',
    });
    return { status: res.status, data: res.status === 204 ? null : await res.json() };
  };
  const self = await request('/api/v1/auth/me');
  if (self.status !== 200 || !self.data?.id || !self.data?.role) throw new Error('Unable to verify synthetic actor');
  // This adapter changes only the CI transport address; no customer host or
  // production trust list is touched. Response URL remains intentionally empty.
  const transport: typeof fetch = async (input, init) => {
    const address = String(input);
    if (!address.startsWith(API_ORIGIN + '/api/v1/')) throw new Error('Unexpected transport origin');
    const suffix = address.slice(API_ORIGIN.length);
    const headers = new Headers(init?.headers);
    headers.set('Cookie', cookie);
    const res = await localFetch(base + suffix, { ...init, headers, redirect: 'error' });
    return { ok: res.ok, status: res.status, redirected: false, url: '',
      json: () => res.json() } as Response;
  };
  const { createLiveModules: realLiveModules } =
    jest.requireActual('../src/api/liveModules') as typeof import('../src/api/liveModules');
  return { me: self.data as AuthUser,
    live: realLiveModules(API_ORIGIN, transport, 'single_property'), request };
}

const liveOnly = process.env.RUN_MARINA_REAL_SCREEN_E2E === '1' ? test : test.skip;

liveOnly('STORE_STAFF screen commits one PostgreSQL receipt, OWNER sees it, WAITER denied and replay is safe', async () => {
  mockStorage.clear();
  jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
  try {
    const owner = await login('BOOTSTRAP_OWNER_USERNAME', 'BOOTSTRAP_OWNER_PASSWORD');
    const store = await login('PROC_STORE_USERNAME', 'PROC_STORE_PASSWORD');
    const waiter = await login('WAITER_SERVE_E2E_USERNAME', 'WAITER_SERVE_E2E_PASSWORD');
    expect(owner.me.role).toBe('OWNER');
    expect(store.me.role).toBe('STORE_STAFF');
    expect(waiter.me.role).toBe('WAITER');
    expect(store.me.property_code).toBe(owner.me.property_code);
    expect(waiter.me.property_code).toBe(owner.me.property_code);
    expect(store.me.module_permissions).toContain('DINING');

    const name = 'MARINA-LIVE-STORE-SCREEN-' + Date.now();
    const created = await owner.request('/api/v1/kitchen/stock/items', 'POST', {
      name, unit: 'KG', cost_per_unit_kgs: '2.5', is_sample: false,
    });
    expect(created.status).toBe(201);
    const itemId = created.data.id as string;
    const balanceBefore = (await owner.live.kitchenStock()).items.find(x => x.id === itemId);
    expect(balanceBefore).toBeDefined();

    // Only the real StoreWorkspace screen can trigger this write in the test.
    const submissions: unknown[] = [];
    const originalTransport = store.live.receiveKitchenStock;
    store.live.receiveKitchenStock = async (body) => {
      submissions.push(body);
      return originalTransport(body);
    };
    mockLive = store.live; mockUser = store.me;
    const view = await render(<ThemeProvider initial="light"><StoreWorkspace /></ThemeProvider>);
    await waitFor(() => expect(view.getByText(name + ' (KG)')).toBeTruthy());
    fireEvent.press(view.getByText(name + ' (KG)'));
    fireEvent.changeText(view.getByLabelText('Quantity'), '3');
    await waitFor(() => expect(view.getByTestId('stock-receipt-save')).toBeEnabled());
    fireEvent.press(view.getByTestId('stock-receipt-save'));
    const buttons = jest.mocked(Alert.alert).mock.calls.at(-1)?.[2];
    const confirm = buttons?.find(x => x.style !== 'cancel')?.onPress;
    expect(confirm).toBeDefined();
    await act(async () => { await confirm?.(); });
    await waitFor(() => expect(submissions).toHaveLength(1), { timeout: 15000 });
    await waitFor(() => expect(view.queryByTestId('stock-receipt-pending')).toBeNull());
    await view.unmount();

    const recorded = submissions[0] as { movement_id: string; quantity: string; stock_item_id: string };
    expect(recorded.stock_item_id).toBe(itemId);
    expect(Number(recorded.quantity)).toBe(3);
    const balanceAfter = (await owner.live.kitchenStock()).items.find(x => x.id === itemId);
    expect(balanceAfter).toBeDefined();
    expect(Number(balanceAfter!.balance) - Number(balanceBefore!.balance)).toBeCloseTo(3, 6);

    const repeated = await store.request('/api/v1/kitchen/stock/receipts', 'POST', recorded);
    expect(repeated.status).toBe(201);
    expect(repeated.data.already_processed).toBe(true);
    const changed = await store.request('/api/v1/kitchen/stock/receipts', 'POST',
      { ...recorded, quantity: '4' });
    expect(changed.status).toBe(409);
    const denied = await waiter.request('/api/v1/kitchen/stock/receipts', 'POST', recorded);
    expect(denied.status).toBe(403);
    const finalItem = (await owner.live.kitchenStock()).items.find(x => x.id === itemId);
    expect(Number(finalItem!.balance)).toBeCloseTo(Number(balanceAfter!.balance), 6);

    const managerOnly = await waiter.request('/api/v1/admin/finance/owner/kitchen-operations');
    expect(managerOnly.status).toBe(403);
    const ownerFinance = await owner.request('/api/v1/admin/finance/owner/kitchen-operations');
    expect(ownerFinance.status).toBe(200);
    console.log('MARINA_P0_SCREEN_DB_E2E_PASS: store=committed, owner=readback, waiter=403, replay=idempotent, conflict=409');
  } finally {
    jest.restoreAllMocks(); mockLive = null; mockUser = null; mockStorage.clear();
  }
}, 120_000);
