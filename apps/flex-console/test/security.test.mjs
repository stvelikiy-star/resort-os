import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {handler,testRouteAllowed,testValidateHotelRegistration,testValidateLinkPayload,testValidateCatalogAdminAction} from '../server.mjs';

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

test('catalog and subscription proposal actions are strict and never accept payment/activation fields',()=>{
 const goodSku={sku:'EXTRA_QA',title:'Extended QA',capability_key:'analytics.extra'};
 assert.deepEqual(testValidateCatalogAdminAction('sku',goodSku),goodSku);
 for(const bad of [
   {...goodSku,product_status:'AVAILABLE'},
   {...goodSku,payment_received:true},
   {...goodSku,capability_key:'../../etc'},
   {...goodSku,sku:'badSku'},
 ]) assert.equal(testValidateCatalogAdminAction('sku',bad),null);
 const validFuture=new Date(Date.now()+72*3600*1000).toISOString();
 const goodPrice={monthly_price:'1500.00',currency:'KGS',valid_from:validFuture};
 assert.deepEqual(testValidateCatalogAdminAction('price',goodPrice),goodPrice);
 for(const bad of [
   {...goodPrice,monthly_price:-1},
   {...goodPrice,monthly_price:'1e9'},
   {...goodPrice,monthly_price:'1.000'},
   {...goodPrice,currency:'USD'},
   {...goodPrice,valid_from:new Date().toISOString()},
   {...goodPrice,confirmed_payment_id:'fake'},
 ]) assert.equal(testValidateCatalogAdminAction('price',bad),null);
 const goodDraft={
   hotel_id:'123e4567-e89b-12d3-a456-426614174000',
   title:'QA package',period_start:'2027-01-01',period_end:'2027-01-31',
   skus:['BASE_PMS','EXTRA_QA']
 };
 assert.deepEqual(testValidateCatalogAdminAction('draft',goodDraft),goodDraft);
 for(const bad of [
   {...goodDraft,skus:['BASE_PMS','BASE_PMS']},
   {...goodDraft,period_end:'2026-12-01'},
   {...goodDraft,state:'ACTIVE'},
   {...goodDraft,enforcement:'ENFORCE'},
   {...goodDraft,paid:true},
   {...goodDraft,invoice_id:'uuid'},
 ]) assert.equal(testValidateCatalogAdminAction('draft',bad),null);
 assert.equal(testRouteAllowed('/v1/platform/catalog',new URLSearchParams()),'catalog_admin');
 assert.equal(testRouteAllowed('/v1/platform/catalog/skus/EXTRA_QA/versions',new URLSearchParams()),'catalog_admin');
 assert.equal(testRouteAllowed('/v1/platform/subscription-drafts',new URLSearchParams('hotel_id=123e4567-e89b-12d3-a456-426614174000')),'catalog_admin');
 assert.equal(testRouteAllowed('/v1/platform/subscription-drafts',new URLSearchParams('hotel_id=../admin')),null);
 assert.equal(testRouteAllowed('/v1/platform/catalog',new URLSearchParams('role=admin')),null);
});

test('FLEX Console RU/KG/EN includes every UI label without malformed text',()=>{
 const src=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const match=src.match(/const translations = (\{[\s\S]*?\n\});\nconst main=/);
 assert.ok(match,'Translation dictionary must be statically reviewable');
 const dict=vm.runInNewContext('('+match[1]+')');
 const reference=Object.keys(dict.ru).sort();
 assert.ok(reference.length>=130,'Admin, hotel, partners and catalog labels need coverage');
 for(const language of ['ru','kg','en']){
   assert.deepEqual(Object.keys(dict[language]).sort(),reference,language+' untranslated or excess keys');
   for(const [key,value] of Object.entries(dict[language])){
     assert.equal(typeof value,'string',language+': '+key);
     assert.ok(value.trim().length>0,language+': '+key);
     assert.ok(!value.includes('\uFFFD'),language+': '+key+' replacement character');
   }
   for(const key of ['billingHold','draftOnly','priceHistory','notPublished','linked','noDrafts','adminError'])
     assert.ok(dict[language][key].length>0,language+': '+key+' missing');
 }
 assert.ok(!src.includes('\uFFFD'),'Misdecoded console source');
});


