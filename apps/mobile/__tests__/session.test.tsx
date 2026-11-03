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
  const screen = render(
    <SessionProvider initialLocale="ru" initialHotelId="demo-marina-issykkul" initialUser={account}>
      <Probe />
    </SessionProvider>,
  );
  expect(screen.getByTestId('session-state').props.children).toBe('signed-in');
  fireEvent.press(screen.getByTestId('logout'));
  await waitFor(() => expect(screen.getByTestId('session-state').props.children).toBe('signed-out'));
});
