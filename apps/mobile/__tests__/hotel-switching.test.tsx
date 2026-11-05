import React from 'react';
import { Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';

function BoundHotelPanel() {
  const { user, hotel, signIn, switchHotel } = useSession();
  const [result, setResult] = React.useState('not-attempted');
  return <>
    <Text testID="selected">{hotel?.id ?? 'none'}</Text>
    <Text testID="role">{user?.role ?? 'none'}</Text>
    <Text testID="result">{result}</Text>
    <Pressable testID="login" onPress={() => { void signIn('owner', 'demo'); }}><Text>Login</Text></Pressable>
    <Pressable testID="switch" onPress={() => {
      void switchHotel('demo-sunrise-bishkek').then(
        () => setResult('unexpected-success'),
        () => setResult('denied'),
      );
    }}><Text>Switch</Text></Pressable>
  </>;
}

it('one bound hotel: cross-hotel switch is denied without dropping current employee', async () => {
  const screen = render(<SessionProvider initialLocale="ru" initialHotelId="demo-marina-issykkul"><BoundHotelPanel/></SessionProvider>);
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(() => expect(screen.getByTestId('role').props.children).toBe('OWNER'));
  fireEvent.press(screen.getByTestId('switch'));
  await waitFor(() => expect(screen.getByTestId('result').props.children).toBe('denied'));
  expect(screen.getByTestId('selected').props.children).toBe('demo-marina-issykkul');
  expect(screen.getByTestId('role').props.children).toBe('OWNER');
});
