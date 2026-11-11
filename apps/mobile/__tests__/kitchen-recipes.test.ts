import { ingredientRequirements, kitchenRecipe } from '../src/api/kitchenRecipes';

const recipe = {
  version:1,status:'APPROVED',is_sample:true,updated_at:'2026-11-11T00:00:00Z',
  ingredients:[{name:'Рис',unit:'KG',quantity_per_portion:'0.1'}],
};
const requirements = {
  basis:'PRODUCTION_PORTIONS',is_complete:true,contains_sample_data:true,inventory_deducted:false,
  items:[{name:'Рис',unit:'KG',planned_quantity:'2',prepared_quantity:'0.8',remaining_quantity:'1.2'}],
  missing_recipes:[],
};

describe('kitchen recipe contracts',()=>{
  it('accepts exact decimal strings and sample markers',()=>{
    expect(kitchenRecipe(recipe)?.ingredients[0].quantity_per_portion).toBe('0.1');
    expect(ingredientRequirements(requirements)?.contains_sample_data).toBe(true);
  });
  it('keeps compatibility with a server without recipe fields',()=>{
    expect(kitchenRecipe(undefined)).toBeNull();
    expect(ingredientRequirements(undefined)).toBeUndefined();
  });
  it('rejects invalid norms and unknown units',()=>{
    for (const quantity of ['0','-1','NaN','0.0000001','1001']) {
      expect(()=>kitchenRecipe({...recipe,ingredients:[{...recipe.ingredients[0],quantity_per_portion:quantity}]})).toThrow();
    }
    expect(()=>kitchenRecipe({...recipe,ingredients:[{...recipe.ingredients[0],unit:'G'}]})).toThrow();
  });
  it('does not convert a missing recipe into a complete calculation',()=>{
    expect(()=>ingredientRequirements({...requirements,missing_recipes:[
      {menu_item_id:'dish-1',name_ru:'Суп',service_date:'2026-11-11'}],
    })).toThrow();
  });
  it('rejects missing metadata and numeric quantities in place of decimal strings',()=>{
    expect(()=>ingredientRequirements({...requirements,contains_sample_data:undefined})).toThrow();
    expect(()=>ingredientRequirements({...requirements,items:[{...requirements.items[0],planned_quantity:2}]})).toThrow();
  });
});
