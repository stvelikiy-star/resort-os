import React from 'react';
import {Alert} from 'react-native';
import {act,fireEvent,render,waitFor} from '@testing-library/react-native';
import '../src/i18n';
import {createLiveModules,KitchenAuthorMenuItem} from '../src/api/liveModules';
import {KitchenDraftPublication} from '../src/components/KitchenDraftPublication';
import {ThemeProvider} from '../src/theme/ThemeProvider';
let mockRole='OWNER';
jest.mock('../src/state/session',()=>({useSession:()=>({user:{role:mockRole},locale:'en'})}));
const item:KitchenAuthorMenuItem={id:'dish',code:'DISH',category:'MAIN',name_ru:'Блюдо',name_kg:'Тамак',name_en:'Dish',name_kz:'Тағам',price_kgs:0,is_draft:true,is_active:false,recipe:null};
const publish=jest.fn(),reload=jest.fn();
const live={publishKitchenMenuDraft:publish} as unknown as ReturnType<typeof createLiveModules>;
const screen=(dish=item)=> <ThemeProvider initial="light"><KitchenDraftPublication item={dish} live={live} onPublished={reload}/></ThemeProvider>;
beforeEach(()=>{mockRole='OWNER';publish.mockReset().mockResolvedValue(undefined);reload.mockReset().mockResolvedValue(undefined);jest.spyOn(Alert,'alert').mockImplementation(()=>{});});
afterEach(()=>jest.restoreAllMocks());
test.each(['OWNER','MANAGER'])('%s chooses price and confirms publication',async role=>{
 mockRole=role;const view=await render(screen());expect(view.getByTestId('menu-publish-submit-dish')).toBeDisabled();
 await fireEvent.changeText(view.getByTestId('menu-publish-price-dish'),'750');await fireEvent.press(view.getByTestId('menu-publish-submit-dish'));
 expect(publish).not.toHaveBeenCalled();
 await act(async()=>{await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(x=>x.style!=='cancel')?.onPress?.();});
 expect(publish).toHaveBeenCalledWith('dish',750);expect(reload).toHaveBeenCalledTimes(1);
});
test.each(['COOK','WAITER'])('%s has no publication control',async role=>{
 mockRole=role;const view=await render(screen());expect(view.queryByTestId('menu-publish-submit-dish')).toBeNull();expect(publish).not.toHaveBeenCalled();
});
test('missing translations and invalid prices cannot publish',async()=>{
 const missing=await render(screen({...item,name_kg:''}));await fireEvent.changeText(missing.getByTestId('menu-publish-price-dish'),'750');expect(missing.getByTestId('menu-publish-submit-dish')).toBeDisabled();await missing.unmount();
 const view=await render(screen());for(const price of ['-1','1.5','100001']){await fireEvent.changeText(view.getByTestId('menu-publish-price-dish'),price);expect(view.getByTestId('menu-publish-submit-dish')).toBeDisabled();}
});
test('a denied publication is not shown as confirmed',async()=>{
 publish.mockRejectedValue(new Error('Publication denied'));const view=await render(screen());
 await fireEvent.changeText(view.getByTestId('menu-publish-price-dish'),'750');await fireEvent.press(view.getByTestId('menu-publish-submit-dish'));
 await act(async()=>{await jest.mocked(Alert.alert).mock.calls.at(-1)?.[2]?.find(x=>x.style!=='cancel')?.onPress?.();});
 await waitFor(()=>view.getByText('Publication denied'));expect(reload).not.toHaveBeenCalled();
});
const response=(x:unknown):Response=>({ok:true,status:200,json:async()=>x}) as Response;
test('publication sends only explicit price/activation flags to canonical PATCH',async()=>{
 const transport=jest.fn(async(_url:RequestInfo|URL,_init?:RequestInit)=>response({id:'dish',price_kgs:750,is_draft:false,is_active:true}));
 const api=createLiveModules('https://hotel.example',transport as typeof fetch,'single_property');await api.publishKitchenMenuDraft('dish',750);
 expect(String(transport.mock.calls[0][0])).toContain('/api/v1/kitchen/menu/dish');
 expect(JSON.parse(String(transport.mock.calls[0][1]?.body))).toEqual({price_kgs:750,is_draft:false,is_active:true});
});
test('wrong publication acknowledgment and invalid price are rejected',async()=>{
 const transport=jest.fn(async()=>response({id:'other',price_kgs:750,is_draft:false,is_active:true}));const api=createLiveModules('https://hotel.example',transport as typeof fetch,'single_property');
 await expect(api.publishKitchenMenuDraft('dish',750)).rejects.toMatchObject({code:'UNKNOWN'});
 await expect(api.publishKitchenMenuDraft('dish',100001)).rejects.toMatchObject({code:'BAD_REQUEST'});expect(transport).toHaveBeenCalledTimes(1);
});
