import { fireEvent, renderRouter, waitFor } from 'expo-router/testing-library';
import RootLayout from '../app/_layout';
import Index from '../app/index';
import AuthLayout from '../app/(auth)/_layout';
import Connect from '../app/(auth)/connect';
import Login from '../app/(auth)/login';
import AppTabs from '../app/(app)/_layout';
import More from '../app/(app)/more';
import Tasks from '../app/(app)/tasks';
import Rooms from '../app/(app)/rooms';
import Requests from '../app/(app)/requests';
import Admin from '../app/(app)/admin';
import Profile from '../app/(app)/profile';
import TaskDetail from '../app/task/[id]';
import RoomCard from '../app/room/[id]';
import NewRequest from '../app/new-request';
import { apiFor, dropApi } from '../src/api/factory';
import { DEMO_HOTELS } from '../src/api/hotels';
import { ApiError } from '../src/api/types';

jest.mock('react-native-safe-area-context', () => {
  const actual = jest.requireActual('react-native-safe-area-context');
  return { ...actual, SafeAreaProvider: ({ children }: any) => children, useSafeAreaInsets: () => ({ top: 0, bottom: 0, left: 0, right: 0 }) };
});

const routes = {
  _layout: RootLayout,
  index: Index,
  '(auth)/_layout': AuthLayout,
  '(auth)/connect': Connect,
  '(auth)/login': Login,
  '(app)/_layout': AppTabs,
  '(app)/more': More,
  '(app)/tasks': Tasks,
  '(app)/rooms': Rooms,
  '(app)/requests': Requests,
  '(app)/admin': Admin,
  '(app)/profile': Profile,
  'task/[id]': TaskDetail,
  'room/[id]': RoomCard,
  'new-request': NewRequest,
};

async function loginAs(role: string) {
  const screen = await renderRouter(routes, { initialUrl: '/connect' });
  await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 });
  await fireEvent.press(screen.getByTestId('hotel-demo-marina-issykkul'));
  await screen.findByTestId('login-submit');
  await fireEvent.press(screen.getByTestId(`demo-${role}`));
  await screen.findByTestId('progress-pct', {}, { timeout: 4000 }).catch(() => null);
  return screen;
}

