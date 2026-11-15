// Isolated browser proof only. Every PMS response/write is synthetic and intercepted here.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE||import.meta.url)('playwright');
const out=process.env.C3_EVIDENCE||'c3-evidence';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch();const evidence=[];
const date=n=>{const d=new Date();d.setDate(d.getDate()+n);return d.toISOString().slice(0,10);};
const rooms=Array.from({length:6},(_,i)=>({id:`room-${i}`,code:String(301+i),name:`Номер QA ${301+i}`,room_type_code:'SUITE',room_type_name:'Люкс',building_or_zone:i<3?'Главный корпус':'Виллы',floor:'1',beds_raw:'2 гостя',operational_state:['CLEAN','DIRTY','IN_INSPECTION','TECH_BLOCK','CLEAN','CLEAN'][i],blocks:i<3?[{id:`block-${i}`,type:'RESERVATION',start:date(i),end:date(i+4),reason:null,reservation_id:`res-${i}`,booking_number:`QA-${100+i}`,reservation_status:i===0?'CHECKED_IN':'GUARANTEED',guest_name:i===0?'Иванова Анна (QA)':'Гость QA',guest_phone:'+996000000000',channel_source:'Booking.com'}]:[]}));
async function open(width=1440,theme='dark',role='OWNER',mode='ready') {
 const context=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:'reduce'});
 await context.addInitScript(({theme,mode})=>{localStorage.setItem('marina-admin-ui',mode==='legacy'?'legacy':'future-luxury');localStorage.setItem('marina-fl2-theme',theme);},{theme,mode});
 const page=await context.newPage();const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.routeWebSocket('**/ws/pms/grid**',ws=>{ /* Deliberately offline: no invented live updates. */ ws.close(); });
 await page.route('**/core/api/v1/**',async r=>{
  const u=new URL(r.request().url()),p=u.pathname.replace('/core','');const body=r.request().postDataJSON?.()||{};
  const json=x=>r.fulfill({json:x});requests.push({method:r.request().method(),path:p,body});
  if(p==='/api/v1/auth/me')return json({id:'qa',username:'qa',display_name:'QA',role,property_code:'QA',module_permissions:['PMS'],module_permissions_custom:true});
  if(p==='/api/v1/pms/grid'){
   if(mode==='error')return r.fulfill({status:503,json:{detail:'QA: шахматка временно недоступна'}});
   if(mode==='loading')await new Promise(resolve=>setTimeout(resolve,4000));
   return json({property:'QA',start:u.searchParams.get('start'),end:u.searchParams.get('end'),rooms:mode==='empty'?[]:rooms.map(room=>({...room,blocks:room.blocks.map(b=>role==='AGENT'?{...b,guest_name:null,booking_number:null,guest_phone:null}:b)}))});
  }
  if(p.endsWith('/control-snapshot'))return json({complete:true,generated_at:new Date().toISOString(),local_date:date(0),window:{start:date(0),end:date(31)},rooms:rooms.map(r=>({...r,state:r.operational_state})),room_states:{CLEAN:3,DIRTY:1,IN_INSPECTION:1,TECH_BLOCK:1},reservations:[],tasks:[],summary:{room_count:6,active_reservations:3,active_tasks:0,debt_total_kgs:15000,unassigned_guaranteed:0}});
  if(p==='/api/v1/admin/reception/reservations')return json({items:[0,1,2].map(i=>({id:`res-${i}`,totalKgs:20000,paidKgs:i===0?20000:5000,remainingKgs:i===0?0:15000}))});
  if(p.endsWith('/owner-corrections/agents'))return json({items:[]});
  if(p.endsWith('/reservations/new/preview'))return json({room:{...rooms[4],capacity_adults:2,effective_capacity_adults:2,extra_bed_allowed:true,max_extra_bed_count:1},check_in:body.check_in,check_out:body.check_out,nights:1,adults:body.adults,children:body.children,extra_bed_count:0,conflicts:[],can_commit:true,pricing:{source:'CORE_RATE',sellable:true,total_kgs:5000,base_total_kgs:5000,extra_beds_total_kgs:0,discount_percent:0,discount_kgs:0,returning_guest:false,previous_stays:0,auto_discount_percent:0,core_total_kgs:5000,core_sellable:true,nights:[{date:body.check_in,price_kgs:5000}]}});
  if(p.endsWith('/reservations/new/commit'))return json({booking_number:'QA-CREATED',total_kgs:5000});
  if(p==='/api/v1/admin/pms/holds')return json({id:'11111111-1111-1111-1111-111111111111',expires_at:new Date(Date.now()+3600000).toISOString()});
  if(/\/reservations\/res-\d\/schedule$/.test(p))return json({reservation:{id:'res-0',booking_number:'QA-100',status:'CHECKED_IN',check_in:date(0),check_out:date(4),stored_total_kgs:20000,version:1},guest:{name:'Иванова Анна (QA)',phone:'+996000000000'},schedule:[{inventory_block_id:'block-0',room_id:'room-0',room_code:'301',room_state:'CLEAN',room_type_name:'Люкс',room_type_code:'SUITE',start:date(0),end:date(4)}],local_today:date(0)});
  if(/\/rooms\/room-\d$/.test(p))return json({room:{...rooms[0],capacity_adults:2,capacity_children:1,updated_at:new Date().toISOString()},blocks:[],tasks:[],truth:''});
  if(r.request().method()!=='GET')return r.fulfill({status:400,json:{detail:'QA blocks unimplemented mutations'}});
  return r.continue();
 });
 await page.goto(process.env.ADMIN_URL||'http://127.0.0.1:3001',{waitUntil:'domcontentloaded'});
 // RECEPTION normally starts in Reservations; explicitly navigate to its existing PMS grant.
 await page.waitForSelector('.admin-shell-actions');
 if(role==='RECEPTION')await page.locator('[data-section="PMS"]').click();
 await page.waitForSelector('.owner-grid-shell');
 if(mode!=='loading')await page.waitForTimeout(350);
 return {page,context,errors,requests};
}
async function metrics(page,selector='.owner-grid-shell'){
 return page.evaluate(selector=>{const root=document.querySelector(selector);return {overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,smallControls:[...root.querySelectorAll('button,input,select')].filter(e=>e.getClientRects().length&&!e.closest('.owner-room-row')).filter(e=>e.getBoundingClientRect().height<43.9).map(e=>({text:e.textContent,height:e.getBoundingClientRect().height})),innerOverflow:root.scrollWidth-root.clientWidth};},selector);
}
async function newBooking(page,keyboard=false){const cell=page.locator('.owner-night-cell[data-room-code="305"][data-free="true"]').first();await cell.scrollIntoViewIfNeeded();if(keyboard){await cell.focus();await page.keyboard.press('Enter');}else await cell.click();await page.locator('.owner-booking-modal .owner-commercial-prices').first().waitFor();}
async function close(page,selector){await page.locator(selector).getByRole('button',{name:'Закрыть',exact:true}).click();}
try {
 for(const width of [1440,768,390])for(const theme of ['dark','light']){
  const t=await open(width,theme),{page}=t;await page.locator('.owner-booking-bar').first().waitFor();
  const m=await metrics(page);assert.equal(m.overflow,0);assert.equal(m.innerOverflow,0);assert.deepEqual(m.smallControls,[]);assert.deepEqual(t.errors,[]);
  const clipped=await page.locator('.owner-booking-bar').evaluateAll(bars=>bars.flatMap(b=>[...b.children].filter(c=>c.getBoundingClientRect().top<b.getBoundingClientRect().top||c.getBoundingClientRect().bottom>b.getBoundingClientRect().bottom).map(c=>c.textContent)));assert.deepEqual(clipped,[]);
  const day=page.locator('.owner-day-head.today strong');assert.equal(await day.evaluate(e=>getComputedStyle(e).color),await day.evaluate(e=>getComputedStyle(document.documentElement).getPropertyValue('--mx-ink').trim()).then(hex=>{const m=hex.replace('#','');return `rgb(${parseInt(m.slice(0,2),16)}, ${parseInt(m.slice(2,4),16)}, ${parseInt(m.slice(4,6),16)})`;}));
  await page.screenshot({path:`${out}/pms-${width}-${theme}.png`,fullPage:true});
  await page.getByPlaceholder('Номер, гость, бронь…').fill('нет-такого-номера');await page.locator('.owner-grid-empty').waitFor();await page.getByPlaceholder('Номер, гость, бронь…').fill('');await page.locator('.owner-booking-bar').first().waitFor();
  await page.getByRole('button',{name:'Показать 14 дней',exact:true}).click();await page.waitForTimeout(150);assert.equal(await page.locator('.owner-grid-scroll').getAttribute('data-window-days'),'14');
  const bar=page.locator('.owner-booking-bar').first();await bar.scrollIntoViewIfNeeded();await bar.hover();await page.getByRole('tooltip').waitFor();assert.match(await page.getByRole('tooltip').innerText(),/QA-100/);await page.screenshot({path:`${out}/preview-${width}-${theme}.png`});await bar.focus();await page.keyboard.press('Escape');assert.equal(await page.getByRole('tooltip').count(),0);
  await newBooking(page);const form=await metrics(page,'.owner-booking-modal');assert.equal(form.overflow,0);assert.deepEqual(form.smallControls,[]);await page.screenshot({path:`${out}/new-booking-${width}-${theme}.png`});await close(page,'.owner-booking-modal');
  await bar.click();await page.locator('.v8-builder .v8-segment-card').first().waitFor();const schedule=await metrics(page,'.v8-builder');if(width===390)assert.ok(await page.locator('.v8-segment-index span').first().evaluate(e=>e.getBoundingClientRect().width>80 && e.getBoundingClientRect().height <= parseFloat(getComputedStyle(e).lineHeight)*2),'Segment status must not wrap into tiny column');assert.equal(schedule.overflow,0);assert.deepEqual(schedule.smallControls,[]);await page.screenshot({path:`${out}/booking-${width}-${theme}.png`});if(width===390){await page.locator('.v8-builder').evaluate(e=>{e.scrollTop=e.scrollHeight;});await page.screenshot({path:`${out}/booking-bottom-${width}-${theme}.png`});}await close(page,'.v8-builder');
  evidence.push({width,theme,metrics:m,form,schedule,tooltip:true,errors:t.errors});await t.context.close();
 }
 const t=await open();await newBooking(t.page,true);await t.page.getByLabel('Имя гостя',{exact:true}).fill('Тестовый гость');await t.page.getByLabel('Телефон',{exact:true}).fill('+996000000000');await t.page.getByRole('button',{name:'Подтвердить бронь',exact:true}).click();await t.page.getByText('QA-CREATED',{exact:true}).waitFor();assert.equal(t.requests.filter(r=>r.path.endsWith('/new/commit')).length,1);await t.page.getByRole('button',{name:'Готово',exact:true}).click();
 await newBooking(t.page);await t.page.getByLabel('Имя гостя',{exact:true}).fill('Тест HOLD');await t.page.getByLabel('Телефон',{exact:true}).fill('+996000000000');await t.page.getByRole('button',{name:'HOLD на 60 минут',exact:true}).click();await t.page.getByRole('button',{name:'Подтвердить HOLD → бронь',exact:true}).waitFor();assert.equal(t.requests.filter(r=>r.path==='/api/v1/admin/pms/holds').length,1);await t.context.close();
 for(const role of ['AGENT','RECEPTION']){const t=await open(1440,'dark',role);const bar=t.page.locator('.owner-booking-bar').first();await bar.click();assert.equal(await t.page.locator('.v8-builder').count(),0);if(role==='AGENT'){assert.equal(t.requests.filter(r=>r.path.includes('/reception/reservations')).length,0);assert.equal(await bar.getAttribute('data-paid-kgs'),null);await newBooking(t.page,true);assert.equal(await t.page.getByRole('button',{name:'HOLD на 60 минут',exact:true}).count(),0);}else{const cell=t.page.locator('.owner-night-cell[data-room-code="305"]').first();await cell.focus();await t.page.keyboard.press('Enter');assert.equal(await t.page.locator('.owner-booking-modal').count(),0);}evidence.push({role,existingRestrictionsPreserved:true});await t.context.close();}
 for(const mode of ['empty','error','loading'])for(const theme of ['dark','light']){const t=await open(390,theme,'OWNER',mode);await t.page.locator(mode==='empty'?'.owner-grid-empty':mode==='error'?'.owner-grid-error':'.owner-grid-loading').waitFor();assert.equal((await metrics(t.page)).overflow,0);await t.page.screenshot({path:`${out}/${mode}-${theme}.png`});assert.deepEqual(t.errors,[]);evidence.push({mode,theme});await t.context.close();}
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({syntheticData:true,liveHotel:false,Android:false,evidence,keyboardCreate:true,interceptedCommit:true,interceptedHold:true},null,2));console.log('C3_PMS_PASS: 6 viewport/themes; booking+new forms; tooltip; keyboard create; mocked commit/HOLD; AGENT/RECEPTION; loading/empty/error');
}catch(error){fs.writeFileSync(`${out}/failure.txt`,String(error.stack||error));for(const c of browser.contexts())for(const p of c.pages()){fs.writeFileSync(`${out}/failure-metrics.json`,JSON.stringify(await metrics(p).catch(()=>null),null,2));await p.screenshot({path:`${out}/failure-${p.viewportSize()?.width}.png`,fullPage:true}).catch(()=>{});}throw error;}finally{await browser.close();}
