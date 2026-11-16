import React from 'react';
import { Alert } from 'react-native';
import { act, fireEvent, render, waitFor } from '@testing-library/react-native';
import '../src/i18n';
import { OwnerExpenses } from '../src/components/OwnerExpenses';
import { ThemeProvider } from '../src/theme/ThemeProvider';
import type { createLiveModules } from '../src/api/liveModules';

let mockRole = 'OWNER';
let mockLocale = 'en';
jest.mock('../src/state/session', () => ({ useSession: () => ({ user: { id: 'owner', role: mockRole }, locale: mockLocale }) }));
const list = jest.fn();
const post = jest.fn();
const refresh = jest.fn();
const live = { ownerExpenses: list, postOwnerExpense: post } as unknown as ReturnType<typeof createLiveModules>;
const snapshot = { new_expense_id: '11111111-1111-4111-8111-111111111111', items: [], totals: { posted_expenses_kgs: 0, settled_against_period_expenses_kgs: 0, outstanding_kgs: 0 } };
const screen = () => <ThemeProvider initial="light"><OwnerExpenses live={live} from="2026-11-01" to="2026-11-16" onRecorded={refresh}/></ThemeProvider>;
beforeEach(() => {
  mockRole = 'OWNER'; mockLocale = 'en';
  list.mockReset().mockResolvedValue(snapshot); post.mockReset(); refresh.mockReset();
  jest.spyOn(Alert, 'alert').mockImplementation(() => {});
});
afterEach(() => jest.restoreAllMocks());
async function record() {
  const view = await render(screen());
  await waitFor(() => expect(view.getByLabelText('Expense title')).toBeTruthy());
  await fireEvent.changeText(view.getByLabelText('Expense title'), 'Repair supplies');
  await fireEvent.changeText(view.getByLabelText('Amount, KGS'), '1200');
  await fireEvent.press(view.getByTestId('owner-expense-save'));
  await act(async () => { await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(x => x.style !== 'cancel')?.onPress?.(); });
  return view;
}
test('confirmed write refreshes the ledger and notifies all parent reports once', async () => {
  post.mockResolvedValue({});
  await record();
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  expect(list).toHaveBeenCalledTimes(2);
  expect(post).toHaveBeenCalledTimes(1);
});
test('unknown write outcome retains identical retry and does not announce success or refresh totals', async () => {
  post.mockRejectedValueOnce(new Error('lost acknowledgement')).mockResolvedValue({});
  const view = await record();
  await waitFor(() => expect(view.getByTestId('owner-expense-retry')).toBeTruthy());
  expect(refresh).not.toHaveBeenCalled();
  expect(jest.mocked(Alert.alert).mock.calls.some(x => x[0] === 'Saved')).toBe(false);
  await fireEvent.press(view.getByTestId('owner-expense-retry'));
  await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
  expect(post.mock.calls[0]).toEqual(post.mock.calls[1]);
});
test('manager cannot read or write the OWNER ledger', async () => {
  mockRole = 'MANAGER';
  const view = await render(screen());
  expect(view.queryByTestId('owner-expenses')).toBeNull();
  expect(list).not.toHaveBeenCalled(); expect(post).not.toHaveBeenCalled();
});
