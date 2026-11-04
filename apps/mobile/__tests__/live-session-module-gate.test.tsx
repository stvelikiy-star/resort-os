import React from 'react';
import { Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { useLiveModules } from '../src/api/liveModules';
import type { HotelConnection } from '../src/api/hotels';
import type { AuthUser } from '../src/api/types';

const mockSession: { hotel: HotelConnection | null; user: AuthUser | null; api: { mode: 'LIVE' } | null } = {
  hotel: null, user: null, api: null,
};
jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));

function GateProbe() {
  const modules = useLiveModules();
  return <Text testID="live-modules">{modules ? 'VERIFIED' : 'BLOCKED'}</Text>;
}

const hotel: HotelConnection = {
  id: 'live-platform.example', name: 'MARINA SMART',
  city: '', baseUrl: 'https://platform.example', demo: false, accent: '#245E9A',
};
const userA: AuthUser = {
  id: 'staff-a', username: 'a', display_name: 'Manager A', role: 'MANAGER',
  property_code: 'HOTEL_A', property_id: '11111111-1111-4111-8111-111111111111',
  tenant_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', module_permissions: ['PMS'],
};
const userB: AuthUser = {
  ...userA, id: 'staff-b', property_code: 'HOTEL_B',
  property_id: '22222222-2222-4222-8222-222222222222',
  tenant_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
};
const priorTrust = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
beforeEach(() => {
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://platform.example';
  mockSession.hotel = null; mockSession.user = null; mockSession.api = null;
});
afterAll(() => {
  if (priorTrust === undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = priorTrust;
});

it('blocks operations even on a trusted shared host until /auth/me verifies the user', async () => {
  mockSession.hotel = hotel;
  mockSession.api = { mode: 'LIVE' };
  const screen = await render(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('BLOCKED');
  mockSession.user = userA;
  screen.rerender(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('VERIFIED');
});

it('drops module access immediately during a switch from hotel A to B on the same host', async () => {
  mockSession.hotel = hotel;
  mockSession.api = { mode: 'LIVE' };
  mockSession.user = userA;
  const screen = await render(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('VERIFIED');

  // The OS cookie might still belong to A. Selection alone is not authority.
  mockSession.user = null;
  screen.rerender(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('BLOCKED');

  mockSession.user = userB; // only after verified B login + /me
  screen.rerender(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('VERIFIED');
  mockSession.api = null; // explicit sign-out / disconnect
  screen.rerender(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('BLOCKED');
});

it('never exposes LIVE modules for an unapproved origin, even with a user object', async () => {
  mockSession.user = userA;
  mockSession.api = { mode: 'LIVE' };
  mockSession.hotel = { ...hotel, baseUrl: 'https://impostor.example' };
  const screen = await render(<GateProbe />);
  expect(screen.getByTestId('live-modules').props.children).toBe('BLOCKED');
});
