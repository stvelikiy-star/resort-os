import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {handler,testRouteAllowed,testValidateHotelRegistration,testValidateLinkPayload} from '../server.mjs';

test('GET allowlist is narrowly scoped to read-only FLEX routes',()=>{
 const empty=new URLSearchParams();
 assert.equal(testRouteAllowed('/v1/me',empty),'core');
 assert.equal(testRouteAllowed('/v1/hotels',empty),'core');
 assert.equal(testRouteAllowed('/v1/catalog',empty),'core');
 assert.equal(testRouteAllowed('/v1/hotels/123e4567-e89b-12d3-a456-426614174000/subscription',empty),'core');
 assert.equal(testRouteAllowed('/v1/hotels/123e4567-e89b-12d3-a456-426614174000/invoices',empty),'core');
 assert.equal(testRouteAllowed('/v1/partner/me/earnings',new URLSearchParams('period=week')),'partner');
 assert.equal(testRouteAllowed('/v1/platform/partner-earnings-summary',new URLSearchParams('period=month')),'partner');
 for(const path of ['/v1/payments','/v1/hotels/abc/invoices','/v1/onboarding/hotels','/v1/payouts','/v1/admin/grants','/v1/partner/me/earnings/../../admin'])
   assert.equal(testRouteAllowed(path,empty),null,path);
 assert.equal(testRouteAllowed('/v1/hotels',new URLSearchParams('hotel_id=any')),null);
 assert.equal(testRouteAllowed('/v1/partner/me/earnings',new URLSearchParams('period=year')),null);
 assert.equal(testRouteAllowed('/v1/partner/me/earnings',new URLSearchParams('period=month&agent_id=123')),null);
});
test('not configured: no false session, protected data never leaked', async()=>{
 const server=createServer(handler);
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 try{
  const status=await fetch(base+'/api/status');
  const s=await status.json();
  assert.equal(status.status,200); assert.equal(s.configured,false);
  assert.equal(s.payments_enabled,false); assert.equal(s.payouts_enabled,false);
  const r=await fetch(base+'/api/data/v1/hotels');
  assert.equal(r.status,503);
  assert.equal((await r.json()).error,'QA_BACKEND_NOT_CONFIGURED');
  const p=await fetch(base+'/api/data/v1/payouts');
  assert.ok([404,503].includes(p.status));
  const mutation=await fetch(base+'/api/data/v1/hotels',{method:'POST'});
  assert.equal(mutation.status,405);
  const home=await fetch(base+'/');
  assert.equal(home.status,200);
  assert.match(home.headers.get('content-security-policy'),/script-src 'self'/);
  assert.doesNotMatch(home.headers.get('content-security-policy'),/unsafe-inline/);
  assert.equal(home.headers.get('cache-control'),'no-store, private');
  assert.equal((await fetch(base+'/prototype.html')).status,404);
 }finally{await new Promise((resolve,reject)=>server.close(err=>err?reject(err):resolve()));}
});

test('PENDING hotel request rejects malformed or financial payloads',()=>{
 assert.deepEqual(testValidateHotelRegistration({display_name:' QA HOTEL 01 ',currency:'KGS'}),{display_name:'QA HOTEL 01',currency:'KGS'});
 for(const p of [
   {display_name:'X',currency:'KGS'},
   {display_name:'QA HOTEL',currency:'USD'},
   {display_name:'QA HOTEL',currency:'KGS',subscription_status:'ACTIVE'},
   {display_name:'QA HOTEL',currency:'KGS',payment:1000},
   {display_name:'QA'+String.fromCharCode(10)+'HOTEL',currency:'KGS'},
   {display_name:'  ',currency:'KGS'},
   null,
 ])assert.equal(testValidateHotelRegistration(p),null,JSON.stringify(p));
});
test('QA registration requires explicit environment approval and never mutates production by default',async()=>{
 const server=createServer(handler);
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const base='http://127.0.0.1:'+server.address().port;
  const status=await (await fetch(base+'/api/status')).json();
  assert.equal(status.qa_onboarding_enabled,false);
  const blocked=await fetch(base+'/api/actions/hotels',{
    method:'POST',headers:{'Content-Type':'application/json','Origin':base,'Idempotency-Key':'unique-request-123'},
    body:JSON.stringify({display_name:'QA HOTEL',currency:'KGS'})
  });
  assert.equal(blocked.status,503);
  assert.equal((await blocked.json()).error,'QA_ONBOARDING_NOT_ENABLED');
  const session=await fetch(base+'/api/session');
  assert.equal(session.status,401);
 }finally{await new Promise((resolve,reject)=>server.close(err=>err?reject(err):resolve()));}
});

test('P0 trusted hotel linking payloads reject broad mutation or forged signer metadata',()=>{
 assert.deepEqual(testValidateLinkPayload('challenge',{deployment_id:'qa-deploy-001',property_external_id:'qa-property-001'}),
   {deployment_id:'qa-deploy-001',property_external_id:'qa-property-001'});
 assert.deepEqual(testValidateLinkPayload('confirm',{signature_b64:'A'.repeat(88)}),{signature_b64:'A'.repeat(88)});
 for(const data of [
    {deployment_id:'x',property_external_id:'hotel-001'},
    {deployment_id:'qa-deploy-001',property_external_id:''},
    {deployment_id:'qa-deploy-001',property_external_id:'prop-001',activate:true},
    {deployment_id:'qa-deploy-001',property_external_id:'prop-001',payment_status:'PAID'},
 ]) assert.equal(testValidateLinkPayload('challenge',data),null);
 for(const data of [
    {signature_b64:'x'},
    {signature_b64:'A'.repeat(88),new_public_key:'injected-key'},
    {signature_b64:'A'.repeat(88),subscription_activated:true},
    {signature_b64:'A'.repeat(88)+'!'},
 ]) assert.equal(testValidateLinkPayload('confirm',data),null);
});
