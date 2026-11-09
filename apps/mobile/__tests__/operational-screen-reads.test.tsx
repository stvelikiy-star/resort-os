import React from 'react';
import { act, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import Overview from '../app/(app)/overview';
import Tasks from '../app/(app)/tasks';
import Requests from '../app/(app)/requests';
import Rooms from '../app/(app)/rooms';
import Admin from '../app/(app)/admin';
import TaskDetail from '../app/task/[id]';
import RoomDetail from '../app/room/[id]';
import NewRequest from '../app/new-request';
import Reservation from '../app/reservation/[id]';
import Conversation from '../app/conversation/[id]';
import NewBooking from '../app/new-booking';
import Assistant from '../app/ai';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { AuthUser, Role, Room } from '../src/api/types';

const mockApi = {
  mode: 'LIVE' as const,
  listTasks: jest.fn(async () => []),
  listRooms: jest.fn(async (): Promise<Room[]> => []),
  listStaff: jest.fn(async () => []),
};
const mockModules = {
  dashboard: jest.fn(async () => null), reservation: jest.fn(async () => null),
  conversation: jest.fn(async () => null), pmsGrid: jest.fn(async () => null),
  assistantCapabilities: jest.fn(async () => null),
};
const mockSession = {
  api: mockApi,
  user: { id: 'staff', username: 'staff', display_name: 'Staff', property_code: 'TEST_HOTEL', role: 'MANAGER', module_permissions: [] } as AuthUser,
  hotel: { id: 'hotel', name: 'Test hotel', demo: false },
  serverAuthMode: null,
  locale: 'en',
};
jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));
jest.mock('../src/api/liveModules', () => ({
  useLiveModules: () => mockModules,
  localDate: (offset = 0) => offset === 1 ? '2026-11-07' : offset === 2 ? '2026-11-08' : '2026-11-06',
}));
jest.mock('expo-router', () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  useFocusEffect: jest.fn(), useLocalSearchParams: () => ({ id: 'r1' }), Redirect: () => null,
}));
jest.mock('react-native-safe-area-context', () => ({ useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }) }));

const panels = [
  { name: 'overview', Screen: Overview, reads: [mockModules.dashboard], grant: ['DASHBOARD'] },
  { name: 'tasks', Screen: Tasks, reads: [mockApi.listTasks], grant: ['OPS'] },
  { name: 'requests', Screen: Requests, reads: [mockApi.listTasks], grant: ['OPS'] },
  { name: 'rooms', Screen: Rooms, reads: [mockApi.listRooms], grant: ['OPS'] },
  { name: 'admin', Screen: Admin, reads: [mockApi.listTasks, mockApi.listStaff], grant: ['OPS', 'STAFF'] },
  { name: 'task detail', Screen: TaskDetail, reads: [mockApi.listTasks], grant: ['OPS'] },
  { name: 'room detail', Screen: RoomDetail, reads: [mockApi.listRooms, mockApi.listTasks], grant: ['OPS'] },
  { name: 'new maintenance', Screen: NewRequest, reads: [mockApi.listRooms], grant: ['OPS'] },
  { name: 'reservation', Screen: Reservation, reads: [mockModules.reservation], grant: ['RESERVATIONS'] },
  { name: 'conversation', Screen: Conversation, reads: [mockModules.conversation], grant: ['WHATSAPP'] },
];

function identity(role: Role, grants: string[]) {
  mockSession.user = { ...mockSession.user, role, module_permissions: grants };
}
function panel(Screen: React.ComponentType) {
  return <ThemeProvider initial="light"><Screen /></ThemeProvider>;
}
beforeEach(() => {
  jest.clearAllMocks();
  identity('MANAGER', []);
});

it('checks booking permissions before loading the room grid on a direct link', async () => {
  identity('MAID', ['PMS']);
  await render(panel(NewBooking));
  expect(mockModules.pmsGrid).not.toHaveBeenCalled();
});

it('loads the booking grid only after PMS is granted and stops again on revoke', async () => {
  identity('MANAGER', []);
  const screen = await render(panel(NewBooking));
  expect(mockModules.pmsGrid).not.toHaveBeenCalled();
  identity('MANAGER', ['PMS']);
  await screen.rerender(panel(NewBooking));
  await waitFor(() => expect(mockModules.pmsGrid).toHaveBeenCalledTimes(1));
  identity('MANAGER', []);
  await screen.rerender(panel(NewBooking));
  expect(mockModules.pmsGrid).toHaveBeenCalledTimes(1);
});

it('checks the assistant role before loading capabilities on a direct link', async () => {
  identity('COOK', ['DASHBOARD', 'DINING']);
  await render(panel(Assistant));
  expect(mockModules.assistantCapabilities).not.toHaveBeenCalled();
});

