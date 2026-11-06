import React from 'react';
import { Alert } from 'react-native';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import NewBooking from '../app/new-booking';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { ApiError } from '../src/api/types';
import type { AuthUser, Role } from '../src/api/types';
import { BOOKING_CREATE_ROLES, canCreateBooking, canStartBookingFromPms } from '../src/roles/bookingAccess';
import { hasTabForSession } from '../src/roles/registry';

const mockRecords = new Map<string, string>();
jest.mock('../src/lib/storage', () => ({
  getDurableItem: async (key: string) => mockRecords.get(key) ?? null,
  setDurableItem: async (key: string, value: string) => { mockRecords.set(key, value); },
  removeDurableItem: async (key: string) => { mockRecords.delete(key); },
}));

const grid = { rooms: [{ id: 'room-1', code: 'M-101', operational_state: 'READY', blocks: [] }] };
const preview = {
  room: { id: 'room-1', code: 'M-101' }, check_in: '2026-11-07', check_out: '2026-11-08', nights: 1, can_commit: true, conflicts: [],
  pricing: { source: 'CORE_RATE', sellable: true, total_kgs: 5000, discount_percent: null },
};
const mockModules = {
  pmsGrid: jest.fn(async () => grid),
  bookingPreview: jest.fn(async (_draft: unknown) => preview),
  bookingCommit: jest.fn(async (_payload: unknown) => ({ reservation_id: 'res-1', booking_number: 'B-1', total_kgs: 5000, price_adjusted_at_commit: false })),
};
const mockSession = {
  api: { mode: 'LIVE' as const },
  user: { id: 'u', username: 'rec', display_name: 'Rec', property_code: 'H', role: 'RECEPTION', module_permissions: ['PMS'] } as AuthUser,
  hotel: { id: 'hotel', name: 'Hotel', demo: false },
  serverAuthMode: 'shared_auth_preview' as const,
  locale: 'en',
};
jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));
jest.mock('../src/api/liveModules', () => ({
  useLiveModules: () => mockModules,
  localDate: (offset = 0) => offset === 1 ? '2026-11-07' : offset === 2 ? '2026-11-08' : '2026-11-06',
}));
jest.mock('expo-router', () => ({ useRouter: () => ({ push: jest.fn(), back: jest.fn() }) }));
jest.mock('react-native-safe-area-context', () => ({ useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }) }));

const as = (role: Role, grants = ['PMS']) => { mockSession.user = { ...mockSession.user, role, module_permissions: grants }; };
const screen = () => <ThemeProvider initial="light"><NewBooking /></ThemeProvider>;
async function fillAndPreview(view: Awaited<ReturnType<typeof render>>) {
  // Rooms stay locked until the durable booking journal has been read.
  await waitFor(() => expect(view.getByTestId('booking-room-room-1')).toBeEnabled());
  await fireEvent.press(view.getByTestId('booking-room-room-1'));
  await fireEvent.changeText(view.getByLabelText('Guest name'), 'Test Guest');
  await fireEvent.changeText(view.getByLabelText('Phone'), '+996555000111');
  await fireEvent.press(view.getByTestId('booking-preview'));
  await waitFor(() => view.getByTestId('booking-commit'));
}
/** Press the confirm button of the native Alert exactly as a user would. */
function confirmAlert() {
  const spy = jest.spyOn(Alert, 'alert');
  return { spy, press: async () => {
    const buttons = spy.mock.calls.at(-1)![2]!;
    await buttons.find(b => b.style !== 'cancel')!.onPress!();
  } };
}
beforeEach(() => {
  jest.clearAllMocks(); mockRecords.clear(); as('RECEPTION');
  mockModules.pmsGrid.mockImplementation(async () => grid);
  mockModules.bookingPreview.mockImplementation(async () => preview);
  mockModules.bookingCommit.mockImplementation(async () => ({ reservation_id: 'res-1', booking_number: 'B-1', total_kgs: 5000, price_adjusted_at_commit: false }));
});
afterEach(() => { jest.restoreAllMocks(); });

