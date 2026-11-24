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


test('hotel read state distinguishes empty subscription from failed API calls',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const match=source.match(/function hotelReadResult\(result,allowNotFound=false\)\{[\s\S]*?\n\}/);
 assert.ok(match,'hotel read guard must be independently testable');
 const read=vm.runInNewContext('('+match[0]+')');
 assert.equal(read({status:'fulfilled',value:[]}).length,0);
 assert.equal(read({status:'rejected',reason:{status:404}},true),null);
 for(const status of [401,403,404,429,500,502,503]){
   assert.throws(()=>read({status:'rejected',reason:{status}}),err=>err.status===status);
   if(status!==404) assert.throws(()=>read({status:'rejected',reason:{status}},true),err=>err.status===status);
 }
 assert.match(source,/const subscription=hotelReadResult\(sub,true\)/);
 assert.match(source,/const invoices=hotelReadResult\(inv\)/);
});


test('SUPER ADMIN summary reports partial API failures rather than hiding errors',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const block=source.slice(source.indexOf('async function overview(){'),source.indexOf('function hotelTable(items)'));
 assert.match(block,/Promise\.allSettled/);
 assert.match(block,/const degraded=results\.map/);
 assert.match(block,/r\.status==='rejected'/);
 assert.match(block,/degraded\+periodButtons\(\)/);
});


test('SUPER ADMIN draft dates mirror the API bounds without sending malformed periods',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const fragment=source.slice(source.indexOf('function validDraftPeriod('),source.indexOf('// Browser price estimate only;'));
 assert.ok(fragment.startsWith('function validDraftPeriod('));
 const valid=vm.runInNewContext('('+fragment.trim()+')');
 const today='2026-11-24';
 for(const dates of [
   ['2026-11-23','2026-11-23'],
   ['2026-11-24','2026-11-24'],
   ['2026-12-01','2027-12-02'],
   ['2027-11-25','2027-11-25']
 ])assert.equal(valid(...dates,today),true,JSON.stringify(dates));
 for(const dates of [
   ['2026-11-22','2026-11-24'],
   ['2026-11-25','2026-11-24'],
   ['2026-12-01','2027-12-03'],
   ['2027-11-26','2027-11-26'],
   ['2026-02-30','2026-03-01'],
   ['garbage','2027-01-01']
 ])assert.equal(valid(...dates,today),false,JSON.stringify(dates));
 assert.match(source,/if\(!validDraftPeriod\(form.elements.period_start.value,form.elements.period_end.value\)\)/);
 const match=source.match(/const translations = (\{[\s\S]*?\n\});\nconst main=/);
 assert.ok(match);
 const translations=vm.runInNewContext('('+match[1]+')');
 for(const lang of ['ru','kg','en'])assert.ok(translations[lang].draftDatesError.length>30);
});


test('commercial hotel card presents honest role-bound tabs without inventing usage or partner figures',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const section=source.slice(source.indexOf('function hotelCardTabs(){'),source.indexOf('async function hotelDetail(){'));
 const context={state:{me:{role:'HOTEL_OWNER'},hotelTab:'overview'},safe:x=>String(x),t:x=>x};
 const tabs=vm.runInNewContext('('+section.trim()+')',context);
 const owner=tabs();
 assert.match(owner,/data-hotel-tab="overview"/);
 assert.match(owner,/data-hotel-tab="finance"/);
 assert.match(owner,/data-hotel-tab="usage"/);
 assert.doesNotMatch(owner,/data-hotel-tab="relations"/);
 assert.doesNotMatch(owner,/data-hotel-tab="history"/);
 context.state.me.role='SUPER_ADMIN';
 const admin=tabs();
 assert.match(admin,/data-hotel-tab="relations"/);
 assert.match(admin,/data-hotel-tab="history"/);
 context.state.me.role='HOTEL_OWNER';
 context.state.hotelTab='relations';
 tabs();
 assert.equal(context.state.hotelTab,'overview','restricted tab resets for owner');
 const detail=source.slice(source.indexOf('async function hotelDetail(){'),source.indexOf('async function catalog(){'));
 assert.match(detail,/hotelTabPending/);
 assert.match(detail,/if\(\['usage','relations','history'\].includes\(state.hotelTab\)\)/);
 assert.match(detail,/const subscription=hotelReadResult\(sub,true\)/);
 assert.match(detail,/const invoices=hotelReadResult\(inv\)/);
 assert.doesNotMatch(detail,/Math\.random/);
});


