import React from 'react';
import { Alert, ScrollView } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import ReservationScreen from '../app/reservation/[id]';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { ApiError } from '../src/api/types';
import type { AuthUser, Role } from '../src/api/types';

const reservationId = '11111111-1111-4111-8111-111111111111';
const mockSession = {
  user: {
    id:'u1', username:'owner', display_name:'Test Owner', property_code:'HOTEL_A',
    role:'OWNER', module_permissions:['RESERVATIONS','PMS','FINANCE'],
  } as AuthUser,
  locale: 'ru',
};
const payload = {
  reservation: { id: reservationId, booking_number:'B-101', status:'GUARANTEED',
    check_in:'2026-12-01',check_out:'2026-12-03',total_kgs:5000 },
  guest:{ first_name:'Synthetic',last_name:'Guest',phone:'+996 555 111 222',email:'guest@example.test' },
  room:{ code:'A101',room_type_name:'Standard',state:'CLEAN' },
  finance:{ total_kgs:5000,paid_kgs:2000,remaining_kgs:3000 },
  schedule:[{ room_id:'22222222-2222-4222-8222-222222222222' }],
};
const mockLive={
  reservation:jest.fn(async (_id:string):Promise<any>=>payload),
  checkIn:jest.fn(async (_id:string)=>({reservation_id:reservationId,status:'CHECKED_IN'})),
  checkOut:jest.fn(async (_id:string)=>({reservation_id:reservationId,status:'CHECKED_OUT'})),
  schedulePreview:jest.fn(async ()=>({can_commit:false,conflicts:[],proposed_check_in:'2026-12-02',proposed_check_out:'2026-12-04',reservation:{version:'v1-11111111'}})),
  scheduleCommit:jest.fn(async ()=>({ok:true,reservation_id:reservationId})),
};
jest.mock('../src/state/session',()=>({useSession:()=>mockSession}));
jest.mock('../src/api/liveModules',()=>({useLiveModules:()=>mockLive}));
jest.mock('expo-router',()=>({useLocalSearchParams:()=>({id:reservationId}),useRouter:()=>({back:jest.fn(),push:jest.fn()})}));
jest.mock('react-native-safe-area-context',()=>({useSafeAreaInsets:()=>({top:0,bottom:0,left:0,right:0})}));

function as(role:Role, grants:string[], locale='ru'){
  mockSession.user={...mockSession.user,role,module_permissions:grants};
  mockSession.locale=locale;
}
const screen=(theme:'light'|'dark'='light')=><ThemeProvider initial={theme}><ReservationScreen/></ThemeProvider>;
beforeEach(()=>{
  jest.clearAllMocks();
  as('OWNER',['RESERVATIONS','PMS','FINANCE']);
  mockLive.reservation.mockImplementation(async()=>payload);
});
afterEach(()=>jest.restoreAllMocks());

describe('Mobile real reservation card: locale/theme/role states (UI, not native screenshots)',()=>{
  it.each(['ru','kg','en'] as const)('%s presents canonical guest, booking, room, dates and semantic status',async locale=>{
    as('OWNER',['RESERVATIONS','PMS','FINANCE'],locale);
    const view=render(screen());
    await waitFor(()=>expect(view.getByTestId('reservation-guest-summary')).toBeTruthy());
    expect(view.getByText('Synthetic Guest')).toBeTruthy();
    expect(view.getAllByText(/B-101/).length).toBeGreaterThan(0);
    expect(view.getByText('2026-12-01 → 2026-12-03')).toBeTruthy();
    expect(view.getByText('A101 · Standard')).toBeTruthy();
    expect(view.getByTestId('reservation-checkin')).toBeTruthy();
    expect(view.queryByTestId('reservation-checkout')).toBeNull();
    expect(view.getByTestId('reservation-finance')).toBeTruthy();
    expect(view.UNSAFE_getAllByType(ScrollView).length).toBeGreaterThan(0);
    expect(mockLive.reservation).toHaveBeenCalledWith(reservationId);
  });
  it.each(['light','dark'] as const)('%s keeps the card/actions mounted in scrollable layout',async theme=>{
    const view=render(screen(theme));
    await waitFor(()=>expect(view.getByTestId('reservation-guest-summary')).toBeTruthy());
    expect(view.getByTestId('reservation-call-guest')).toBeTruthy();
    expect(view.getByTestId('reservation-edit-dates')).toBeTruthy();
    expect(view.UNSAFE_getAllByType(ScrollView).length).toBeGreaterThan(0);
  });
  it('RECEPTION can view and check in but cannot see finance or owner-only schedule',async()=>{
    as('RECEPTION',['RESERVATIONS','PMS']);
    const view=render(screen());
    await waitFor(()=>expect(view.getByTestId('reservation-checkin')).toBeTruthy());
    expect(view.queryByTestId('reservation-finance')).toBeNull();
    expect(view.queryByTestId('reservation-edit-dates')).toBeNull();
    expect(view.getByTestId('reservation-guest-summary')).toBeTruthy();
  });
  it.each(['COOK','WAITER','MAID','TECHNICIAN','STORE_STAFF'] as Role[])('%s never requests reservation detail even when granted RESERVATIONS',async role=>{
    as(role,['RESERVATIONS','PMS','FINANCE']);
    const view=render(screen());
    expect(view.queryByTestId('reservation-guest-summary')).toBeNull();
    await waitFor(()=>expect(mockLive.reservation).not.toHaveBeenCalled());
  });
  it('OWNER without RESERVATIONS cannot query the card or view finance',async()=>{
    as('OWNER',['PMS','FINANCE']);
    const view=render(screen());
    expect(view.queryByTestId('reservation-finance')).toBeNull();
    expect(view.queryByTestId('reservation-guest-summary')).toBeNull();
    await waitFor(()=>expect(mockLive.reservation).not.toHaveBeenCalled());
  });
  it('unknown server write result never enables duplicate check-in',async()=>{
    mockLive.checkIn.mockRejectedValueOnce(new ApiError('OFFLINE','lost acknowledgement'));
    const alert=jest.spyOn(Alert,'alert');
    const view=render(screen());
    await waitFor(()=>expect(view.getByTestId('reservation-checkin')).toBeTruthy());
    await fireEvent.press(view.getByTestId('reservation-checkin'));
    const items=alert.mock.calls.at(-1)?.[2]||[];
    await items.find(item=>item.style!=='cancel')?.onPress?.();
    await waitFor(()=>expect(view.getByTestId('reservation-unknown-result')).toBeTruthy());
    expect(view.getByTestId('reservation-checkin')).toBeDisabled();
    await fireEvent.press(view.getByTestId('reservation-checkin'));
    expect(mockLive.checkIn).toHaveBeenCalledTimes(1);
  });
  it('loading failure shows retry and never pretends a confirmed reservation',async()=>{
    mockLive.reservation.mockRejectedValueOnce(new ApiError('OFFLINE','network unavailable'));
    const view=render(screen());
    await waitFor(()=>expect(view.getByText(/network unavailable/)).toBeTruthy());
    expect(view.queryByTestId('reservation-guest-summary')).toBeNull();
    expect(view.queryByTestId('reservation-checkin')).toBeNull();
  });
});
