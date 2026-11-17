import React from 'react';
import {Alert} from 'react-native';
import {act, fireEvent, render, waitFor} from '@testing-library/react-native';
import '../src/i18n';
import {OwnerExpenses} from '../src/components/OwnerExpenses';
import {ThemeProvider} from '../src/theme/ThemeProvider';
import type {createLiveModules} from '../src/api/liveModules';

let mockRole='OWNER', mockLocale='en';
jest.mock('../src/state/session',()=>({
  useSession:()=>({user:{id:'owner',role:mockRole},hotel:{id:'hotel.test'},locale:mockLocale}),
}));
const ledger={
  new_expense_id:'11111111-1111-4111-8111-111111111111',
  new_settlement_id:'22222222-2222-4222-8222-222222222222',
  items:[],totals:{posted_expenses_kgs:0,settled_against_period_expenses_kgs:0,outstanding_kgs:0},
};
const list=jest.fn(), post=jest.fn(), settled=jest.fn(), onCommitted=jest.fn();
const live={ownerExpenses:list,postOwnerExpense:post,settleOwnerExpense:settled}
  as unknown as ReturnType<typeof createLiveModules>;
const makeScreen=()=> <ThemeProvider initial="light"><OwnerExpenses
  live={live} from="2026-11-01" to="2026-11-30" onCommitted={onCommitted}
/></ThemeProvider>;
beforeEach(()=>{
  mockRole='OWNER';mockLocale='en';
  list.mockReset().mockResolvedValue(ledger);
  post.mockReset().mockResolvedValue({});
  settled.mockReset();
  onCommitted.mockReset().mockResolvedValue(undefined);
  jest.spyOn(Alert,'alert').mockImplementation(()=>undefined);
});
afterEach(()=>jest.restoreAllMocks());
const labelByLocale:Record<string,[string,string]>={
  en:['Expense title','Amount, KGS'],
  ru:['Название расхода','Сумма, сом'],
  kg:['Чыгымдын аты','Сумма, сом'],
  kz:['Шығын атауы','Сома, сом'],
};
async function fill(view:ReturnType<typeof render>){
  const [name,amount]=labelByLocale[mockLocale];
  await waitFor(()=>expect(view.getByLabelText(name)).toBeTruthy());
  fireEvent.changeText(view.getByLabelText(name),'Supplies');
  fireEvent.changeText(view.getByLabelText(amount),'1200');
  fireEvent.press(view.getByTestId('owner-expense-save'));
}
async function confirm(){
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]??[];
  const action=buttons.find(x=>x.style!=='cancel')?.onPress;
  expect(action).toBeDefined();
  await act(async()=>{await action?.();});
}

test('confirmed expense writes once, reloads the ledger and invalidates parent finance',async()=>{
  const view=render(makeScreen()); await fill(view);await confirm();
  await waitFor(()=>expect(onCommitted).toHaveBeenCalledTimes(1));
  expect(post).toHaveBeenCalledTimes(1);
  expect(list).toHaveBeenCalledTimes(2);
  expect(view.queryByTestId('owner-expense-retry')).toBeNull();
});

test('unconfirmed network outcome retains identical retry, without updating finance',async()=>{
  post.mockRejectedValueOnce(new Error('lost ack'));
  const view=render(makeScreen());await fill(view);await confirm();
  await waitFor(()=>expect(view.getByTestId('owner-expense-retry')).toBeTruthy());
  expect(onCommitted).not.toHaveBeenCalled();
  expect(jest.mocked(Alert.alert).mock.calls.some(c=>c[0]==='Saved')).toBe(false);
  fireEvent.press(view.getByTestId('owner-expense-retry'));
  await waitFor(()=>expect(onCommitted).toHaveBeenCalledTimes(1));
  expect(post.mock.calls[0]).toEqual(post.mock.calls[1]);
});

test('post-commit parent refresh rejection still shows saved and never offers duplicate retry',async()=>{
  onCommitted.mockRejectedValueOnce(new Error('finance summary unavailable'));
  const view=render(makeScreen());await fill(view);await confirm();
  await waitFor(()=>expect(jest.mocked(Alert.alert).mock.calls.some(c=>c[0]==='Saved')).toBe(true));
  const success=jest.mocked(Alert.alert).mock.calls.find(c=>c[0]==='Saved');
  expect(success?.[1]).toContain('did not refresh');
  expect(view.queryByTestId('owner-expense-retry')).toBeNull();
  expect(post).toHaveBeenCalledTimes(1);
});

test('MANAGER cannot access OWNER expense ledger',async()=>{
  mockRole='MANAGER';
  const view=render(makeScreen());
  expect(view.queryByTestId('owner-expenses')).toBeNull();
  expect(list).not.toHaveBeenCalled();expect(post).not.toHaveBeenCalled();
});

test.each([
  ['en','Cancel'],['ru','Отмена'],['kg','Жокко чыгаруу'],['kz','Бас тарту'],
])('expense confirmation localizes cancel for %s',async(locale,cancel)=>{
  mockLocale=locale;
  const view=render(makeScreen());await fill(view);
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]??[];
  expect(buttons.find(x=>x.style==='cancel')?.text).toBe(cancel);
});