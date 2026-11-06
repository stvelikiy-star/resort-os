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
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { AuthUser, Role, Room } from '../src/api/types';

const mockApi = {
  mode: 'LIVE' as const,
  listTasks: jest.fn(async () => []),
  listRooms: jest.fn(async (): Promise<Room[]> => []),
  listStaff: jest.fn(async () => []),
};
const mockModules = { dashboard: jest.fn(async () => null) };
const mockSession = {
  api: mockApi,
  user: { id: 'staff', username: 'staff', display_name: 'Staff', property_code: 'TEST_HOTEL', role: 'MANAGER', module_permissions: [] } as AuthUser,
  hotel: { id: 'hotel', name: 'Test hotel', demo: false },
  serverAuthMode: null,
  locale: 'en',
};
jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));
jest.mock('../src/api/liveModules', () => ({ useLiveModules: () => mockModules }));
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
