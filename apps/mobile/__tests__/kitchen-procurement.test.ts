import { procurementGaps } from '../src/roles/kitchenProcurement';
import type { IngredientRequirements } from '../src/api/kitchenRecipes';
import type { KitchenStockSnapshot } from '../src/api/liveModules';

const requirements: IngredientRequirements = {
  basis:'PRODUCTION_PORTIONS',is_complete:true,contains_sample_data:false,inventory_deducted:false,
  missing_recipes:[],
  items:[
    {name:'Рис',unit:'KG',planned_quantity:'4.5',prepared_quantity:'1.25',remaining_quantity:'3.25'},
    {name:'Молоко',unit:'L',planned_quantity:'1.25',prepared_quantity:'0',remaining_quantity:'1.25'},
  ],
};
const stock: KitchenStockSnapshot = {
  production_cost_kgs:'0',inventory_deducted_only_on_explicit_consume:true,
  items:[
    {id:'1',name:'  рис ',unit:'KG',cost_per_unit_kgs:'100',is_sample:false,balance:'2'},
    {id:'2',name:'молоко',unit:'L',cost_per_unit_kgs:'60',is_sample:false,balance:'2'},
  ],
};

describe('read-only kitchen purchase shortage estimate',()=>{
  it('subtracts eligible stock from remaining plan, not full plan or prepared quantities',()=>{
    expect(procurementGaps(requirements,stock)).toEqual([{
      name:'Рис',unit:'KG',required:'3.25',available:'2',shortage:'1.25',is_sample:false,
    }]);
  });
  it('never mixes incompatible units or sample inventory with real stock',()=>{
    const mixed = {...stock,items:[
      {...stock.items[0],unit:'PCS' as const,balance:'500'},
      {...stock.items[0],is_sample:true,balance:'200'},
    ]};
    expect(procurementGaps(requirements,mixed)[0].shortage).toBe('3.25');
    expect(procurementGaps(requirements,mixed)[1].shortage).toBe('1.25');
  });
  it('does not display zero or negative shortages as purchase requirements',()=>{
    const supplied = {...stock,items:stock.items.map(x=>({...x,balance:'9'}))};
    expect(procurementGaps(requirements,supplied)).toEqual([]);
  });
  it('preserves six-digit precision and refuses unsafe inventory numbers',()=>{
    expect(procurementGaps({...requirements,items:[{
      name:'Рис',unit:'KG',planned_quantity:'0.000003',prepared_quantity:'0',remaining_quantity:'0.000003'
    }]},{...stock,items:[{...stock.items[0],balance:'0.000002'}]})[0].shortage).toBe('0.000001');
    expect(()=>procurementGaps(requirements,{...stock,items:[{...stock.items[0],balance:'999999999999999.99'}]})).toThrow();
  });
  it('marks sample calculations as samples, never real procurement',()=>{
    const rows=procurementGaps({...requirements,contains_sample_data:true},{
      ...stock,items:[{...stock.items[0],is_sample:true,balance:'1'}],
    });
    expect(rows[0].is_sample).toBe(true);
    expect(rows[0].shortage).toBe('2.25');
  });
});
