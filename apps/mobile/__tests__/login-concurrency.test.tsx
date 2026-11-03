import React from 'react';
import { Pressable, Text } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import type { AuthUser } from '../src/api/types';

type FakeApi = { mode: 'DEMO'; login: (name: string) => Promise<AuthUser> };
let mockApi: FakeApi;
jest.mock('../src/api/factory', () => ({
  apiFor: () => mockApi,
  dropApi: jest.fn(),
}));

const mkUser = (username: string): AuthUser => ({
  id: username, username, display_name: username, role: username === 'manager' ? 'MANAGER' : 'MAID',
  property_code: 'DEMO', module_permissions: ['*'],
});
function Probe() {
  const { user, signIn } = useSession();
  const login = (username: string) => { void signIn(username, 'demo').catch(() => {}); };
  return (
    <>
      <Text testID="logged-in-user">{user?.username ?? 'none'}</Text>
      <Pressable testID="login-maid" onPress={() => login('maid')}><Text>Maid</Text></Pressable>
      <Pressable testID="login-manager" onPress={() => login('manager')}><Text>Manager</Text></Pressable>
    </>
  );
}

it('ignores an earlier login response that arrives after the latest account', async () => {
  let releaseMaid!: (user: AuthUser) => void;
  let releaseManager!: (user: AuthUser) => void;
  mockApi = {
    mode: 'DEMO',
    login: (name) => new Promise((resolve) => {
      if (name === 'maid') releaseMaid = resolve;
      else releaseManager = resolve;
    }),
  };
  const screen = render(
    <SessionProvider initialLocale="ru" initialHotelId="demo-marina-issykkul">
      <Probe />
    </SessionProvider>,
  );
  fireEvent.press(screen.getByTestId('login-maid'));
  fireEvent.press(screen.getByTestId('login-manager'));
  await act(async () => releaseManager(mkUser('manager')));
  await waitFor(() => expect(screen.getByTestId('logged-in-user').props.children).toBe('manager'));
  await act(async () => releaseMaid(mkUser('maid')));
  expect(screen.getByTestId('logged-in-user').props.children).toBe('manager');
});
