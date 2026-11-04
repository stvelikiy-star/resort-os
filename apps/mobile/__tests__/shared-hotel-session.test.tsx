import React from 'react';
import { AppState, Pressable, Text } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import { ApiError } from '../src/api/types';
import type { AuthMode, AuthUser } from '../src/api/types';
import type { SharedHotelSelector } from '../src/api/sharedHotelAuth';

const PROP_A = '11111111-1111-4111-8111-111111111111';
const PROP_B = '22222222-2222-4222-8222-222222222222';
const TENANT_A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const TENANT_B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const HOTEL = { id: 'live-platform.example', name: 'Shared platform', city: '', baseUrl: 'https://platform.example', demo: false, accent: '#245E9A' };

const calls: string[] = [];
let mode: AuthMode = 'shared_auth_preview';
let cookie: AuthUser | null = null;
let meOverride: AuthUser | null = null;
let revoked = false;

const selected = (property: 'HOTEL_A' | 'HOTEL_B'): SharedHotelSelector =>
  ({ tenant_code: property === 'HOTEL_A' ? 'tenant_a' : 'tenant_b', property_code: property });
const identity = (property: 'HOTEL_A' | 'HOTEL_B'): AuthUser => ({
  id: 'staff-' + property, username: 'manager', display_name: 'Manager', role: 'MANAGER',
  property_code: property, property_id: property === 'HOTEL_A' ? PROP_A : PROP_B,
  tenant_id: property === 'HOTEL_A' ? TENANT_A : TENANT_B,
  module_permissions: ['PMS', 'OPS'],
});

const mockApi = {
  mode: 'LIVE' as const,
  authMode: async (): Promise<AuthMode> => { calls.push('mode'); return mode; },
  logout: async () => { calls.push('logout'); cookie = null; },
  login: async (_username: string, _password: string, selector?: SharedHotelSelector): Promise<AuthUser> => {
    calls.push('login:' + (selector?.property_code ?? 'legacy'));
    const property = selector?.property_code === 'HOTEL_B' ? 'HOTEL_B' : 'HOTEL_A';
    cookie = identity(property);
    return cookie;
  },
  me: async (): Promise<AuthUser> => {
    calls.push('me');
    if (revoked || !cookie) throw new ApiError('UNAUTHORIZED');
    return meOverride ?? cookie;
  },
};
jest.mock('../src/api/factory', () => ({ apiFor: () => mockApi, dropApi: jest.fn() }));
jest.mock('../src/api/realApi', () => ({ createRealApi: () => mockApi }));
jest.mock('../src/lib/pendingLogout', () => ({
  flushPendingCookieLogouts: jest.fn(async () => {}),
  hasUnrevokedCookieForHost: jest.fn(async () => false),
  queueCookieLogout: jest.fn(async () => {}),
}));

