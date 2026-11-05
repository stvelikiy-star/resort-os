import React from 'react';
import { Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';

/**
 * Hotel A and B have distinct fixture stores. Returning to A must not log in
 * again or return B's tasks/rooms. LIVE shared-host property switching is
 * intentionally excluded: a native host cookie is NOT a per-property token.
 */
function HotelPanel() {
  const { user, hotel, api, signIn, switchHotel } = useSession();
  const [rooms, setRooms] = React.useState('');
  const [restored, setRestored] = React.useState('none');
  const change = async (id: string) => {
    setRooms('');
    const retained = await switchHotel(id);
    setRestored(retained ? 'yes' : 'no');
  };
  return <>
    <Text testID="selected">{hotel?.id ?? 'none'}</Text>
    <Text testID="role">{user?.role ?? 'none'}</Text>
    <Text testID="rooms">{rooms}</Text>
    <Text testID="restored">{restored}</Text>
    <Pressable testID="login-owner" onPress={() => { void signIn('owner', 'demo'); }}><Text>Login owner</Text></Pressable>
    <Pressable testID="login-manager" onPress={() => { void signIn('manager', 'demo'); }}><Text>Login manager</Text></Pressable>
    <Pressable testID="a" onPress={() => { void change('demo-marina-issykkul'); }}><Text>A</Text></Pressable>
    <Pressable testID="b" onPress={() => { void change('demo-sunrise-bishkek'); }}><Text>B</Text></Pressable>
    <Pressable testID="read" onPress={() => {
      if (!api || !user) return;
      void api.listRooms().then(rows => setRooms(rows.map(row => row.code).join(',')));
    }}><Text>Read rooms</Text></Pressable>
  </>;
}
it('A → B → A retains A in-memory identity without re-login and never mixes hotel data', async () => {
  const screen = render(<SessionProvider initialLocale="ru" initialHotelId="demo-marina-issykkul"><HotelPanel/></SessionProvider>);
  fireEvent.press(screen.getByTestId('login-owner'));
  await waitFor(() => expect(screen.getByTestId('role').props.children).toBe('OWNER'));
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(() => expect(screen.getByTestId('rooms').props.children).toContain('M-101'));

  fireEvent.press(screen.getByTestId('b'));
  await waitFor(() => expect(screen.getByTestId('selected').props.children).toBe('demo-sunrise-bishkek'));
  expect(screen.getByTestId('role').props.children).toBe('none');
  expect(screen.getByTestId('rooms').props.children).toBe('');
  fireEvent.press(screen.getByTestId('login-manager'));
  await waitFor(() => expect(screen.getByTestId('role').props.children).toBe('MANAGER'));
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(() => expect(screen.getByTestId('rooms').props.children).toContain('S-101'));
  expect(screen.getByTestId('rooms').props.children).not.toContain('M-101');

  fireEvent.press(screen.getByTestId('a'));
  await waitFor(() => expect(screen.getByTestId('selected').props.children).toBe('demo-marina-issykkul'));
  await waitFor(() => expect(screen.getByTestId('restored').props.children).toBe('yes'));
  expect(screen.getByTestId('role').props.children).toBe('OWNER');
  expect(screen.getByTestId('rooms').props.children).toBe('');
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(() => expect(screen.getByTestId('rooms').props.children).toContain('M-101'));
  expect(screen.getByTestId('rooms').props.children).not.toContain('S-101');
});
