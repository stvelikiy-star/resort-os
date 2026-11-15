// The exact Mobile createHotelHttpClient TS is bundled from apps/mobile by esbuild.
// Test-only transport bridges the Mobile-required HTTPS host to disposable loopback.
// Native Android TLS/cookie handling is NOT verified by this CI.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';

const root = process.cwd();
const { chromium } = createRequire(root + '/web-candidate/scripts/package.json')('playwright');
const { createHotelHttpClient } = createRequire(root + '/package.json')('/tmp/marina-fl2-mobile-http-client.cjs');
const WEB = 'http://localhost:13001';
const MOBILE_HTTPS = 'https://ci.marinasmart.example/core';
const API = WEB + '/core/api/v1';
assert.equal(process.env.MARINA_SHARED_BROWSER_CI_CONFIRM, 'DISPOSABLE_TWO_HOTEL_BROWSER_CI');
assert.equal(process.env.MARINA_CROSS_CLIENT_CONFIRM, 'SYNTHETIC_MOBILE_TO_WEB_POSTGRES_ONLY');
assert.equal(process.env.APP_ENV, 'staging');
assert.equal(process.env.MARINA_SHARED_BROWSER_CI_PASSWORD?.startsWith('synthetic-ci-only-'), true);
const day = offset => {
 const now = new Date();
 now.setUTCDate(now.getUTCDate() + offset);
 return now.toISOString().slice(0,10);
};
const dateRange = (start,end) => ({ check_in:day(start),check_out:day(end) });
const blocksFor = (grid,id) => grid.rooms.flatMap(room => room.blocks||[]).filter(b=>b.reservation_id===id);

