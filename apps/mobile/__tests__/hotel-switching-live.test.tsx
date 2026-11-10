import React from 'react';
import { AppState, Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import { ApiError, AuthUser, StaffApi } from '../src/api/types';
import { DEMO_HOTELS } from '../src/api/hotels';
import type { HotelConnection } from '../src/api/hotels';

const hotelA: HotelConnection = {id:'live-hotel-a.example',name:'Hotel A',city:'',baseUrl:'https://hotel-a.example',demo:false,accent:'#245E9A'};
const hotelB: HotelConnection = {id:'live-hotel-b.example',name:'Hotel B',city:'',baseUrl:'https://hotel-b.example',demo:false,accent:'#245E9A'};
const identity = (key: 'A' | 'B'): AuthUser => ({
  id:'staff-'+key,username:'owner',display_name:'Owner '+key,role:'OWNER',
  property_code:'HOTEL_'+key,
  property_id:key==='A'?'11111111-1111-4111-8111-111111111111':'22222222-2222-4222-8222-222222222222',
  tenant_id:key==='A'?'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa':'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  module_permissions:['FINANCE','OPS','PMS'],
});
const mockClients: Record<string, StaffApi> = {};
const mockEvents: string[] = [];
function fakeApi(key: 'A' | 'B'): StaffApi {
  let signed = false;
  return {
    mode:'LIVE',
    authMode:async()=> 'single_property' as const,
    login:async()=>{signed=true; mockEvents.push('login-'+key);return identity(key);},
    logout:async()=>{signed=false;mockEvents.push('logout-'+key);},
    me:async()=>{
      mockEvents.push('me-'+key);
      if(!signed)throw new ApiError('UNAUTHORIZED');
      return identity(key);
    },
    listTasks:async()=>[],claimTask:async()=>{throw new ApiError('FORBIDDEN');},
    setTaskStatus:async()=>{throw new ApiError('FORBIDDEN');},
    completeHousekeeping:async()=>{throw new ApiError('FORBIDDEN');},
    createMaintenance:async()=>{throw new ApiError('FORBIDDEN');},
    listRooms:async()=>[{id:'room-'+key,code:key+'-101',floor:1,state:'CLEAN'}],
    setRoomState:async()=>{throw new ApiError('FORBIDDEN');},
    listStaff:async()=>[],assignTask:async()=>{throw new ApiError('FORBIDDEN');},
    daySummary:async()=>({occupancy_pct:0,dirty:0,blocked:0,overdue:0}),
  };
}
jest.mock('../src/api/factory',()=>({
  apiFor:(h:HotelConnection)=>mockClients[h.id],
  dropApi:jest.fn(),
}));
jest.mock('../src/api/realApi',()=>({createRealApi:()=>({logout:async()=>undefined})}));
jest.mock('../src/lib/pendingLogout',()=>({
  flushPendingCookieLogouts:jest.fn(async()=>{}),
  hasUnrevokedCookieForHost:jest.fn(async()=>false),
  queueCookieLogout:jest.fn(async()=>{}),
}));
jest.mock('../src/lib/storage',()=>({getItem:jest.fn(async()=>null),setItem:jest.fn(async()=>{})}));
let appStateSpy: jest.SpyInstance;
const previousTrust=process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
beforeAll(()=>{
  appStateSpy=jest.spyOn(AppState,'addEventListener').mockImplementation(() => ({remove:()=>{}}));
});
afterAll(()=>{
  appStateSpy.mockRestore();
  if(previousTrust===undefined)delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS=previousTrust;
});
beforeEach(()=>{
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS='https://hotel-a.example,https://hotel-b.example';
  mockClients[hotelA.id]=fakeApi('A');mockClients[hotelB.id]=fakeApi('B');mockEvents.length=0;
});
function ViewPanel(){
  const {hotel,user,addHotel,signIn,switchHotel,selectHotel,startDemo,api}=useSession();
  const [result,setResult]=React.useState('none');
  const [room,setRoom]=React.useState('none');
  return <>
    <Text testID="hotel">{hotel?.id??'none'}</Text>
    <Text testID="owner">{user?.property_code??'none'}</Text>
    <Text testID="result">{result}</Text>
    <Text testID="room">{room}</Text>
    <Pressable testID="add-a" onPress={()=>addHotel(hotelA)}><Text>Bind A</Text></Pressable>
    <Pressable testID="login" onPress={()=>{void signIn('owner','testpass');}}><Text>Sign in</Text></Pressable>
    <Pressable testID="add-b" onPress={()=>{
      try { addHotel(hotelB); setResult('unexpected-add'); }
      catch { setResult('add-denied'); }
    }}><Text>Bind B</Text></Pressable>
    <Pressable testID="switch-b" onPress={()=>{
      void switchHotel(hotelB.id).then(()=>setResult('unexpected-switch'),()=>setResult('switch-denied'));
    }}><Text>Switch B</Text></Pressable>
    <Pressable testID="read" onPress={()=>{void api?.listRooms().then(v=>setRoom(v[0]?.code??'none'));}}><Text>Read</Text></Pressable>
    <Pressable testID="select-demo" onPress={()=>{selectHotel(DEMO_HOTELS[0].id);setResult("selected-demo-attempt");}}><Text>Select demo</Text></Pressable>
    <Pressable testID="start-demo" onPress={()=>{void startDemo("owner").then(()=>setResult("unexpected-demo"),()=>setResult("demo-denied"));}}><Text>Start demo</Text></Pressable>
    <Pressable testID="switch-demo" onPress={()=>{void switchHotel(DEMO_HOTELS[0].id).then(()=>setResult("unexpected-switch-demo"),()=>setResult("switch-demo-denied"));}}><Text>Switch to demo</Text></Pressable>
  </>;
}
it('LIVE device binds one origin and refuses a second hotel without losing session A',async()=>{
  const screen=await render(<SessionProvider initialLocale="ru"><ViewPanel/></SessionProvider>);
  fireEvent.press(screen.getByTestId('add-a'));
  await waitFor(()=>expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id));
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A'));
  fireEvent.press(screen.getByTestId('add-b'));
  await waitFor(()=>expect(screen.getByTestId('result').props.children).toBe('add-denied'));
  fireEvent.press(screen.getByTestId('switch-b'));
  await waitFor(()=>expect(screen.getByTestId('result').props.children).toBe('switch-denied'));
  expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id);
  expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A');
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(()=>expect(screen.getByTestId('room').props.children).toBe('A-101'));
  expect(mockEvents).not.toContain('login-B');
});


