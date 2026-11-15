import React from 'react';
import {Alert} from 'react-native';
import {act,fireEvent,render,waitFor} from '@testing-library/react-native';
import '../src/i18n';
import {KitchenProcurement} from '../src/components/KitchenProcurement';
import {ThemeProvider} from '../src/theme/ThemeProvider';
import type {createLiveModules,KitchenStockSnapshot} from '../src/api/liveModules';
const REQUEST='11111111-1111-4111-8111-111111111111',RECEIPT='22222222-2222-4222-8222-222222222222',ITEM='33333333-3333-4333-8333-333333333333',FRESH='44444444-4444-4444-8444-444444444444';
const mockRecords=new Map<string,string>();let mockRole='STORE_STAFF';
jest.mock('../src/lib/storage',()=>({getDurableItem:async(k:string)=>mockRecords.get(k)??null,setDurableItem:async(k:string,v:string)=>{mockRecords.set(k,v);},removeDurableItem:async(k:string)=>{mockRecords.delete(k);}}));
jest.mock('../src/state/session',()=>({useSession:()=>({user:{id:'user',role:mockRole},hotel:{id:'hotel.example'},locale:'en'})}));
const list=jest.fn(),receive=jest.fn(),request=jest.fn(),reload=jest.fn();
const ledger={new_request_id:REQUEST,new_receipt_id:RECEIPT,payment_created:false,items:[{id:REQUEST,stock_name:'Rice',stock_item_id:ITEM,quantity:'10',received_quantity:'0',status:'APPROVED',unit:'KG'}]};
const live={procurementRequests:list,receiveKitchenProcurement:receive,requestKitchenProcurement:request,procurementNeeds:async()=>({items:[],is_complete:true})} as unknown as ReturnType<typeof createLiveModules>;
const stock={items:[{id:ITEM,name:'Rice',unit:'KG',is_sample:false}]} as KitchenStockSnapshot;
const screen=()=> <ThemeProvider initial="light"><KitchenProcurement live={live} stock={stock} reloadStock={reload}/></ThemeProvider>;
async function confirm(){await act(async()=>{await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(x=>x.style!=='cancel')?.onPress?.();});}
beforeEach(()=>{mockRecords.clear();mockRole='STORE_STAFF';list.mockReset().mockResolvedValue(ledger);receive.mockReset();request.mockReset();reload.mockReset().mockResolvedValue(undefined);jest.spyOn(Alert,'alert').mockImplementation(()=>{});});
afterEach(()=>jest.restoreAllMocks());
test('lost receipt acknowledgement -> remount -> explicit identical replay without a new ID',async()=>{
 receive.mockRejectedValueOnce(new Error('lost ack')).mockResolvedValue({id:RECEIPT,request_id:REQUEST,status:'PARTIAL',already_processed:true,payment_created:false});
 const first=await render(screen());await waitFor(()=>expect(first.getByLabelText('Received quantity')).toBeTruthy());
 await fireEvent.changeText(first.getByLabelText('Received quantity'),'2');await fireEvent.press(first.getByText('Receive stock'));await confirm();
 await waitFor(()=>expect(first.getByTestId('procurement-retry')).toBeEnabled());await first.unmount();
 const reopened=await render(screen());await waitFor(()=>expect(reopened.getByTestId('procurement-retry')).toBeEnabled());
 expect(receive).toHaveBeenCalledTimes(1);expect(reopened.queryByTestId('procurement-create')).toBeNull();
 await fireEvent.press(reopened.getByTestId('procurement-retry'));await waitFor(()=>expect(reopened.queryByTestId('procurement-pending')).toBeNull());
 expect(receive).toHaveBeenCalledTimes(2);expect(receive.mock.calls[0]).toEqual(receive.mock.calls[1]);expect(mockRecords.size).toBe(0);
});
test('new action fetches a fresh nonce instead of reusing the rendered snapshot',async()=>{
 list.mockResolvedValueOnce(ledger).mockResolvedValue({...ledger,new_request_id:FRESH});request.mockResolvedValue({id:FRESH,status:'REQUESTED',payment_created:false});
 const view=await render(screen());await waitFor(()=>expect(view.getByTestId('procurement-create')).toBeTruthy());
 await fireEvent.press(view.getByText('Rice · KG'));await fireEvent.changeText(view.getByLabelText('Quantity'),'4');
 await fireEvent.press(view.getByTestId('procurement-create'));await confirm();await waitFor(()=>expect(request).toHaveBeenCalled());
 expect(request.mock.calls[0][0]).toMatchObject({request_id:FRESH,stock_item_id:ITEM,quantity:'4'});
});
test('a cook cannot replay a saved warehouse receipt after a role change',async()=>{
 mockRecords.set('marina.procurement.v1.hotel.example.user',JSON.stringify({kind:'RECEIVE',requestId:REQUEST,receipt_id:RECEIPT,quantity:'2'}));mockRole='COOK';
 const view=await render(screen());await waitFor(()=>expect(view.getByTestId('procurement-retry')).toBeDisabled());expect(receive).not.toHaveBeenCalled();expect(mockRecords.size).toBe(1);
});
test('corrupt durable journal blocks new requests and receipts',async()=>{
 mockRecords.set('marina.procurement.v1.hotel.example.user','{invalid');const view=await render(screen());
 await waitFor(()=>expect(view.queryByTestId('procurement-create')).toBeNull());expect(receive).not.toHaveBeenCalled();expect(request).not.toHaveBeenCalled();
});
