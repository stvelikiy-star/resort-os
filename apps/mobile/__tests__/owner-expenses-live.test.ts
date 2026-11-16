import {createLiveModules} from '../src/api/liveModules';
const expenseId='11111111-1111-4111-8111-111111111111';
const paymentId='22222222-2222-4222-8222-222222222222';
const respond=(body:unknown,status=200):Response=>({
 ok:status>=200&&status<300,status,json:async()=>body,
} as Response);
const ledger={
 items:[{id:expenseId,expense_date:'2026-11-15',category:'UTILITIES',
 title:'Electricity',amount_kgs:1000,settled_kgs:300,outstanding_kgs:700,status:'POSTED',
 supplier_name:null,document_reference:null,notes:null,
 created_by_id:null,void_reason:null,created_at:'2026-11-15T10:00:00Z'}],
 preview_limit:500,preview_truncated:false,new_expense_id:expenseId,new_settlement_id:paymentId,
 totals:{posted_expenses_kgs:1000,settled_against_period_expenses_kgs:300,
  outstanding_kgs:700,posted_count:1},
 scope:'OWNER_ONLY_PROPERTY_SCOPED',payment_created:false,
 truth:'POSTED_OBLIGATION_NOT_AUTOMATIC_PAYMENT_OR_PROFIT',
};

test('OWNER expense ledger displays actual posted, manually paid and open amounts',async()=>{
 const live=createLiveModules('https://test.example',jest.fn(async()=>respond(ledger)) as typeof fetch,
  'single_property');
 const data=await live.ownerExpenses('2026-11-15','2026-11-15');
 expect(data.items[0].outstanding_kgs).toBe(700);
 expect(data.totals.posted_expenses_kgs).toBe(1000);
 expect(data.payment_created).toBe(false);
});

test('expense ledger rejects fabricated settlement arithmetic and server UUID',async()=>{
 for(const broken of [
   {...ledger,items:[{...ledger.items[0],outstanding_kgs:900}]},
   {...ledger,new_settlement_id:'bad-id'},
   {...ledger,truth:'PROFIT_IS_1000'},
 ]){
   const live=createLiveModules('https://test.example',
     jest.fn(async()=>respond(broken)) as typeof fetch,'single_property');
   await expect(live.ownerExpenses('2026-11-15','2026-11-15'))
     .rejects.toMatchObject({code:'UNKNOWN'});
 }
});

test('unknown network outcome reuses exact manual expense UUID and payload',async()=>{
 const bodies:string[]=[];
 const transport=jest.fn(async(_url:RequestInfo|URL,init?:RequestInit)=>{
   bodies.push(String(init?.body));
   if(bodies.length===1)throw new TypeError('Response was lost');
   return respond({id:expenseId,status:'POSTED',already_processed:true,payment_created:false},201);
 });
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const mutation={id:expenseId,expense_date:'2026-11-15',category:'UTILITIES' as const,
  title:'Electricity',amount_kgs:1000,supplier_name:null,document_reference:null,notes:null};
 await expect(live.postOwnerExpense(mutation)).rejects.toBeDefined();
 await expect(live.postOwnerExpense(mutation)).resolves.toMatchObject({already_processed:true});
 expect(bodies).toHaveLength(2);
 expect(JSON.parse(bodies[0])).toEqual(JSON.parse(bodies[1]));
 expect(JSON.parse(bodies[1]).id).toBe(expenseId);
});

test('manual partial payment response is not a customer Payment and retries unchanged',async()=>{
 const bodies:string[]=[];
 const transport=jest.fn(async(url:RequestInfo|URL,init?:RequestInit)=>{
   expect(String(url)).toContain('/owner/expenses/'+expenseId+'/settlements');
   bodies.push(String(init?.body));
   if(bodies.length===1)throw new TypeError('Lost network acknowledgment');
   return respond({id:paymentId,expense_id:expenseId,already_processed:true,
     payment_created:false,source:'MANUAL_EXPENSE_SETTLEMENT_FACT'},201);
 });
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const mutation={id:paymentId,amount_kgs:300,paid_on:'2026-11-15',
  method:'BANK_TRANSFER' as const,reference:null};
 await expect(live.settleOwnerExpense(expenseId,mutation)).rejects.toBeDefined();
 await expect(live.settleOwnerExpense(expenseId,mutation)).resolves.toMatchObject({
  payment_created:false,source:'MANUAL_EXPENSE_SETTLEMENT_FACT'});
 expect(JSON.parse(bodies[0])).toEqual(JSON.parse(bodies[1]));
});

test('zero, negative and non-integer expenses rejected before transport',async()=>{
 const transport=jest.fn(async()=>respond({}));
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 for(const amount of [0,-1,1.2,Number.MAX_SAFE_INTEGER]){
   await expect(live.postOwnerExpense({id:expenseId,expense_date:'2026-11-15',
    category:'UTILITIES',title:'Utilities',amount_kgs:amount,
    supplier_name:null,document_reference:null,notes:null})).rejects.toMatchObject({code:'BAD_REQUEST'});
 }
 await expect(live.settleOwnerExpense(expenseId,{id:paymentId,amount_kgs:0,
  paid_on:'2026-11-15',method:'CASH',reference:null})).rejects.toMatchObject({code:'BAD_REQUEST'});
 expect(transport).not.toHaveBeenCalled();
});
