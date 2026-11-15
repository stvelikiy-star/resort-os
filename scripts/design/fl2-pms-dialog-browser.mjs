// Isolated browser proof only. Every PMS response/write is synthetic and intercepted here.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE||import.meta.url)('playwright');
const out=process.env.DIALOG_EVIDENCE||'dialog-evidence';fs.mkdirSync(out,{recursive:true});
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
// Additional dialog cases reuse the same synthetic grid but never contact a live property.
async function configure(t,mode='ready'){
 const {page,requests}=t;const history=mode==='history';let state='CLEAN';
 const start=date(history?-2:1),end=date(history?2:5),status=history?'CHECKED_IN':'GUARANTEED';
 const reservation={id:'res-0',booking_number:'QA-100',status,check_in:start,check_out:end,stored_total_kgs:20000,version:'qa-v1'};
 await page.route('**/core/api/v1/admin/pms/reservations/*/schedule**',async r=>{
  const p=new URL(r.request().url()).pathname,body=r.request().postDataJSON()||{};requests.push({method:r.request().method(),path:p,body});const json=x=>r.fulfill({json:x});
  if(p.endsWith('/schedule/preview')){
   if(mode==='busy')await new Promise(resolve=>setTimeout(resolve,1800));
   return json({reservation,proposed_schedule:body.segments.map(s=>({...s,room_code:rooms.find(r=>r.id===s.room_id).code})),proposed_check_in:body.segments[0].start,proposed_check_out:body.segments.at(-1).end,can_commit:mode!=='conflict',category_changed:false,conflicts:mode==='conflict'?[{room_code:'305',block_type:'RESERVATION',start,end,booking_number:'QA-CONFLICT'}]:[],pricing:{sellable:true,suggested_total_kgs:24000,stored_total_kgs:20000,delta_kgs:4000,stored_total_will_change_on_commit:false}});
  }
  if(p.endsWith('/schedule/commit'))return mode==='stale'?r.fulfill({status:409,json:{detail:{code:'VERSION_CONFLICT'}}}):json({});
  if(mode==='schedule-error')return r.fulfill({status:503,json:{detail:'QA: график временно недоступен'}});
  return json({reservation,guest:{name:'Тестовый гость QA',phone:'+996000000000'},schedule:[{inventory_block_id:'block-0',room_id:'room-0',room_code:'301',room_state:'CLEAN',room_type_code:'SUITE',room_type_name:'Люкс',start,end}],local_today:date(0)});
 });
 await page.route('**/core/api/v1/admin/rooms/**',async r=>{
  const p=new URL(r.request().url()).pathname;
  if(p.endsWith('/wayfinding'))return r.fulfill({json:{wayfinding:{latitude:null,longitude:null,parking_label:'QA парковка',directions:'Тестовый маршрут',walkthrough_video_url:'',map_url:null}}});
  if(mode==='room-error')return r.fulfill({status:503,json:{detail:'QA: номер временно недоступен'}});
  if(mode==='room-loading')await new Promise(resolve=>setTimeout(resolve,2500));
  return r.fulfill({json:{room:{...rooms[0],operational_state:state,name:'Люкс QA',capacity_adults:2,capacity_children:1,area:'42',notes:'Тестовые данные для визуальной проверки',updated_at:new Date().toISOString()},blocks:[{id:'block-0',type:'RESERVATION',start,end,active:true,reservation:{id:'res-0',booking_number:'QA-100',status,guest_name:'Тестовый гость QA'}}],tasks:[{id:'task-qa',type:'HOUSEKEEPING',status:'OPEN',priority:'NORMAL',title:'Подготовить номер к заезду (QA)',assigned_to:'Сотрудник QA',created_at:new Date().toISOString(),updated_at:new Date().toISOString()}],truth:'QA'}});
 });
 await page.route('**/core/api/v1/ops/rooms/*/state',async r=>{const body=r.request().postDataJSON();requests.push({method:r.request().method(),path:new URL(r.request().url()).pathname,body});await new Promise(resolve=>setTimeout(resolve,1200));state=body.state;return r.fulfill({json:{}});});
 return {start,end};
}
async function dialogLegibility(page,selector='.room-detail-modal'){return page.locator(selector).evaluate(root=>{
 const nodes=[root,...root.querySelectorAll('*')].filter(e=>e.getClientRects().length&&[...e.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim()));
 const rgba=s=>{const a=s.match(/[\d.]+/g)?.map(Number);return a&&a.length>=3?[a[0],a[1],a[2],a[3]??1]:[0,0,0,0];};
 const over=(a,b)=>a.slice(0,3).map((v,i)=>v*a[3]+b[i]*(1-a[3]));
 const background=e=>{const chain=[];for(let p=e;p;p=p.parentElement)chain.unshift(p);let c=[255,255,255];for(const n of chain)c=over(rgba(getComputedStyle(n).backgroundColor),c);return c;};
 const lum=a=>a.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const ratios=nodes.map(e=>{const b=background(e),c=over(rgba(getComputedStyle(e).color),b),l=[lum(c),lum(b)].sort((a,b)=>a-b);return {text:e.textContent.slice(0,70),ratio:(l[1]+.05)/(l[0]+.05)};});
 return {small:nodes.filter(e=>parseFloat(getComputedStyle(e).fontSize)<11.99).map(e=>({text:e.textContent.slice(0,70),size:getComputedStyle(e).fontSize})),failures:ratios.filter(r=>r.ratio<4.5),minimum:Math.min(...ratios.map(r=>r.ratio))};
 });}
