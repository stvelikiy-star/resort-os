import React from 'react';
import { Alert } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import { AgentGuestServices } from '../src/components/AgentGuestServices';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import { ApiError } from '../src/api/types';
const RID = '33333333-3333-4333-8333-333333333333';
const mockAdd = jest.fn();
const mockHistory = jest.fn();
const mockModules = { addAgentGuestService: mockAdd, agentGuestServices: mockHistory };
let mockJournal: string | null = null;
const mockSession = {
  api: { mode: 'LIVE' }, user: { id: 'agent-1', role: 'AGENT', module_permissions: ['PMS'] },
  hotel: { id: 'hotel-1' }, locale: 'en', serverAuthMode: 'single_property',
};
jest.mock('expo-secure-store', () => ({
  getItemAsync: async () => mockJournal,
  setItemAsync: async (_key: string, value: string) => { mockJournal = value; },
  deleteItemAsync: async () => { mockJournal = null; },
}));
jest.mock('../src/state/session', () => ({ useSession: () => mockSession }));
jest.mock('../src/api/liveModules', () => ({
  AGENT_SERVICES: ['TRANSFER', 'MEALS', 'PARKING', 'SAUNA', 'BILLIARDS', 'EXCURSIONS'],
  useLiveModules: () => mockModules,
}));
const screen = () => <ThemeProvider initial="light"><AgentGuestServices reservationId={RID}/></ThemeProvider>;
beforeEach(() => {
  mockJournal = null; mockAdd.mockReset().mockResolvedValue(undefined);
  mockHistory.mockReset().mockResolvedValue({reservation_id:RID,items:[],preview_limit:200,preview_truncated:false});
  mockSession.user.role = 'AGENT'; mockSession.user.module_permissions = ['PMS'];
  mockSession.serverAuthMode = 'single_property';
});
afterEach(() => jest.restoreAllMocks());
async function submit(view: Awaited<ReturnType<typeof render>>) {
  await waitFor(() => expect(view.getByText('Add service')).toBeEnabled());
  await fireEvent.press(view.getByText('Add service'));
  await fireEvent.press(view.getByText('Transfer'));
  await act(async () => { await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(button => button.style !== 'cancel')?.onPress?.(); });
}
test('existing reservation uses durable service flow', async () => {
  jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  const view = await render(screen()); await submit(view);
  await waitFor(() => expect(mockAdd).toHaveBeenCalledWith(RID, 'TRANSFER', {}));
  expect(mockJournal).toBeNull();
});
test('timeout persists across remount and prevents resending', async () => {
  jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  mockAdd.mockRejectedValue(new Error('timeout'));
  const view = await render(screen()); await submit(view);
  await waitFor(() => expect(mockJournal).toContain(RID)); await view.unmount();
  const reopened = await render(screen());
  await waitFor(() => expect(reopened.getByText('Add service')).toBeDisabled());
  expect(mockAdd).toHaveBeenCalledTimes(1);
});
test('known denial clears pending operation', async () => {
  jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  mockAdd.mockRejectedValue(new ApiError('FORBIDDEN', 'Agent link revoked'));
  const view = await render(screen()); await submit(view);
  await waitFor(() => expect(view.getByText('Agent link revoked')).toBeTruthy());
  expect(mockJournal).toBeNull();
});
test.each(['OWNER', 'WAITER'])('role %s has no agent actions', async role => {
  mockSession.user.role = role; const view = await render(screen());
  expect(view.queryByText('Add service')).toBeNull(); expect(mockAdd).not.toHaveBeenCalled();
});
test('revoked PMS and shared preview hide writes', async () => {
  mockSession.user.module_permissions = []; const view = await render(screen());
  expect(view.queryByText('Add service')).toBeNull(); await view.unmount();
  mockSession.user.module_permissions = ['PMS']; mockSession.serverAuthMode = 'shared_auth_preview';
  const preview = await render(screen()); expect(preview.queryByText('Add service')).toBeNull();
});
test('agent schedules a service with note and sees refreshed server status', async () => {
  jest.spyOn(Alert, 'alert').mockImplementation(() => {});
  const view = await render(screen());
  await waitFor(() => expect(view.getByText('Add service')).toBeEnabled());
  await fireEvent.press(view.getByText('Add service'));
  await fireEvent.changeText(view.getByLabelText('Service date (YYYY-MM-DD, optional)'), '2026-11-15');
  await fireEvent.changeText(view.getByLabelText('Service time (HH:MM, optional)'), '10:30');
  await fireEvent.changeText(view.getByLabelText('Service note'), 'Meet at reception');
  mockHistory.mockResolvedValue({reservation_id:RID,preview_limit:200,preview_truncated:false,items:[{
    id:'task-1',reservation_id:RID,service_code:'TRANSFER',status:'IN_PROGRESS',
    service_date:'2026-11-15',service_time:'10:30',description:'Meet at reception',
  }]});
  await fireEvent.press(view.getByText('Transfer'));
  await act(async () => { await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(button => button.style !== 'cancel')?.onPress?.(); });
  expect(mockAdd).toHaveBeenCalledWith(RID, 'TRANSFER', {
    service_date:'2026-11-15',service_time:'10:30',description:'Meet at reception',
  });
  await waitFor(() => expect(view.getByText('Transfer · In progress')).toBeTruthy());
});
test('a server readback does not automatically clear an uncertain write journal', async () => {
  mockJournal = JSON.stringify({reservationId:RID,serviceCode:'TRANSFER',startedAt:'2026-11-15T12:00:00Z'});
  mockHistory.mockResolvedValue({reservation_id:RID,preview_limit:200,preview_truncated:false,items:[{
    id:'task-1',reservation_id:RID,service_code:'TRANSFER',status:'DONE',service_date:null,service_time:null,description:null,
  }]});
  const view = await render(screen());
  await waitFor(() => expect(view.getByText('Transfer · Completed')).toBeTruthy());
  expect(view.getByText('Add service')).toBeDisabled();
  expect(mockJournal).not.toBeNull();
  expect(mockAdd).not.toHaveBeenCalled();
});
