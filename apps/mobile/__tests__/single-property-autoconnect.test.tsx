import React from 'react';
import { Text } from 'react-native';
import { render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import { getItem } from '../src/lib/storage';

jest.mock('../src/lib/storage', () => ({ getItem: jest.fn(async () => null), setItem: jest.fn(async () => {}) }));

function Probe() {
  const { hotel, hotels } = useSession();
  return <>
    <Text testID="hotel">{hotel?.baseUrl ?? 'NOT_SELECTED'}</Text>
    <Text testID="live-count">{hotels.filter(h => !h.demo).length}</Text>
  </>;
}

const aska = 'https://leeds-biology-charming-employ.trycloudflare.com/core';
const previous = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
afterEach(() => {
  if (previous === undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = previous;
  jest.clearAllMocks();
});

it('starts directly at the single pinned live hotel instead of demo/chooser', async () => {
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = aska;
  const screen = await render(<SessionProvider initialLocale="ru"><Probe /></SessionProvider>);
  expect(screen.getByTestId('hotel').props.children).toBe(aska);
  expect(String(screen.getByTestId('live-count').props.children)).toBe('1');
});

it('retains the pinned hotel after stale saved preferences are rehydrated', async () => {
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = aska;
  (getItem as jest.Mock).mockImplementation(async (key: string) =>
    key === 'marina.hotels' ? JSON.stringify([{baseUrl:aska,demo:false},{baseUrl:'https://evil.example/core',demo:false}]) : null);
  const screen = await render(<SessionProvider><Probe /></SessionProvider>);
  await waitFor(() => expect(screen.getByTestId('hotel').props.children).toBe(aska));
  await waitFor(() => expect(String(screen.getByTestId('live-count').props.children)).toBe('1'));
});