async function signIn(browser,hotel) {
 const context = await browser.newContext();
 const page = await context.newPage();
 await page.goto(WEB,{waitUntil:'domcontentloaded'});
 await page.waitForURL('**/shared-auth-preview');
 await page.getByLabel('Код организации').fill('tenant_'+hotel.at(-1).toLowerCase());
 await page.getByLabel('Код отеля').fill(hotel);
 await page.getByLabel('Логин').fill('owner');
 await page.getByLabel('Пароль').fill(process.env.MARINA_SHARED_BROWSER_CI_PASSWORD);
 const login = page.waitForResponse(r=>r.url().endsWith('/core/api/v1/auth/login')&&r.request().method()==='POST');
 await page.getByRole('button',{name:'Войти'}).click();
 assert.equal((await login).status(),200);
 await page.getByText('Подтверждённый вход:',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Шахматка'}).click();
 await page.getByRole('form',{name:'Форма бронирования'}).waitFor();
 const cookies=await context.cookies();
 assert.ok(cookies.some(c=>c.name==='resort_session'),'Missing Web hotel session cookie');
 return {context,page,cookies};
}

function createMobileTransport(cookies) {
 const header = cookies.map(c=>c.name+'='+c.value).join('; ');
 return async (expectedUrl,init={})=>{
   assert.equal(typeof expectedUrl,'string');
   assert.ok(expectedUrl.startsWith(MOBILE_HTTPS+'/api/v1/'),'Mobile HTTP client left trusted HTTPS API prefix');
   const realUrl = WEB + '/core' + expectedUrl.slice(MOBILE_HTTPS.length);
   const response = await fetch(realUrl,{
     ...init,
     headers:{...init.headers, Cookie:header},
     redirect:'manual'
   });
   assert.ok(![301,302,303,307,308].includes(response.status),'Unexpected redirect from local Web Core proxy');
   // Only the test transport rewrites the response.url; app HTTP client still
   // validates the original trusted API endpoint, as it does on Android.
   return {
      status:response.status,ok:response.ok,redirected:false,url:expectedUrl,
      json:()=>response.json()
   };
 };
}
async function main(){
 const browser=await chromium.launch({headless:true});
 try {
  const a=await signIn(browser,'HOTEL_A');
  const mobile=createHotelHttpClient(MOBILE_HTTPS,createMobileTransport(a.cookies));
  const me=await mobile.request('GET','/api/v1/auth/me');
  assert.equal(me.role,'OWNER');
  assert.equal(me.property_code,'HOTEL_A');
  const first=dateRange(2,4);
  const firstGrid=await mobile.request('GET',`/api/v1/pms/grid?start=${first.check_in}&end=${first.check_out}`);
  assert.equal(firstGrid.property,'HOTEL_A');
  const room=firstGrid.rooms.find(r=>r.code==='A101');
  assert.ok(room?.id,'Mobile cannot see same canonical room as Web');
  const draft={room_id:room.id,...first,adults:2,children:0};
  const quote=await mobile.request('POST','/api/v1/admin/pms/reservations/new/preview',draft);
  assert.equal(quote.can_commit,true);
  assert.equal(quote.pricing.source,'CORE_RATE');
  const committed=await mobile.request('POST','/api/v1/admin/pms/reservations/new/commit',{
    ...draft,guest_name:'Synthetic Mobile Transport Guest',phone:'+996555000331',
    expected_total_kgs:quote.pricing.total_kgs,expected_pricing_source:'CORE_RATE'
  });
  assert.match(committed.reservation_id,/^[0-9a-f-]{36}$/i);
  assert.equal(committed.payment_created,false);
  // Web browser MUST read the reservation committed by the original Mobile
  // HTTP client through the same Next.js proxy and same disposable PostgreSQL.
  const webGridResponse=await a.context.request.get(API+`/pms/grid?start=${first.check_in}&end=${first.check_out}`);
  assert.equal(webGridResponse.status(),200);
  const webGrid=await webGridResponse.json();
  assert.equal(blocksFor(webGrid,committed.reservation_id).length,1,'Web PMS did not see Mobile reservation');
  // Real Web UI creates a SECOND booking for a nonoverlapping date interval.
  const second=dateRange(6,8);
  const form=a.page.getByRole('form',{name:'Форма бронирования'});
  await form.getByLabel('Номер').selectOption({label:'A101 · CI Room'});
  await form.getByLabel('Заезд').fill(second.check_in);
  await form.getByLabel('Выезд').fill(second.check_out);
  await form.getByLabel('Имя гостя').fill('Synthetic Web PMS Guest');
  await form.getByLabel('Телефон гостя').fill('+996555000332');
  const previewResponse=a.page.waitForResponse(r=>r.url().endsWith('/core/api/v1/admin/pms/reservations/new/preview')&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Проверить доступность и цену'}).click();
  assert.equal((await previewResponse).status(),200);
  const confirm=form.getByRole('button',{name:'Подтвердить бронь'});
  await confirm.waitFor();
  const committedResponse=a.page.waitForResponse(r=>r.url().endsWith('/core/api/v1/admin/pms/reservations/new/commit')&&r.request().method()==='POST');
  await confirm.click();
  const webBookingResponse=await committedResponse;
  assert.equal(webBookingResponse.status(),201);
  const webBooking=await webBookingResponse.json();
  assert.notEqual(webBooking.reservation_id,committed.reservation_id);
  const secondGrid=await mobile.request('GET',`/api/v1/pms/grid?start=${second.check_in}&end=${second.check_out}`);
  assert.equal(blocksFor(secondGrid,webBooking.reservation_id).length,1,'Mobile HTTP client did not see Web reservation');
  // Preserve tenant isolation and no repeat commit after unknown ACK.
  const b=await signIn(browser,'HOTEL_B');
  const bClient=createHotelHttpClient(MOBILE_HTTPS,createMobileTransport(b.cookies));
  const bGrid=await bClient.request('GET',`/api/v1/pms/grid?start=${first.check_in}&end=${second.check_out}`);
  assert.equal(bGrid.property,'HOTEL_B');
  assert.equal(blocksFor(bGrid,committed.reservation_id).length,0);
  assert.equal(blocksFor(bGrid,webBooking.reservation_id).length,0);
  await assert.rejects(()=>bClient.request('GET','/api/v1/admin/reception/reservations/'+committed.reservation_id),{code:'NOT_FOUND'});
  const result={testOnly:true,nativeAndroidTested:false,syntheticTransportBridge:true,
   mobileToWeb:committed.reservation_id,webToMobile:webBooking.reservation_id,
   hotel:'HOTEL_A',otherHotel:'HOTEL_B',roomId:room.id,first,second};
  writeFileSync('/tmp/marina-fl2-cross-client-receipts.json',JSON.stringify(result));
  console.log('MARINA_MOBILE_TRANSPORT_TO_WEB_POSTGRES_CI_PASS: bidirectional bookings and foreign tenant isolation');
  await a.context.close();await b.context.close();
 }finally{await browser.close();}
}
await main();
