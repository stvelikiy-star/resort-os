import React from 'react';
import { Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import { ApiError } from '../src/api/types';
import type { AuthUser } from '../src/api/types';

const events: string[] = [];
let revokeFails = false;
const account: AuthUser = {
  id:'staff-user-1', username:'manager', display_name:'Hotel manager', role:'MANAGER',
  property_code:'HOTEL_A', module_permissions:['OPS','STAFF'],
};
const mockApi = {
  mode: 'LIVE' as const,
  authMode: async () => 'single_property' as const,
  logout: async () => {
    events.push('logout');
    if (revokeFails) throw new ApiError('OFFLINE', 'No server acknowledgement');
  },
  login: async () => { events.push('login'); return account; },
  me: async () => { events.push('me'); return account; },
};
jest.mock('../src/api/factory', () => ({
  apiFor: () => mockApi,
  dropApi: jest.fn(),
}));
jest.mock('../src/api/realApi', () => ({
  createRealApi: () => mockApi,
}));
jest.mock('../src/lib/pendingLogout', () => ({
  flushPendingCookieLogouts: jest.fn(async () => {}),
  hasUnrevokedCookieForHost: jest.fn(async () => false),
  queueCookieLogout: jest.fn(async () => {}),
}));

function Probe() {
  const { hotel, user, addHotel, signIn } = useSession();
  const [error, setError] = React.useState('');
  return <>
    <Text testID="selected-hotel">{hotel?.baseUrl ?? 'none'}</Text>
    <Text testID="login-state">{user?.id ?? 'anonymous'}</Text>
    <Text testID="login-error">{error}</Text>
    <Pressable testID="add-hotel" onPress={() => addHotel({
      id:'live-hotel.example',name:'Hotel A',city:'',baseUrl:'https://hotel.example',
      demo:false,accent:'#245E9A',
    })}><Text>Add</Text></Pressable>
    <Pressable testID="login" onPress={() => {
      void signIn('manager','password').catch((e: unknown) => {
        setError(e instanceof ApiError ? e.code : 'OTHER');
      });
    }}><Text>Login</Text></Pressable>
  </>;
}

const priorTrust=process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
beforeEach(()=>{events.length=0;revokeFails=false;process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS='https://hotel.example';});
afterAll(()=>{if(priorTrust===undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS=priorTrust;});

async function connect() {
  const screen=await render(<SessionProvider initialLocale="ru"><Probe /></SessionProvider>);
  fireEvent.press(screen.getByTestId('add-hotel'));
  await waitFor(()=>expect(screen.getByTestId('selected-hotel').props.children).toBe('https://hotel.example'));
  return screen;
}

it('revoke any stale host cookie before sending new live credentials', async()=>{
  const screen=await connect();
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('login-state').props.children).toBe('staff-user-1'));
  expect(events.slice(0,3)).toEqual(['logout','login','me']);
  await screen.unmount();
});

it('blocks sending login credentials if stale-cookie revocation cannot be confirmed',async()=>{
  revokeFails=true;
  const screen=await connect();
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('login-error').props.children).toBe('PENDING_LOGOUT'));
  expect(events).toEqual(['logout']);
  expect(screen.getByTestId('login-state').props.children).toBe('anonymous');
  await screen.unmount();
});