describe('navigation, guards and screens', () => {
  it('browser demo can open manager workspace without username or password', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/connect' });
    await fireEvent.press(await screen.findByTestId('web-demo-start', {}, { timeout: 4000 }));
    expect(await screen.findByTestId('tab-admin', {}, { timeout: 4000 })).toBeTruthy();
    expect(await screen.findByTestId('task-t1', {}, { timeout: 4000 })).toBeTruthy();
  });

  it('unauthenticated direct profile link goes to hotel selection, not empty settings', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/profile' });
    expect(await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 })).toBeTruthy();
  });

  it('unauthenticated users land on hotel connection with demo banner', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/tasks' });
    await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 });
    expect(screen.getByTestId('demo-banner')).toBeTruthy();
    expect(screen.getByTestId('hotel-demo-sunrise-bishkek')).toBeTruthy();
  });

  it('protects a direct task detail deep link without login', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/task/t1' });
    expect(await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 })).toBeTruthy();
  });

  it('protects a direct room detail deep link without login', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/room/r1' });
    expect(await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 })).toBeTruthy();
  });

  it('protects a direct maintenance creation deep link without login', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/new-request' });
    expect(await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 })).toBeTruthy();
  });

  it('rejects insecure hotel address', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/connect' });
    await fireEvent.changeText(await screen.findByTestId('hotel-address'), 'http://evil.example');
    await fireEvent.press(screen.getByTestId('connect-add'));
    expect((await screen.findByTestId('connect-error')).props.children).toMatch(/HTTPS/);
  });

  it('maid: signs in, sees tasks tab only for her workspace, no admin tab', async () => {
    const screen = await loginAs('maid');
    await screen.findByTestId('task-t1', {}, { timeout: 4000 });
    expect(screen.queryByTestId('tab-admin')).toBeNull();
    expect(screen.queryByTestId('tab-requests')).toBeNull();
    expect(screen.getByTestId('tab-rooms')).toBeTruthy();
  });

  it('maid housekeeping flow reaches inspection via checklist', async () => {
    const screen = await loginAs('maid');
    await fireEvent.press(await screen.findByTestId('task-t2', {}, { timeout: 4000 }));
    await screen.findByTestId('hk-submit', {}, { timeout: 4000 });
    for (const k of ['BED_LINEN', 'BATHROOM', 'SURFACES', 'AMENITIES', 'FINAL_CHECK']) await fireEvent.press(screen.getByTestId(`check-${k}`));
    await fireEvent.press(screen.getByTestId('hk-submit'));
    await waitFor(() => expect(screen.getByTestId('task-msg')).toBeTruthy(), { timeout: 4000 });
  });

  it('manager sees admin tab', async () => {
    const screen = await loginAs('manager');
    await screen.findByTestId('task-t1', {}, { timeout: 4000 });
    expect(screen.getByTestId('tab-admin')).toBeTruthy();
    expect(screen.getByTestId('tab-requests')).toBeTruthy();
  });

  it('manager can assign an unassigned cleaning task from the admin screen', async () => {
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('tab-admin', {}, { timeout: 4000 }));
    const task = await screen.findByTestId('task-t8', {}, { timeout: 4000 });
    await fireEvent.press(task);
    await fireEvent.press(await screen.findByTestId('assign-u-maid2', {}, { timeout: 4000 }));
    await waitFor(() => expect(screen.queryByTestId('assign-u-maid2')).toBeNull(), { timeout: 4000 });
  });

  it('blocks resubmission of admin assignment after lost server acknowledgment', async () => {
    dropApi(DEMO_HOTELS[0].id); // Reset mutated demo seed from earlier test cases.
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('tab-admin', {}, { timeout: 4000 }));
    await fireEvent.press(await screen.findByTestId('task-t8', {}, { timeout: 4000 }));
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'assignTask').mockRejectedValueOnce(new ApiError('OFFLINE', 'lost ack'));
    try {
      await fireEvent.press(await screen.findByTestId('assign-u-maid2', {}, { timeout: 4000 }));
      expect(await screen.findByTestId('admin-unknown-result', {}, { timeout: 4000 })).toBeTruthy();
      const button = screen.getByTestId('assign-u-maid2');
      expect(button.props.accessibilityState?.disabled).toBe(true);
      await fireEvent.press(button);
      expect(spy).toHaveBeenCalledTimes(1);
    } finally { spy.mockRestore(); }
  });

  it('allows corrected admin assignment after explicit server rejection', async () => {
    dropApi(DEMO_HOTELS[0].id); // Reset mutated demo seed from earlier test cases.
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('tab-admin', {}, { timeout: 4000 }));
    await fireEvent.press(await screen.findByTestId('task-t8', {}, { timeout: 4000 }));
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'assignTask').mockRejectedValueOnce(new ApiError('CONFLICT', 'rejected'));
    try {
      await fireEvent.press(await screen.findByTestId('assign-u-maid2', {}, { timeout: 4000 }));
      expect(await screen.findByTestId('admin-action-error', {}, { timeout: 4000 })).toBeTruthy();
      expect(screen.queryByTestId('admin-unknown-result')).toBeNull();
      await fireEvent.press(screen.getByTestId('assign-u-maid2'));
      await waitFor(() => expect(spy).toHaveBeenCalledTimes(2), { timeout: 4000 });
    } finally { spy.mockRestore(); }
  });

  it('blocks resubmission of admin inspection approval after lost acknowledgment', async () => {
    dropApi(DEMO_HOTELS[0].id); // Reset mutated demo seed from earlier test cases.
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('tab-admin', {}, { timeout: 4000 }));
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'setTaskStatus').mockRejectedValueOnce(new ApiError('UNKNOWN', 'ack missing'));
    try {
      await fireEvent.press(await screen.findByTestId('approve-t3', {}, { timeout: 4000 }));
      expect(await screen.findByTestId('admin-unknown-result', {}, { timeout: 4000 })).toBeTruthy();
      const button = screen.getByTestId('approve-t3');
      expect(button.props.accessibilityState?.disabled).toBe(true);
      await fireEvent.press(button);
      expect(spy).toHaveBeenCalledTimes(1);
    } finally { spy.mockRestore(); }
  });
  it('does not create a second maintenance ticket after successful submission', async () => {
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('quick-new-request', {}, { timeout: 4000 }));
    await fireEvent.changeText(await screen.findByTestId('mt-text', {}, { timeout: 4000 }), 'Broken water valve');
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'createMaintenance');
    try {
      const submit = screen.getByTestId('mt-send');
      await fireEvent.press(submit);
      await screen.findByTestId('mt-msg', {}, { timeout: 4000 });
      await fireEvent.press(submit);
      expect(spy).toHaveBeenCalledTimes(1);
    } finally {
      spy.mockRestore();
    }
  });

  it('never submits maintenance twice after an unknown/lost POST response', async () => {
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('quick-new-request', {}, {timeout: 4000}));
    await fireEvent.changeText(await screen.findByTestId('mt-text', {}, {timeout: 4000}), 'Water leak in bathroom');
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'createMaintenance').mockRejectedValueOnce(new ApiError('OFFLINE', 'no response'));
    try {
      await fireEvent.press(screen.getByTestId('mt-send'));
      await screen.findByTestId('mt-unknown-result', {}, {timeout: 4000});
      const send = screen.getByTestId('mt-send');
      expect(send.props.accessibilityState?.disabled).toBe(true);
      await fireEvent.press(send);
      expect(spy).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('mt-check-existing')).toBeTruthy();
    } finally {
      spy.mockRestore();
    }
  });

  it('allows fixing and retrying a definitively rejected maintenance request', async () => {
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('quick-new-request', {}, {timeout: 4000}));
    await fireEvent.changeText(await screen.findByTestId('mt-text', {}, {timeout: 4000}), 'Replace damaged lamp');
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'createMaintenance').mockRejectedValueOnce(new ApiError('BAD_REQUEST'));
    try {
      await fireEvent.press(screen.getByTestId('mt-send'));
      await screen.findByTestId('mt-msg', {}, {timeout: 4000});
      expect(screen.queryByTestId('mt-unknown-result')).toBeNull();
      await fireEvent.press(screen.getByTestId('mt-send'));
      await waitFor(() => expect(spy).toHaveBeenCalledTimes(2), {timeout: 4000});
    } finally {
      spy.mockRestore();
    }
  });

  it('does not repeat a staff task mutation if the server response is lost', async () => {
    const screen = await loginAs('maid');
    await fireEvent.press(await screen.findByTestId('task-t1', {}, { timeout: 4000 }));
    const button = await screen.findByTestId('task-start', {}, { timeout: 4000 });
    const spy = jest.spyOn(apiFor(DEMO_HOTELS[0]), 'claimTask').mockRejectedValueOnce(new ApiError('OFFLINE', 'no acknowledgment'));
    try {
      await fireEvent.press(button);
      expect(await screen.findByTestId('task-unknown-result', {}, { timeout: 4000 })).toBeTruthy();
      expect(button.props.accessibilityState?.disabled).toBe(true);
      await fireEvent.press(button);
      expect(spy).toHaveBeenCalledTimes(1);
    } finally {
      spy.mockRestore();
    }
  });

  it('profile language and theme selectors respond to taps', async () => {
    const screen = await loginAs('manager');
    await fireEvent.press(await screen.findByTestId('tab-profile', {}, { timeout: 4000 }));
    const en = await screen.findByTestId('segment-en', {}, { timeout: 4000 });
    await fireEvent.press(en);
    await waitFor(() => expect(screen.getByTestId('segment-en').props.accessibilityState.checked).toBe(true), { timeout: 4000 });
    await fireEvent.press(screen.getByTestId('segment-dark'));
    await waitFor(() => expect(screen.getByTestId('segment-dark').props.accessibilityState.checked).toBe(true), { timeout: 4000 });
    await fireEvent.press(screen.getByTestId('segment-ru'));
    await fireEvent.press(screen.getByTestId('segment-system'));
  });

  it('waiter has no operational workspace (profile only)', async () => {
    const screen = await loginAs('waiter');
    await screen.findByTestId('tab-profile', {}, { timeout: 4000 });
    expect(screen.queryByTestId('tab-tasks')).toBeNull();
    expect(screen.queryByTestId('tab-admin')).toBeNull();
  });

  it('wrong password shows error', async () => {
    const screen = await renderRouter(routes, { initialUrl: '/connect' });
    await fireEvent.press(await screen.findByTestId('hotel-demo-marina-issykkul', {}, { timeout: 4000 }));
    await fireEvent.changeText(await screen.findByTestId('login-username'), 'maid');
    await fireEvent.changeText(screen.getByTestId('login-password'), 'nope');
    await fireEvent.press(screen.getByTestId('login-submit'));
    await screen.findByTestId('login-error', {}, { timeout: 4000 });
  });
});