function Panel() {
  const { hotel, user, addHotel, signIn, signOut, leaveHotel } = useSession();
  const [error, setError] = React.useState('');
  const login = (selector?: SharedHotelSelector) => {
    setError('');
    void signIn('manager', 'synthetic-password', selector)
      .catch((e: unknown) => setError(e instanceof ApiError ? e.code : 'OTHER'));
  };
  return <>
    <Text testID="hotel-host">{hotel?.baseUrl ?? 'none'}</Text>
    <Text testID="selected-property">{user?.property_code ?? 'none'}</Text>
    <Text testID="selected-tenant">{user?.tenant_id ?? 'none'}</Text>
    <Text testID="error">{error}</Text>
    <Pressable testID="connect" onPress={() => addHotel(HOTEL)}><Text>Connect</Text></Pressable>
    <Pressable testID="login-a" onPress={() => login(selected('HOTEL_A'))}><Text>Login A</Text></Pressable>
    <Pressable testID="login-b" onPress={() => login(selected('HOTEL_B'))}><Text>Login B</Text></Pressable>
    <Pressable testID="login-missing" onPress={() => login()}><Text>Missing selector</Text></Pressable>
    <Pressable testID="logout" onPress={() => void signOut()}><Text>Logout</Text></Pressable>
    <Pressable testID="leave" onPress={leaveHotel}><Text>Switch hotel</Text></Pressable>
  </>;
}
const TRUST = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
// RN's test AppState stub does not always return an EventSubscription. Every
// mounted provider must receive a real remove() across the entire suite.
const appStateHandlers = new Set<(state: string) => void>();
let appStateSpy: jest.SpyInstance;
beforeAll(() => {
  appStateSpy = jest.spyOn(AppState, 'addEventListener').mockImplementation(((
    kind: string, handler: (state: string) => void,
  ) => {
    if (kind === 'change') appStateHandlers.add(handler);
    return { remove: () => appStateHandlers.delete(handler) };
  }) as typeof AppState.addEventListener);
});
beforeEach(() => {
  calls.length = 0;
  cookie = null;
  meOverride = null;
  revoked = false;
  mode = 'shared_auth_preview';
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://platform.example';
  jest.clearAllMocks();
});
afterAll(() => {
  appStateSpy.mockRestore();
  if (TRUST === undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = TRUST;
});
const setup = async () => {
  const screen = await render(<SessionProvider initialLocale="ru"><Panel /></SessionProvider>);
  fireEvent.press(screen.getByTestId('connect'));
  await waitFor(() => expect(screen.getByTestId('hotel-host').props.children).toBe('https://platform.example'));
  return screen;
};

describe('shared multi-hotel sign-in; one trusted host, unrelated owners', () => {
  it('binds A then B to different verified tenants and clears A before switching cookie', async () => {
    const screen = await setup();
    fireEvent.press(screen.getByTestId('login-a'));
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('HOTEL_A'));
    expect(screen.getByTestId('selected-tenant').props.children).toBe(TENANT_A);
    fireEvent.press(screen.getByTestId('login-b'));
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('HOTEL_B'));
    expect(screen.getByTestId('selected-tenant').props.children).toBe(TENANT_B);
    expect(calls.filter(x => x === 'logout')).toHaveLength(2);
    expect(calls).toEqual(['mode', 'logout', 'login:HOTEL_A', 'me', 'mode', 'logout', 'login:HOTEL_B', 'me']);
  });

  it('requires both shared selectors before sending any password or changing cookie', async () => {
    const screen = await setup();
    fireEvent.press(screen.getByTestId('login-missing'));
    await waitFor(() => expect(screen.getByTestId('error').props.children).toBe('BAD_REQUEST'));
    expect(calls).toEqual(['mode']);
    expect(screen.getByTestId('selected-property').props.children).toBe('none');
  });

  it('rejects server /me returning a different hotel, even with valid login HTTP 200', async () => {
    const screen = await setup();
    meOverride = { ...identity('HOTEL_A'), property_id: PROP_B };
    fireEvent.press(screen.getByTestId('login-a'));
    await waitFor(() => expect(screen.getByTestId('error').props.children).toBe('UNAUTHORIZED'));
    expect(screen.getByTestId('selected-property').props.children).toBe('none');
    const { queueCookieLogout } = jest.requireMock('../src/lib/pendingLogout');
    expect(queueCookieLogout).toHaveBeenCalledWith('https://platform.example');
  });

  it('clears revoked hotel A session on foreground and permits verified fresh login', async () => {
    const screen = await setup();
    fireEvent.press(screen.getByTestId('login-a'));
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('HOTEL_A'));
    revoked = true;
    await act(async () => { for (const handler of [...appStateHandlers]) handler('active'); });
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('none'));
    revoked = false;
    fireEvent.press(screen.getByTestId('login-b'));
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('HOTEL_B'));
  });

  it('does not expose an earlier hotel after leaving the shared connection', async () => {
    const screen = await setup();
    fireEvent.press(screen.getByTestId('login-a'));
    await waitFor(() => expect(screen.getByTestId('selected-property').props.children).toBe('HOTEL_A'));
    fireEvent.press(screen.getByTestId('leave'));
    await waitFor(() => expect(screen.getByTestId('hotel-host').props.children).toBe('none'));
    expect(screen.getByTestId('selected-property').props.children).toBe('none');
  });
});