async function checkFocus(page,selector){
 await page.waitForFunction(selector=>document.querySelector(selector)?.contains(document.activeElement),selector);
 assert.equal(await page.evaluate(()=>document.body.style.overflow),'hidden');
 const ends=await page.locator(selector).evaluate(e=>{const f=[...e.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')].filter(e=>e.tabIndex>=0&&!e.matches(':disabled')&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');f.at(-1).focus();return f.length;});assert.ok(ends>0);
 await page.keyboard.press('Tab');assert.equal(await page.locator(selector).evaluate(e=>{const f=[...e.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')].filter(e=>e.tabIndex>=0&&!e.matches(':disabled')&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');return document.activeElement===f[0];}),true);
 await page.keyboard.press('Shift+Tab');assert.equal(await page.locator(selector).evaluate(e=>{const f=[...e.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')].filter(e=>e.tabIndex>=0&&!e.matches(':disabled')&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');return document.activeElement===f.at(-1);}),true);
 await page.locator('[data-section="PMS"]').evaluate(e=>e.focus());assert.equal(await page.locator(selector).evaluate(e=>e.contains(document.activeElement)),true);
}
async function escapeAndReturn(page,selector,opener){await page.keyboard.press('Escape');await page.locator(selector).waitFor({state:'detached'});await page.waitForFunction(selector=>document.activeElement?.matches(selector),opener);assert.notEqual(await page.evaluate(()=>document.body.style.overflow),'hidden');}
async function schedule(t){const bar=t.page.locator('.owner-booking-bar').first();await bar.scrollIntoViewIfNeeded();await bar.focus();await t.page.keyboard.press('Enter');await t.page.locator('.v8-segment-card').first().waitFor();return bar;}
async function splitAndMove(page){await page.getByRole('button',{name:/Разрезать/}).first().click();assert.equal(await page.locator('.v8-segment-card').count(),2);await page.locator('.v8-segment-room select').nth(1).selectOption('room-4');}
try {
 for(const width of [1440,768,390])for(const theme of ['dark','light']){
  const t=await open(width,theme),{page}=t;await configure(t);
  await newBooking(page,true);assert.equal(await page.locator('.owner-booking-head button').evaluate(e=>e===document.activeElement),true);await checkFocus(page,'.owner-booking-modal');await escapeAndReturn(page,'.owner-booking-modal','.owner-night-cell[data-room-code="305"]');
  const room=page.locator('.owner-room-label').first();await room.scrollIntoViewIfNeeded();await room.focus();await page.keyboard.press('Enter');await page.locator('.room-detail-facts').waitFor();await checkFocus(page,'.room-detail-modal');const m=await metrics(page,'.room-detail-modal');m.legibility=await dialogLegibility(page);assert.deepEqual(m.legibility.small,[]);assert.deepEqual(m.legibility.failures,[]);assert.equal(m.overflow,0);assert.deepEqual(m.smallControls,[]);
  await page.locator('.room-detail-modal').evaluate(e=>{e.scrollTop=0;});await page.screenshot({path:`${out}/room-${width}-${theme}.png`});await page.getByRole('button',{name:/Брони и блоки/}).click();await page.locator('.room-detail-item').getByText('QA-100',{exact:false}).waitFor();await page.screenshot({path:`${out}/room-blocks-${width}-${theme}.png`});
  await escapeAndReturn(page,'.room-detail-modal','.owner-room-label');
  await schedule(t);const openerHandle=await page.locator('.owner-booking-bar').first().elementHandle();await checkFocus(page,'.v8-builder');await splitAndMove(page);assert.equal(await page.getByRole('button',{name:'Подтвердить и сохранить график',exact:true}).count(),0);
  await page.getByRole('button',{name:'Проверить в MARINA SMART',exact:true}).click();await page.locator('.v8-preview').waitFor();await page.locator('.v8-preview').scrollIntoViewIfNeeded();await page.screenshot({path:`${out}/split-${width}-${theme}.png`});const sm=await metrics(page,'.v8-builder');sm.legibility=await dialogLegibility(page,'.v8-builder');assert.deepEqual(sm.legibility.small,[]);assert.deepEqual(sm.legibility.failures,[]);assert.equal(sm.overflow,0);assert.deepEqual(sm.smallControls,[]);
  const preview=t.requests.filter(r=>r.path.endsWith('/schedule/preview')).at(-1);assert.equal(preview.body.segments.length,2);assert.equal(preview.body.segments[0].end,preview.body.segments[1].start);assert.equal(preview.body.segments[1].room_id,'room-4');
  await page.getByRole('button',{name:'Подтвердить и сохранить график',exact:true}).click();await page.locator('.v8-builder').waitFor({state:'detached'});const commit=t.requests.filter(r=>r.path.endsWith('/schedule/commit')).at(-1);assert.deepEqual(commit.body.segments,preview.body.segments);assert.equal(commit.body.expected_version,'qa-v1');const openerRemoved=!(await openerHandle.evaluate(e=>e.isConnected));if(openerRemoved)await page.waitForFunction(()=>document.activeElement?.matches('.owner-grid-scroll'));else assert.equal(await openerHandle.evaluate(e=>e===document.activeElement),true);
  assert.deepEqual(t.errors,[]);evidence.push({width,theme,room:m,schedule:sm,focusLoop:true,escapeAndReturn:true,splitPreviewCommit:true,errors:t.errors});await t.context.close();
 }
 for(const theme of ['dark','light'])for(const mode of ['room-error','room-loading','schedule-error']){
  const t=await open(390,theme);await configure(t,mode);
  if(mode.startsWith('room-')){await t.page.locator('.owner-room-label').first().focus();await t.page.keyboard.press('Enter');await t.page.locator(mode==='room-error'?'.room-detail-modal .error-box':'.room-detail-modal .loading').waitFor();await checkFocus(t.page,'.room-detail-modal');await t.page.screenshot({path:`${out}/${mode}-${theme}.png`});await escapeAndReturn(t.page,'.room-detail-modal','.owner-room-label');}
  else{await t.page.locator('.owner-booking-bar').first().focus();await t.page.keyboard.press('Enter');await t.page.locator('.v8-builder-error').waitFor();await checkFocus(t.page,'.v8-builder');await t.page.screenshot({path:`${out}/${mode}-${theme}.png`});await escapeAndReturn(t.page,'.v8-builder','.owner-booking-bar');}
  assert.deepEqual(t.errors,[]);evidence.push({mode,theme,loadingErrorClosable:true});await t.context.close();
 }
 const h=await open(1440,'dark');await configure(h,'history');await schedule(h);assert.equal(await h.page.locator('.v8-segment-room select').first().isDisabled(),true);await h.page.getByRole('button',{name:'Отделить с сегодня',exact:true}).click();assert.equal(await h.page.locator('.v8-segment-card').count(),2);assert.equal(await h.page.locator('.v8-segment-room select').first().isDisabled(),true);assert.equal(await h.page.locator('.v8-segment-room select').nth(1).isDisabled(),false);await h.page.locator('.v8-segment-room select').nth(1).selectOption('room-4');await h.page.getByRole('button',{name:'Проверить в MARINA SMART',exact:true}).click();await h.page.locator('.v8-preview').waitFor();const hist=h.requests.filter(r=>r.path.endsWith('/schedule/preview')).at(-1).body.segments;assert.equal(hist[0].start,date(-2));assert.equal(hist[0].end,date(0));assert.equal(hist[0].room_id,'room-0');assert.equal(hist[1].start,date(0));await h.page.screenshot({path:`${out}/protected-history.png`});evidence.push({mode:'history',pastProtected:true});await h.context.close();
 for(const mode of ['conflict','stale','busy']){
  const t=await open(390,'light');await configure(t,mode);await schedule(t);await splitAndMove(t.page);await t.page.getByRole('button',{name:'Проверить в MARINA SMART',exact:true}).click();
  if(mode==='busy'){await t.page.getByRole('button',{name:'Проверяю…',exact:true}).waitFor();await t.page.keyboard.press('Escape');assert.equal(await t.page.locator('.v8-builder').count(),1);assert.equal(await t.page.locator('.v8-builder').evaluate(e=>e.contains(document.activeElement)),true);}
  await t.page.locator('.v8-preview').waitFor();const button=t.page.getByRole('button',{name:'Подтвердить и сохранить график',exact:true});
  if(mode==='conflict'){assert.equal(await button.isDisabled(),true);assert.equal(t.requests.filter(r=>r.path.endsWith('/schedule/commit')).length,0);}
  if(mode==='stale'){await button.click();await t.page.locator('.v8-builder-error').waitFor();assert.equal(await t.page.locator('.v8-builder').count(),1);assert.equal(await t.page.locator('.v8-builder').evaluate(e=>e.contains(document.activeElement)),true);}
  const lm=await dialogLegibility(t.page,'.v8-builder');assert.deepEqual(lm.small,[]);assert.deepEqual(lm.failures,[]);await t.page.screenshot({path:`${out}/${mode}-preview.png`});evidence.push({mode,guardPreserved:true});await t.context.close();
 }
 const move=await open();await configure(move);await schedule(move);await move.page.locator('.v8-segment-room select').first().selectOption('room-5');await move.page.locator('.v8-builder-dates input').nth(1).fill(date(7));await move.page.getByRole('button',{name:'Проверить в MARINA SMART',exact:true}).click();await move.page.locator('.v8-preview').waitFor();const mp=move.requests.filter(r=>r.path.endsWith('/schedule/preview')).at(-1).body.segments;assert.equal(mp.length,1);assert.equal(mp[0].room_id,'room-5');assert.equal(mp[0].end,date(7));await move.context.close();evidence.push({mode:'whole-stay-room-and-date-preview',preserved:true});
 const merge=await open();await configure(merge);await schedule(merge);await merge.page.getByRole('button',{name:/Разрезать/}).first().click();await merge.page.getByRole('button',{name:'← к предыдущему',exact:true}).click();assert.equal(await merge.page.locator('.v8-segment-card').count(),1);await merge.context.close();evidence.push({mode:'merge-segments',preserved:true});
 const ready=await open();await configure(ready);await ready.page.locator('.owner-room-label').first().click();await ready.page.locator('.room-readiness-actions').waitFor();await ready.page.getByRole('button',{name:'Уборка Нужна подготовка',exact:true}).click();await ready.page.keyboard.press('Escape');assert.equal(await ready.page.locator('.room-detail-modal').count(),1);await ready.page.locator('.room-detail-modal .content-message.success').waitFor();assert.equal(ready.requests.find(r=>r.path.endsWith('/state')).body.state,'DIRTY');await ready.context.close();evidence.push({mode:'room-busy',escapeBlockedUntilResponse:true});
 const legacy=await open(1440,'dark','OWNER','legacy');await configure(legacy);await schedule(legacy);await legacy.page.keyboard.press('Escape');assert.equal(await legacy.page.locator('.v8-builder').count(),1);await legacy.context.close();evidence.push({mode:'legacy',focusBehaviorUnchanged:true});
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({syntheticData:true,physicalAndroid:false,evidence,mutationsIntercepted:true},null,2));console.log('PMS_DIALOG_BROWSER_PASS: 3 dialogs; focus entry/Tab/ShiftTab/Escape/return/scroll restore; room/error/loading; split/move/date/merge/history; preview/version/conflict/busy guards; 6 viewport/themes; Legacy');
}catch(e){fs.writeFileSync(`${out}/failure.txt`,String(e.stack||e));for(const c of browser.contexts())for(const p of c.pages()){fs.writeFileSync(`${out}/failure-state.json`,JSON.stringify(await p.evaluate(()=>({active:document.activeElement?.outerHTML,dialogs:[...document.querySelectorAll('[role="dialog"]')].map(e=>({name:e.getAttribute('aria-label'),text:e.textContent.slice(0,1500)}))})).catch(()=>null),null,2));await p.screenshot({path:`${out}/failure-${p.viewportSize()?.width}.png`,fullPage:true}).catch(()=>{});}throw e;}finally{await browser.close();}
