import React from 'react';
import {Alert} from 'react-native';
import {act,fireEvent,render,waitFor} from '@testing-library/react-native';
import '../src/i18n';
import {OwnerExpenses} from '../src/components/OwnerExpenses';
import {ThemeProvider} from '../src/theme/ThemeProvider';
import type {createLiveModules} from '../src/api/liveModules';

const EXPENSE='11111111-1111-4111-8111-111111111111',SETTLEMENT='22222222-2222-4222-8222-222222222222';
let mockLocale='en';
jest.mock('../src/state/session',()=>({useSession:()=>({user:{id:'owner',role:'OWNER'},hotel:{id:'hotel.example'},locale:mockLocale})}));
const ledger={new_expense_id:EXPENSE,new_settlement_id:SETTLEMENT,totals:{posted_expenses_kgs:0,settled_against_period_expenses_kgs:0,outstanding_kgs:0},items:[]};
const ownerExpenses=jest.fn(),postOwnerExpense=jest.fn(),settleOwnerExpense=jest.fn(),onChanged=jest.fn();
const live={ownerExpenses,postOwnerExpense,settleOwnerExpense} as unknown as ReturnType<typeof createLiveModules>;
const screen=()=> <ThemeProvider initial="light"><OwnerExpenses live={live} from="2026-11-01" to="2026-11-30" onChanged={onChanged}/></ThemeProvider>;
const LABELS: Record<string,string[]>={en:['Expense title','Amount, KGS','Save'],kg:['Чыгымдын аты','Сумма, сом','Сактоо'],ru:['Название расхода','Сумма, сом','Сохранить']};
async function fill(view:Awaited<ReturnType<typeof render>>,locale:string){
  const [name,amount,save]=LABELS[locale];
  await waitFor(()=>expect(view.getByLabelText(name)).toBeTruthy());
  await fireEvent.changeText(view.getByLabelText(name),'Flour');
  await fireEvent.changeText(view.getByLabelText(amount),'10000');
  await fireEvent.press(view.getByTestId('owner-expense-save'));
  expect(save).toBeTruthy();
}
beforeEach(()=>{mockLocale='en';ownerExpenses.mockReset().mockResolvedValue(ledger);postOwnerExpense.mockReset().mockResolvedValue({});settleOwnerExpense.mockReset();onChanged.mockReset().mockResolvedValue(undefined);jest.spyOn(Alert,'alert').mockImplementation(()=>undefined);});
afterEach(()=>jest.restoreAllMocks());

test('a confirmed expense write refreshes the parent finance summaries exactly once, after the ledger re-read',async()=>{
  const view=await render(screen());await fill(view,'en');
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2];
  await act(async()=>{await buttons?.find(x=>x.style!=='cancel')?.onPress?.();});
  await waitFor(()=>expect(postOwnerExpense).toHaveBeenCalledTimes(1));
  await waitFor(()=>expect(onChanged).toHaveBeenCalledTimes(1));
  expect(ownerExpenses.mock.calls.length).toBeGreaterThanOrEqual(2);
});

test('a failed write never refreshes summaries or shows success',async()=>{
  postOwnerExpense.mockRejectedValueOnce(new Error('timeout'));
  const view=await render(screen());await fill(view,'en');
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2];
  await act(async()=>{await buttons?.find(x=>x.style!=='cancel')?.onPress?.();});
  await waitFor(()=>expect(postOwnerExpense).toHaveBeenCalledTimes(1));
  expect(onChanged).not.toHaveBeenCalled();
  expect(jest.mocked(Alert.alert).mock.calls.some(c=>c[0]==='Saved')).toBe(false);
});

test('a failing parent refresh does not turn a committed write into an error',async()=>{
  onChanged.mockRejectedValueOnce(new Error('summary down'));
  const view=await render(screen());await fill(view,'en');
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2];
  await act(async()=>{await buttons?.find(x=>x.style!=='cancel')?.onPress?.();});
  await waitFor(()=>expect(jest.mocked(Alert.alert).mock.calls.some(c=>c[0]==='Saved')).toBe(true));
});

test.each([['en','Cancel'],['kg','Жокко чыгаруу'],['ru','Отмена']])('the confirmation cancel button is localized (%s)',async(locale,cancel)=>{
  mockLocale=locale;
  const view=await render(screen());await fill(view,locale);
  const buttons=jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]??[];
  expect(buttons.find(x=>x.style==='cancel')?.text).toBe(cancel);
});
