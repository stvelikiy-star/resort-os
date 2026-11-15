// C12 real compiled Guest Concierge browser acceptance with synthetic API only.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE||import.meta.url)('playwright');
const dir='guest-c12-evidence';fs.mkdirSync(dir,{recursive:true});
const browser=await chromium.launch({headless:true});const records=[];
const stay={qr_valid:true,authenticated:false,verification_required:true,active_stay:true,room:{code:'QA-301',name:'QA Room',room_type_name:'Suite'},guest:{first_name:'QA'},stay:{check_in:'2026-11-14',check_out:'2026-11-18'},property:{name:'MARINA SMART TEST HOTEL WITH A VERY LONG NAME',check_out_time:'12:00',official_contact:'+996555123456'},guest_capabilities:{request_codes:['TOWELS','HOUSEKEEPING','MAINTENANCE'],ai_available:false}};
try {
 for(const width of [320,390,768,1440]){
  const context=await browser.newContext({viewport:{width,height:850},colorScheme:'dark',reducedMotion:'reduce'});
  const page=await context.newPage();let auth=false;const requests=[];const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.route('**/core/api/v1/**',route=>{
   const req=route.request(),url=new URL(req.url()),p=url.pathname;
   const fulfill=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
   if(p.endsWith('/guest-os/rooms/qa-room/verify')){if(req.method()!=='POST')return fulfill({detail:'method not allowed'},405);auth=true;return fulfill({ok:true});}
   if(p.endsWith('/guest-os/rooms/qa-room/requests')){if(req.method()==='GET')return fulfill({items:requests});return fulfill({detail:'mutations blocked in visual QA'},403);}
   if(p.endsWith('/guest-os/rooms/qa-room'))return fulfill({...stay,authenticated:auth,verification_required:!auth});
   if(p.endsWith('/guest-os/logout')){auth=false;return fulfill({ok:true});}
   return fulfill({detail:'isolated QA mock'},404);
  });
  const response=await page.goto('http://127.0.0.1:3000/g/qa-room',{waitUntil:'domcontentloaded'});assert.equal(response?.status(),200);
  await page.locator('.concierge-auth input').waitFor({timeout:20000});
  const logo=page.locator('.concierge-brand img');assert.equal(await logo.count(),1);
  const logoOk=await logo.evaluate(e=>e.complete&&e.naturalWidth>0);assert.ok(logoOk,'Original approved PNG did not load');
  if(width===320) {
   const header=await page.locator('.concierge-topbar').evaluate(e=>{
    const name=e.querySelector('.concierge-brand strong').getBoundingClientRect();
    const langs=e.querySelector('.concierge-langs').getBoundingClientRect();
    return {nameWidth:name.width,langTop:langs.top,nameBottom:name.bottom};
   });
   assert.ok(header.nameWidth>=190,'Hotel name is squeezed by locales: '+JSON.stringify(header));
   assert.ok(header.langTop>=header.nameBottom-1,'320px locale controls must not compete with full hotel name');
  }
  let overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=1,'PIN page overflow '+width+': '+overflow);
  await page.screenshot({path:`${dir}/guest-pin-${width}.png`,fullPage:true});
  await page.screenshot({path:`${dir}/guest-pin-${width}-viewport.png`});
  await page.locator('.concierge-auth input').fill('123456');
  await page.locator('.concierge-auth form button').click();
  await page.locator('.concierge-actions button').first().waitFor();
  overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=1,'Logged-in Guest page overflow '+width+': '+overflow);
  await page.screenshot({path:`${dir}/guest-active-${width}.png`,fullPage:true});
  await page.screenshot({path:`${dir}/guest-active-${width}-viewport.png`});
  await page.locator('.concierge-actions button').first().click();
  const modal=page.locator('.concierge-modal');await modal.waitFor();
  const m=await page.evaluate(()=>{
   const close=document.querySelector('.concierge-modal-head button').getBoundingClientRect();
   const locale=[...document.querySelectorAll('.concierge-langs button')].map(x=>({w:x.getBoundingClientRect().width,h:x.getBoundingClientRect().height}));
   const frame=document.querySelector('.concierge-modal').getBoundingClientRect();
   return {width:window.innerWidth,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,close:{w:close.width,h:close.height},locale,frame:{x:frame.x,w:frame.width}};
  });
  assert.ok(m.overflow<=1,'Modal page overflow '+JSON.stringify(m));
  assert.ok(m.close.w>=43.9&&m.close.h>=43.9,'Modal close under 44 px');
  assert.ok(m.locale.every(v=>v.w>=43.9&&v.h>=43.9),'Locale under 44 px');
  // :focus-visible is keyboard-modality sensitive; move to keyboard mode first.
  await page.keyboard.press('Tab');
  await modal.getByRole('button',{name:'Закрыть'}).focus();
  const focus=await modal.getByRole('button',{name:'Закрыть'}).evaluate(e=>getComputedStyle(e).outlineStyle);assert.notEqual(focus,'none');
  await page.screenshot({path:`${dir}/guest-request-dialog-${width}.png`,fullPage:true});
  await page.screenshot({path:`${dir}/guest-request-dialog-${width}-viewport.png`});
  await modal.getByRole('button',{name:'Закрыть'}).click();assert.equal(await modal.count(),0);
  assert.deepEqual(errors,[],'No browser JS errors');
  records.push({width,logoOk,overflow,m,errors,syntheticAuthentication:true,noBusinessWrites:true});
  await context.close();
 }
 fs.writeFileSync(dir+'/results.json',JSON.stringify({syntheticData:true,physicalDevice:false,guestApiWritesBlocked:true,records},null,2));
 console.log('GUEST_C12_VISUAL_PASS: approved PNG, QR/PIN, authenticated state, services modal, 320/390/768/1440, touch targets, no overflow');
}catch(e){fs.writeFileSync(dir+'/failure.txt',String(e.stack||e));throw e;}finally{await browser.close();}
