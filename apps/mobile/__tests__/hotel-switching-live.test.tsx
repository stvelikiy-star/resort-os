import React from 'react';
import { AppState, Pressable, Text } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { SessionProvider, useSession } from '../src/state/session';
import { ApiError, AuthUser, StaffApi } from '../src/api/types';
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
  const {hotel,user,addHotel,switchHotel,signIn,api}=useSession();
  const [room,setRoom]=React.useState('none');
  const [restored,setRestored]=React.useState('none');
  const swap=async(id:string)=>{
    setRoom('none');const r=await switchHotel(id);setRestored(r?'yes':'no');
  };
  return <>
    <Text testID="hotel">{hotel?.id??'none'}</Text>
    <Text testID="owner">{user?.property_code??'none'}</Text>
    <Text testID="room">{room}</Text>
    <Text testID="restored">{restored}</Text>
    <Pressable testID="add-a" onPress={()=>addHotel(hotelA)}><Text>Add A</Text></Pressable>
    <Pressable testID="add-b" onPress={()=>addHotel(hotelB)}><Text>Add B</Text></Pressable>
    <Pressable testID="login" onPress={()=>{void signIn('owner','testpass');}}><Text>Sign in</Text></Pressable>
    <Pressable testID="back-a" onPress={()=>{void swap(hotelA.id);}}><Text>Switch A</Text></Pressable>
    <Pressable testID="back-b" onPress={()=>{void swap(hotelB.id);}}><Text>Switch B</Text></Pressable>
    <Pressable testID="read" onPress={()=>{void api?.listRooms().then(v=>setRoom(v[0]?.code??'none'));}}><Text>Read</Text></Pressable>
  </>;
}
it('retains independent verified LIVE sessions A→B→A on two signed, different HTTPS hosts',async()=>{
  const screen=render(<SessionProvider initialLocale="ru"><ViewPanel/></SessionProvider>);
  fireEvent.press(screen.getByTestId('add-a'));
  await waitFor(()=>expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id));
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A'));
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(()=>expect(screen.getByTestId('room').props.children).toBe('A-101'));

  fireEvent.press(screen.getByTestId('add-b'));
  await waitFor(()=>expect(screen.getByTestId('hotel').props.children).toBe(hotelB.id));
  expect(screen.getByTestId('owner').props.children).toBe('none');
  fireEvent.press(screen.getByTestId('login'));
  await waitFor(()=>expect(screen.getByTestId('owner').props.children).toBe('HOTEL_B'));
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(()=>expect(screen.getByTestId('room').props.children).toBe('B-101'));

  fireEvent.press(screen.getByTestId('back-a'));
  await waitFor(()=>expect(screen.getByTestId('hotel').props.children).toBe(hotelA.id));
  await waitFor(()=>expect(screen.getByTestId('restored').props.children).toBe('yes'));
  expect(screen.getByTestId('owner').props.children).toBe('HOTEL_A');
  expect(mockEvents.filter(x=>x==='login-A')).toHaveLength(1);
  expect(mockEvents).toContain('me-A');
  fireEvent.press(screen.getByTestId('read'));
  await waitFor(()=>expect(screen.getByTestId('room').props.children).toBe('A-101'));
  expect(mockEvents).not.toContain('logout-A');
});
