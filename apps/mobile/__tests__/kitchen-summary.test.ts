import type { KitchenOrder } from '../src/api/liveModules';
import { kitchenWorkload } from '../src/roles/kitchenSummary';

const order = (id: string, status: KitchenOrder['status'], items: KitchenOrder['items'], destination?: {table?:string,room?:string}): KitchenOrder => ({
  id, order_number:'B-'+id, status,
  table_code:destination?.table??null, room_code:destination?.room??null,
  total_kgs:0, notes:null, items,
});
describe('verified kitchen workload', () => {
  it('aggregates dishes without inventing meal choices or serving already-ready food',()=>{
    const r=kitchenWorkload([
      order('1','NEW',[{name:'Омлет',quantity:2},{name:'Чай',quantity:1}],{table:'T-01'}),
      order('2','COOKING',[{name:'омлет',quantity:3},{name:'Каша',quantity:1}],{room:'M-101'}),
      order('3','READY',[{name:'Омлет',quantity:4}],{table:'T-03'}),
      order('4','SERVED',[{name:'Омлет',quantity:7}],{table:'T-04'}),
      order('5','CANCELLED',[{name:'Каша',quantity:10}]),
    ]);
    expect(r).toMatchObject({totalActive:3,newOrders:1,preparing:1,ready:1,unknownDishOrders:0});
    expect(r.dishesToPrepare).toEqual([
      {name:'Омлет',quantity:5,destinations:['M-101','T-01']},
      {name:'Чай',quantity:1,destinations:['T-01']},
      {name:'Каша',quantity:1,destinations:['M-101']},
    ].sort((a,b)=>b.quantity-a.quantity||a.name.localeCompare(b.name)));
  });
  it('does not invent menu items from incomplete order details',()=>{
    const r=kitchenWorkload([order('1','NEW',[]),order('2','ACCEPTED',[{name:undefined,quantity:3},{name:'Суп',quantity:0}])]);
    expect(r.totalActive).toBe(2);
    expect(r.unknownDishOrders).toBe(2); // Both an empty order and an order with invalid quantity/name need review.
    expect(r.dishesToPrepare).toEqual([]);
  });
  it('does not merge across properties because input is only the active hotel API response',()=>{
    const r=kitchenWorkload([order('1','NEW',[{name:'Салат',quantity:1}],{table:'T-02'})]);
    expect(r.dishesToPrepare).toEqual([{name:'Салат',quantity:1,destinations:['T-02']}]);
  });
});