describe.each(panels)('$name network-read boundary', ({ Screen, reads, grant }) => {
  it('does not read with unrelated PMS access even though the workspace is mobile-ready', async () => {
    identity('MANAGER', ['PMS']);
    await render(panel(Screen));
    for (const read of reads) expect(read).not.toHaveBeenCalled();
  });

  it('rechecks grants on the same API instance after revoke and restore', async () => {
    identity('MANAGER', grant);
    const screen = await render(panel(Screen));
    await waitFor(() => { for (const read of reads) expect(read).toHaveBeenCalledTimes(1); });
    identity('MANAGER', ['PMS']);
    await screen.rerender(panel(Screen));
    for (const read of reads) expect(read).toHaveBeenCalledTimes(1);
    identity('MANAGER', grant);
    await screen.rerender(panel(Screen));
    await waitFor(() => { for (const read of reads) expect(read).toHaveBeenCalledTimes(2); });
  });

  it('never borrows grants for STORE_STAFF', async () => {
    identity('STORE_STAFF', ['PMS', 'OPS', 'STAFF', 'DASHBOARD']);
    await render(panel(Screen));
    for (const read of reads) expect(read).not.toHaveBeenCalled();
  });
});

it('rejects a maintenance-list read for a MAID even with OPS', async () => {
  identity('MAID', ['OPS']);
  await render(panel(Requests));
  expect(mockApi.listTasks).not.toHaveBeenCalled();
});

it('does not load the maintenance room picker for a MAID without creation rights', async () => {
  identity('MAID', ['OPS']);
  await render(panel(NewRequest));
  expect(mockApi.listRooms).not.toHaveBeenCalled();
});

it('loads allowed MAID and TECHNICIAN task/room screens', async () => {
  for (const role of ['MAID', 'TECHNICIAN'] as const) {
    identity(role, ['OPS']);
    const tasks = await render(panel(Tasks));
    await waitFor(() => expect(mockApi.listTasks).toHaveBeenCalled());
    await tasks.unmount();
    const rooms = await render(panel(Rooms));
    await waitFor(() => expect(mockApi.listRooms).toHaveBeenCalled());
    await rooms.unmount();
    jest.clearAllMocks();
  }
});

it('discards a pending room read after OPS revocation without replacing the API', async () => {
  let resolve!: (rooms: Room[]) => void;
  mockApi.listRooms.mockImplementationOnce(() => new Promise(done => { resolve = done; }));
  identity('MANAGER', ['OPS']);
  const screen = await render(panel(Rooms));
  identity('MANAGER', ['PMS']);
  await screen.rerender(panel(Rooms));
  await act(async () => { resolve([{ id: 'r1', code: 'ROOM-SECRET', floor: 1, state: 'CLEAN' }]); });
  expect(mockApi.listRooms).toHaveBeenCalledTimes(1);
  expect(screen.queryByText('ROOM-SECRET')).toBeNull();
});

it('removes already displayed rooms as soon as OPS is revoked', async () => {
  mockApi.listRooms.mockResolvedValueOnce([{ id: 'r1', code: 'ROOM-SECRET', floor: 1, state: 'CLEAN' }]);
  identity('MANAGER', ['OPS']);
  const screen = await render(panel(Rooms));
  expect(await screen.findByText('ROOM-SECRET')).toBeTruthy();
  identity('MANAGER', ['PMS']);
  await screen.rerender(panel(Rooms));
  expect(screen.queryByText('ROOM-SECRET')).toBeNull();
  expect(mockApi.listRooms).toHaveBeenCalledTimes(1);
});

const reservationWithFinancials = {
  reservation: { booking_number: 'QA-RBAC-1', status: 'CANCELLED',
    check_in: '2026-11-09', check_out: '2026-11-10' },
  guest: { first_name: 'Test', last_name: 'Guest', phone: null, email: null },
  room: { code: '1', room_type_name: 'Спальный', state: 'CLEAN' },
  schedule: [],
  finance: { total_kgs: 9001, paid_kgs: 1000, remaining_kgs: 8001 },
};

it('hides reservation finance immediately when FINANCE grant is revoked', async () => {
  mockModules.reservation.mockResolvedValue(reservationWithFinancials);
  identity('MANAGER', ['RESERVATIONS', 'FINANCE']);
  const screen = await render(panel(Reservation));
  expect(await screen.findByTestId('reservation-finance')).toBeTruthy();
  identity('MANAGER', ['RESERVATIONS']);
  await screen.rerender(panel(Reservation));
  expect(screen.queryByTestId('reservation-finance')).toBeNull();
  expect(screen.queryByText(/9.001 KGS/)).toBeNull();
});

it('never shows reservation finance to RECEPTION, even when FINANCE is present in grants', async () => {
  mockModules.reservation.mockResolvedValue(reservationWithFinancials);
  identity('RECEPTION', ['RESERVATIONS', 'FINANCE']);
  const screen = await render(panel(Reservation));
  await waitFor(() => expect(mockModules.reservation).toHaveBeenCalledTimes(1));
  expect(screen.queryByTestId('reservation-finance')).toBeNull();
});