describe('RECEPTION booking access', () => {
  it('lets RECEPTION with PMS open the booking form and load the grid', async () => {
    const view = await render(screen());
    await waitFor(() => expect(mockModules.pmsGrid).toHaveBeenCalledTimes(1));
    expect(view.queryByTestId('booking-preview')).not.toBeNull();
    expect(canStartBookingFromPms('RECEPTION')).toBe(true);
    expect(hasTabForSession('RECEPTION', ['PMS'], 'LIVE', 'pms', 'shared_auth_preview')).toBe(true);
  });

  it('sends only core fields on preview, so no price or hold override leaves the app', async () => {
    const view = await render(screen());
    await fillAndPreview(view);
    expect(mockModules.bookingPreview).toHaveBeenCalledTimes(1);
    expect(Object.keys(mockModules.bookingPreview.mock.calls[0][0] as object).sort())
      .toEqual(['adults', 'check_in', 'check_out', 'children', 'guest_phone', 'room_id']);
  });

  it('commits through preview then commit with the CORE_RATE the server priced', async () => {
    const alert = confirmAlert();
    const view = await render(screen());
    await fillAndPreview(view);
    await fireEvent.press(view.getByTestId('booking-commit'));
    await alert.press();
    expect(mockModules.bookingCommit).toHaveBeenCalledTimes(1);
    const payload = mockModules.bookingCommit.mock.calls[0][0] as Record<string, unknown>;
    expect(payload).toMatchObject({ room_id: 'room-1', guest_name: 'Test Guest', phone: '+996555000111', expected_total_kgs: 5000, expected_pricing_source: 'CORE_RATE' });
    for (const forbidden of ['manager_total_kgs', 'discount_percent', 'discount_reason', 'extra_bed_count', 'extra_bed_unit_kgs', 'agent_id', 'hold_id']) {
      expect(payload).not.toHaveProperty(forbidden);
    }
    await waitFor(() => view.getByText(/B-1/));
  });

  it('does not create a second booking when commit is pressed twice', async () => {
    let release!: () => void;
    mockModules.bookingCommit.mockImplementationOnce(() => new Promise(resolve => {
      release = () => resolve({ reservation_id: 'res-1', booking_number: 'B-1', total_kgs: 5000, price_adjusted_at_commit: false });
    }));
    const alert = confirmAlert();
    const view = await render(screen());
    await fillAndPreview(view);
    await fireEvent.press(view.getByTestId('booking-commit'));
    const first = alert.press();
    await waitFor(() => expect(mockModules.bookingCommit).toHaveBeenCalledTimes(1));
    await alert.press(); // second confirmation while the first request is still in flight
    release(); await first;
    expect(mockModules.bookingCommit).toHaveBeenCalledTimes(1);
  });

  it('shows a server 403 and neither retries nor falls back to another path', async () => {
    mockModules.bookingCommit.mockRejectedValueOnce(new ApiError('FORBIDDEN'));
    const alert = confirmAlert();
    const view = await render(screen());
    await fillAndPreview(view);
    await fireEvent.press(view.getByTestId('booking-commit'));
    await alert.press();
    await waitFor(() => view.getByRole('alert'));
    expect(mockModules.bookingCommit).toHaveBeenCalledTimes(1);
    expect(view.queryByTestId('booking-commit')).toBeNull(); // preview dropped, must be repeated deliberately
    expect(view.queryByText(/B-1/)).toBeNull();
  });

  it('reports a 409 conflict and keeps the journal clear because the write was rejected', async () => {
    mockModules.bookingCommit.mockRejectedValueOnce(new ApiError('CONFLICT'));
    const alert = confirmAlert();
    const view = await render(screen());
    await fillAndPreview(view);
    await fireEvent.press(view.getByTestId('booking-commit'));
    await alert.press();
    await waitFor(() => view.getByRole('alert'));
    expect(mockModules.bookingCommit).toHaveBeenCalledTimes(1);
    expect([...mockRecords.keys()].filter(k => k.includes('pending-booking'))).toHaveLength(0);
  });
});

describe('booking access boundary', () => {
  it('keeps booking creation to the four server-admitted roles', () => {
    expect([...BOOKING_CREATE_ROLES].sort()).toEqual(['AGENT', 'MANAGER', 'OWNER', 'RECEPTION']);
  });
  it.each(['MAID', 'TECHNICIAN', 'COOK', 'WAITER', 'STORE_STAFF', 'DINING_STAFF', 'CONTENT_MANAGER', 'BEACH_PARTNER'] as Role[])(
    '%s is denied even with a PMS grant and never reads the grid', async (role) => {
      as(role, ['PMS']);
      expect(canCreateBooking(mockSession.user)).toBe(false);
      expect(canStartBookingFromPms(role)).toBe(false);
      const view = await render(screen());
      expect(view.queryByTestId('booking-preview')).toBeNull();
      expect(mockModules.pmsGrid).not.toHaveBeenCalled();
    });
  it('requires the PMS module grant even for RECEPTION', async () => {
    as('RECEPTION', ['RESERVATIONS']);
    expect(canCreateBooking(mockSession.user)).toBe(false);
    const view = await render(screen());
    expect(view.queryByTestId('booking-preview')).toBeNull();
    expect(mockModules.pmsGrid).not.toHaveBeenCalled();
  });
  it('does not widen cancel or schedule: the live client exposes no such operation', () => {
    const actual = jest.requireActual<typeof import('../src/api/liveModules')>('../src/api/liveModules');
    const names = Object.keys(actual.createLiveModules('https://hotel.example', jest.fn() as unknown as typeof fetch));
    expect(names.filter(name => /cancel|schedule|reschedul|move/i.test(name))).toEqual([]);
    expect(names).toEqual(expect.arrayContaining(['bookingPreview', 'bookingCommit']));
  });
});