test('QA password session renews only after live Better Auth verification',()=>{
 const server=readFileSync(new URL('../server.mjs',import.meta.url),'utf8');
 const identity=readFileSync(new URL('../auth/identity-enabled.mjs',import.meta.url),'utf8');
 const browser=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 assert.match(server,/await validatePasswordSession\(req,payload\.sub\)/);
 assert.match(server,/nearingExpiry\?\{\.\.\.mfaSigner\(payload\.sub,'password'\),csrf:session\.csrf\}:session/);
 assert.match(identity,/session\?\.user\?\.id===subject && session\.user\.emailVerified===true/);
 assert.match(identity,/new Date\(session\.session\.expiresAt\)\.getTime\(\)>Date\.now\(\)/);
 assert.match(browser,/if\(state\.status\?\.password_login_ready\)await refreshPlatformSession\(\)/);
 assert.match(browser,/},120000\)/);
});
test('read-only FLEX admin catalogue remains visible while write endpoints stay disabled',()=>{
 const browser=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const server=readFileSync(new URL('../server.mjs',import.meta.url),'utf8');
 assert.match(server,/qa_catalog_read_only_enabled:configured&&qaEnvironment/);
 assert.match(server,/target==='catalog_admin'&&qaCatalogAdmin\?catalogAdminApiOrigin:apiOrigin/);
 assert.match(server,/if\(!configured\|\|!qaCatalogAdmin\)return json\(res,503,\{error:'QA_CATALOG_ADMIN_NOT_ENABLED'\}\)/);
 assert.match(browser,/qa_catalog_read_only_enabled\|\|state\.status\?\.qa_catalog_admin_enabled/);
 assert.match(browser,/state\.status\?\.qa_catalog_admin_enabled\?'<button type="button"/);
});
test('one-time recovery has complete RU/KG/EN copy and never exposes its token in the URL after load',()=>{
 const js=readFileSync(new URL('../public/recover.js',import.meta.url),'utf8');
 const html=readFileSync(new URL('../public/recover.html',import.meta.url),'utf8');
 const match=js.match(/const translations=(\{[\s\S]*?\n\});\nconst form=/);
 assert.ok(match,'Recovery locale dictionary must be statically testable');
 const translations=vm.runInNewContext('('+match[1]+')');
 const keys=Object.keys(translations.ru).sort();
 for(const lang of ['ru','kg','en']){
   assert.deepEqual(Object.keys(translations[lang]).sort(),keys,lang+' incomplete recovery copy');
   for(const value of Object.values(translations[lang]))assert.ok(typeof value==='string'&&value.length>2);
 }
 assert.match(js,/history\.replaceState\(null,'',location\.pathname\)/);
 assert.match(js,/response\.status!==204/);
 assert.match(js,/form\.hidden=true/);
 assert.match(html,/autocomplete="new-password"/);
 assert.match(html,/id="recover-lang"/);
});
test('dashboard login finishes on signed password platform session before TOTP',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 assert.match(source,/if\(data\.platform_session===true\)\{location\.replace\('\/'\);return;\}/);
 const api=readFileSync(new URL('../server.mjs',import.meta.url),'utf8');
 assert.match(api,/password_login_ready:passwordLoginReady/);
 const recovery=readFileSync(new URL('../auth/recovery.mjs',import.meta.url),'utf8');
 assert.match(recovery,/DELETE FROM flex_auth\.verification/);
 assert.match(recovery,/DELETE FROM flex_auth\.session/);
});

test('first invitation completes password-only QA login without TOTP enrollment',()=>{
 const source=readFileSync(new URL('../public/enroll.js',import.meta.url),'utf8');
 const sessionSuccess=source.indexOf('if(session.platform_session===true)');
 const mfaEnrollment=source.indexOf("post('two-factor/enable'");
 assert.ok(sessionSuccess>0,'successful password login must be handled');
 assert.ok(mfaEnrollment>sessionSuccess,'redirect before TOTP enrollment');
 assert.match(source.slice(sessionSuccess,mfaEnrollment),/location\.replace\('\/'\);return;/);
});