test('commercial proposal estimate uses only effective published noncore KGS prices',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const begin=source.indexOf('function draftEstimate(');
 const end=source.indexOf('function refreshDraftEstimate(',begin);
 const estimate=vm.runInNewContext('('+source.slice(begin,end).trim()+')');
 const row=(sku,price,from='2026-11-20T00:00:00+06:00',to=null,extra={})=>({
  sku,status:'AVAILABLE',is_core:false,
  latest_price:{monthly_price:price,currency:'KGS',valid_from:from,valid_to:to},...extra
 });
 const rows=[row('A','1500.70'),row('B','125.25')];
 assert.equal(estimate(rows,['A','B'],'2026-11-25'),'1625.95');
 assert.equal(estimate(rows,[],'2026-11-25'),null);
 assert.equal(estimate(rows,['MISSING'],'2026-11-25'),null);
 assert.equal(estimate([row('A','100','2026-12-01T00:00:00+06:00')],['A'],'2026-11-25'),null);
 assert.equal(estimate([row('A','100','2026-11-20T00:00:00+06:00','2026-11-25T00:00:00+06:00')],['A'],'2026-11-25'),null);
 assert.equal(estimate([row('A','100',undefined,null,{is_core:true})],['A'],'2026-11-25'),null);
 assert.equal(estimate([row('A','100',undefined,null,{status:'PLANNED'})],['A'],'2026-11-25'),null);
 assert.equal(estimate([row('A','100',undefined,null,{latest_price:{monthly_price:'100',currency:'USD',valid_from:'2026-11-20T00:00:00+06:00'}})],['A'],'2026-11-25'),null);
 assert.match(source,/draftEstimate\(state\.draftPriceRows,checked,form\.elements\.period_start\.value\)===null/);
 assert.match(source,/draftEstimateDisclaimer/);
});


test('tariff proposal labels are safe without assigning fabricated modules or activation',()=>{
 const source=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const fragment=source.slice(source.indexOf('function packageProposalTitle('),source.indexOf('function applyPackageProposal('));
 assert.ok(fragment.startsWith('function packageProposalTitle('));
 const format=vm.runInNewContext('('+fragment.trim()+')');
 assert.equal(format('BASE','BASE'),'BASE');
 assert.equal(format('BUSINESS','BUSINESS'),'BUSINESS');
 assert.equal(format('PREMIUM','Extra analytics'),'PREMIUM — Extra analytics');
 assert.equal(format('CUSTOM','Hotel network 12'),'Hotel network 12');
 assert.equal(format('CUSTOM',''),null);
 assert.equal(format('ADMIN','Grant all'),null);
 assert.equal(format('BASE','x'.repeat(121)),null);
 assert.match(source,/name="package_kind"/);
 assert.match(source,/packageNote/);
 const draft=source.slice(source.indexOf("}else if(kind==='draft'||kind==='package'){"),source.indexOf("if(data.state!=='DRAFT'"));
 assert.match(draft,/packageProposalTitle/);
 assert.doesNotMatch(draft,/enforcement:'ENFORCE'|subscription_activated:true|payment_collected:true/);
 const head=source.slice(source.indexOf('const translations = ')+21,source.indexOf('\nconst main='));
 const dict=vm.runInNewContext('('+head.slice(0,head.lastIndexOf(';'))+')');
 for(const lang of ['ru','kg','en'])for(const key of ['packageType','packageCustom','packageNote','packageTitleRequired'])
  assert.ok(dict[lang][key]?.length,lang+':'+key);
});


test('tariff package version proxy is exact, QA-scoped and does not accept payment fields',()=>{
 const id='123e4567-e89b-12d3-a456-426614174000';
 const valid={
  hotel_id:id,package_kind:'BUSINESS',title:'QA business',
  period_start:'2027-01-01',skus:['AI_ASSISTANT'],
  discount_pct:'10.00',trial_days:14,custom_monthly_price:null
 };
 assert.deepEqual(testValidateCatalogAdminAction('package',valid),valid);
 for(const invalid of [
  {...valid,paid:true},
  {...valid,subscription_activated:true},
  {...valid,enforcement:'ENFORCE'},
  {...valid,package_kind:'ROOT'},
  {...valid,discount_pct:'101'},
  {...valid,trial_days:91},
  {...valid,custom_monthly_price:'999.00'},
  {...valid,skus:['AI_ASSISTANT','AI_ASSISTANT']},
  {...valid,period_start:'2027-02-30'},
 ])assert.equal(testValidateCatalogAdminAction('package',invalid),null);
 const custom={...valid,package_kind:'CUSTOM',discount_pct:'0',custom_monthly_price:'999.00'};
 assert.deepEqual(testValidateCatalogAdminAction('package',custom),custom);
 assert.equal(testRouteAllowed('/v1/platform/tariff-packages',new URLSearchParams('hotel_id='+id)),'catalog_admin');
 assert.equal(testRouteAllowed('/v1/platform/tariff-packages',new URLSearchParams()),null);
 assert.equal(testRouteAllowed('/v1/platform/tariff-packages',new URLSearchParams('hotel_id='+id+'&role=SUPER_ADMIN')),null);
 const src=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 assert.match(src,/saveQaCatalogAction\('tariff-packages'/);
 assert.match(src,/packageHistory/);
 assert.match(src,/data-package-save/);
 assert.match(src,/if\(data.state!=='DRAFT'\|\|data.enforcement!=='OFF'/);
});

test('shared template proxy accepts only a source package and a validated reference',()=>{
 const id='00000000-0000-4000-8000-000000000001';
 assert.deepEqual(testValidateCatalogAdminAction('template',{package_id:id}),{package_id:id});
 assert.equal(testValidateCatalogAdminAction('template',{package_id:id,hotel_id:id}),null);
 assert.equal(testValidateCatalogAdminAction('template',{package_id:'invalid'}),null);
 assert.equal(testRouteAllowed('/v1/platform/tariff-templates',new URLSearchParams()),'catalog_admin');
 assert.equal(testRouteAllowed('/v1/platform/tariff-templates',new URLSearchParams('hotel_id='+id)),null);
});
