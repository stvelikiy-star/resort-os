import { ApiError } from '../src/api/types';
import { receptionResponse,dashboardResponse,gridResponse,inboxListResponse,bookingCommitResponse } from '../src/api/contractValidation';
const invalid=(fn:()=>unknown)=>expect(fn).toThrow(ApiError);
describe('strict validation of LIVE responses',()=>{
 it('requires reservation identity, status, dates and amount',()=>{
  invalid(()=>receptionResponse({local_date:'2026-11-03',items:[{id:'r1',bookingNumber:'M-1'}]}));
  expect(receptionResponse({local_date:'2026-11-03',items:[]})).toMatchObject({items:[]});
 });
 it('rejects partial dashboard and invented metrics',()=>invalid(()=>dashboardResponse({property:{name:'Test'},rooms:{total:'2'}})));
 it('rejects incomplete reservation blocks',()=>invalid(()=>gridResponse({property:'A',rooms:[{id:'r',code:'101',operational_state:'CLEAN',blocks:[{id:'b'}]}]})));
 it('rejects inbox row missing a verified channel',()=>invalid(()=>inboxListResponse({items:[{id:'c1',status:'OPEN'}]})));
 it('rejects booking success without server reservation ID',()=>{
  invalid(()=>bookingCommitResponse({booking_number:'M-1',total_kgs:1000}));
  expect(bookingCommitResponse({reservation_id:'r1',booking_number:'M-1',total_kgs:1000,price_adjusted_at_commit:false}).reservation_id).toBe('r1');
 });
});
