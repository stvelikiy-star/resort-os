import { createLiveModules } from '../src/api/liveModules';
const id = '11111111-1111-4111-8111-111111111111';
const dish = {id, code:'SOUP',category:'SOUP' as const,name_ru:'Суп',name_kg:'Шорпо',name_en:'Soup',name_kz:'Сорпа',
  price_kgs:0,is_active:false,is_draft:true,recipe:null};
const response = (body:unknown):Response => ({ok:true,status:200,json:async()=>body} as Response);

test('reads draft author menu through the existing API and rejects malformed state',async()=>{
  const transport=jest.fn(async(_url:RequestInfo|URL)=>response({items:[dish]}));
  const live=createLiveModules('https://aska.example',transport as typeof fetch,'single_property');
  await expect(live.kitchenAuthorMenu()).resolves.toEqual([dish]);
  expect(String(transport.mock.calls[0]?.[0])).toContain('/api/v1/kitchen/menu');
  const malformed=createLiveModules('https://aska.example',jest.fn(async()=>response({items:[{...dish,is_draft:'true'}]})) as typeof fetch,'single_property');
  await expect(malformed.kitchenAuthorMenu()).rejects.toMatchObject({code:'UNKNOWN'});
});

test('cook draft edits omit price, activation and publication even when supplied',async()=>{
  const transport=jest.fn(async(_url:RequestInfo|URL,_init?:RequestInit)=>response(dish));
  const live=createLiveModules('https://aska.example',transport as typeof fetch,'single_property');
  await expect(live.updateKitchenMenuDraft(id,{...dish,price_kgs:999})).resolves.toBe(id);
  expect(JSON.parse(String(transport.mock.calls[0][1]?.body))).toEqual({
    category:dish.category,name_ru:dish.name_ru,name_kg:dish.name_kg,name_en:dish.name_en,name_kz:dish.name_kz,
  });
});

test('rejects acknowledgments that refer to a published dish',async()=>{
  const live=createLiveModules('https://aska.example',jest.fn(async()=>response({...dish,is_draft:false})) as typeof fetch,'single_property');
  await expect(live.updateKitchenMenuDraft(id,dish)).rejects.toMatchObject({code:'UNKNOWN'});
});