it('provisioned customer rejects direct DEMO selection and showroom launch without revoking LIVE user',async()=>{
  const screen=await render(<SessionProvider initialLocale="ru"><ViewPanel/></SessionProvider>);
  fireEvent.press(screen.getByTestId('add-a'));
  await waitFor(()=>expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id));
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A'));
  // LIVE sign-in deliberately revokes a stale host cookie once before login.
  // Only additional revocations caused by forbidden DEMO entry would be a defect.
  const logoutCountAtLogin = mockEvents.filter(x=>x==='logout-A').length;
  fireEvent.press(screen.getByTestId('select-demo'));
  await waitFor(()=>expect(screen.getByTestId('result').props.children).toBe('selected-demo-attempt'));
  expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id);
  expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A');
  fireEvent.press(screen.getByTestId('start-demo'));
  await waitFor(()=>expect(screen.getByTestId('result').props.children).toBe('demo-denied'));
  expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id);
  expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A');
  fireEvent.press(screen.getByTestId('switch-demo'));
  await waitFor(()=>expect(screen.getByTestId('result').props.children).toBe('switch-demo-denied'));
  expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id);
  expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A');
  expect(mockEvents.filter(x=>x==='logout-A')).toHaveLength(logoutCountAtLogin);
});
