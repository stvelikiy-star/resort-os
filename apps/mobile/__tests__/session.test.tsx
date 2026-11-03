import React from 'react';
import { Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import type { AuthUser } from '../src/api/types';

// Offline logout must not block clearing the locally visible employee session.
jest.mock('../src/api/factory', () => ({
  apiFor: () => ({
    mode: 'LIVE',
    logout: async () => { throw new Error('network disconnected'); },
    me: async () => { throw new Error('network disconnected'); },
  }),
  dropApi: jest.fn(),
}));

const account: AuthUser = {
  id: 'staff-1', username: 'maid', display_name: 'Demo maid', role: 'MAID',
  property_code: 'MARINA_HOTEL01', module_permissions: ['OPS'],
};

function Probe() {
  const { user, signOut } = useSession();
  return (
    <>
      <Text testID="session-state">{user ? 'signed-in' : 'signed-out'}</Text>
      <Pressable testID="logout" onPress={() => { void signOut(); }}>
        <Text>Log out</Text>
      </Pressable>
    </>
  );
}

it('clears live employee data locally even when server logout fails', async () => {
  const screen = await render(
    <SessionProvider initialLocale="ru" initialHotelId="demo-marina-issykkul" initialUser={account}>
      <Probe />
    </SessionProvider>,
  );
  expect(screen.getByTestId('session-state').props.children).toBe('signed-in');
  fireEvent.press(screen.getByTestId('logout'));
  await waitFor(() => expect(screen.getByTestId('session-state').props.children).toBe('signed-out'));
});

function ConnectionProbe() {
  const { hotels, addHotel } = useSession();
  const add = (baseUrl: string) => addHotel({
    id: baseUrl.endsWith('/core') ? 'live-hotel.example-core' : 'live-hotel.example',
    name: 'Hotel', city: '', baseUrl, accent: '#245E9A', demo: false,
  });
  return (
    <>
      <Text testID="connected-origins">{hotels.filter((h) => !h.demo).map((h) => h.baseUrl).join('|')}</Text>
      <Pressable testID="add-root" onPress={() => add('https://hotel.example')}><Text>Root</Text></Pressable>
      <Pressable testID="add-core" onPress={() => add('https://hotel.example/core')}><Text>Core</Text></Pressable>
    </>
  );
}

it('replaces a same-host root API connection with /core instead of presenting shared cookies as isolated hotels', async () => {
  const screen = await render(
    <SessionProvider initialLocale="ru"><ConnectionProbe /></SessionProvider>,
  );
  fireEvent.press(screen.getByTestId('add-root'));
  await waitFor(() => expect(screen.getByTestId('connected-origins').props.children).toBe('https://hotel.example'));
  fireEvent.press(screen.getByTestId('add-core'));
  await waitFor(() => expect(screen.getByTestId('connected-origins').props.children).toBe('https://hotel.example/core'));
});
