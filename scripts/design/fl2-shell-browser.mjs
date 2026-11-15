// Isolated C1 browser checks against QA-only mock Core. Never connect this to a live hotel.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const { chromium } = createRequire(process.env.PLAYWRIGHT_PACKAGE || import.meta.url)('playwright');
const out=process.env.C1_EVIDENCE || 'c1-evidence'; fs.mkdirSync(out,{recursive:true});
const base=process.env.ADMIN_URL || 'http://127.0.0.1:3001';
const all=['DASHBOARD','PMS','RATES','GROUPS','REQUESTS','AGENTS','RESERVATIONS','SERVICES','DINING','SERVICE_SETTINGS','GUESTS','OFFERS','MARKETING','GROWTH','FINANCE','REPORTS','CONTENT','ROOM_QR','POINT_QR','INBOX','WHATSAPP','OPS','STAFF','SETTINGS','HOTEL_RULES','CHANNELS'];
const gated=['GROUPS','AGENTS','MARKETING','DINING','OFFERS','GROWTH','CONTENT','ROOM_QR','POINT_QR','INBOX'];
const browser=await chromium.launch({headless:true}); const evidence=[];
async function open({width=1440,theme='dark',role='OWNER',permissions=all,enabled=gated,legacy=false}={}) {
 const context=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:'reduce'});
 await context.addInitScript(({theme,legacy})=>{localStorage.setItem('marina-admin-ui',legacy?'legacy':'future-luxury');localStorage.setItem('marina-fl2-theme',theme);},{theme,legacy});
 const page=await context.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(String(e))); page.on('console',m=>{if(m.type()==='error'&&!/404/.test(m.text())) errors.push(m.text());});
 await page.route('**/core/api/v1/auth/me',r=>r.fulfill({json:{id:'qa-user',username:'qa',display_name:'Сотрудник QA',role,property_code:'QA',module_permissions:permissions,module_permissions_custom:true}}));
 await page.route('**/core/api/v1/admin/hotel-setup/modules',r=>r.fulfill({json:{enabled_modules:enabled,hotel_name:'QA Resort (synthetic)'}}));
 await page.goto(base,{waitUntil:'networkidle'}); await page.waitForSelector('.admin-shell-actions');
 await page.waitForTimeout(150);
 return {page,context,errors};
}
async function metrics(page) {
 return page.evaluate(()=>({overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth, small:[...document.querySelectorAll('[data-fl2-shell] button')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden').filter(e=>e.getBoundingClientRect().height<43.9).map(e=>e.textContent)}));
}
try {
 for(const width of [1440,768,390]) for(const theme of ['dark','light']) {
  const {page,context,errors}=await open({width,theme});
  await page.waitForSelector('[data-fl2-owner="true"]');
  assert.equal(await page.locator('.fl2-nav-group').count(),6);
  assert.equal(await page.locator('[data-section]').count(),26);
  const closed=await metrics(page); assert.equal(closed.overflow,0); assert.deepEqual(closed.small,[]);
  assert.equal(await page.locator('.fl2-assistant-dock>button').evaluate(e=>getComputedStyle(e).position),'static');
  await page.screenshot({path:`${out}/owner-${width}-${theme}.png`});
  if(width<1101) {
   const toggle=page.locator('.fl2-navigation-toggle'); await toggle.click();
   assert.equal(await toggle.getAttribute('aria-expanded'),'true');
   const opened=await metrics(page);assert.equal(opened.overflow,0);assert.deepEqual(opened.small,[]);
   await page.screenshot({path:`${out}/menu-${width}-${theme}.png`});
   await page.locator('[data-section="REPORTS"]').focus();await page.keyboard.press('Escape');
   assert.equal(await toggle.getAttribute('aria-expanded'),'false');assert.equal(await toggle.evaluate(e=>e===document.activeElement),true);
   await toggle.click();
  }
  assert.deepEqual(errors,[]);
  await page.locator('[data-section="REPORTS"]').click();
  assert.equal(await page.locator('[aria-current="page"]').getAttribute('data-section'),'REPORTS');
  await page.locator('.fl2-current-label').getByText('Отчёты / Аналитика',{exact:true}).waitFor();
  if(width<1101)assert.equal(await page.locator('.fl2-navigation-toggle').getAttribute('aria-expanded'),'false');
  evidence.push({width,theme,closed,groups:6,tabs:26,selection:'REPORTS',errors});await context.close();
 }
 // Exact server-granted sets, including staff/custom roles; no role-to-permission inference in the shell.
 for(const role of ['OWNER','MANAGER','RECEPTION','AGENT','MAID','TECHNICIAN','COOK','WAITER','STORE_STAFF']) {
  const permissions=['DASHBOARD','PMS','DINING','GROUPS','FINANCE'];
  const {page,context}=await open({role,permissions,enabled:['DINING']});
  assert.deepEqual((await page.locator('[data-section]').evaluateAll(es=>es.map(e=>e.dataset.section))).sort(),['DASHBOARD','DINING','FINANCE','PMS']);
  evidence.push({role,grants:permissions,enabled:['DINING'],visible:['DASHBOARD','DINING','FINANCE','PMS']});await context.close();
 }
 const empty=await open({permissions:[]});assert.equal(await empty.page.locator('[data-section]').count(),0);await empty.page.getByText('Доступ к разделам отключён.',{exact:true}).waitFor();await empty.context.close();
 const zoom=await open({width:1440});await zoom.page.evaluate(()=>document.body.style.zoom='200%');assert.equal((await metrics(zoom.page)).overflow,0);await zoom.page.screenshot({path:`${out}/owner-css-zoom-200.png`});await zoom.context.close();
 const legacy=await open({legacy:true});assert.equal(await legacy.page.locator('.fl2-grouped-navigation').count(),0);assert.equal(await legacy.page.locator('.admin-tabs').count(),1);await legacy.page.screenshot({path:`${out}/legacy-1440.png`});await legacy.context.close();
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({syntheticData:true,physicalAndroid:false,zoom:'CSS zoom 200%, not native browser zoom',evidence},null,2));
 console.log('C1_BROWSER_PASS: 6 theme/viewports; 9 explicit role grants; empty grants; keyboard Escape; selection; 44px targets; no horizontal overflow; CSS zoom; Legacy');
} finally { await browser.close(); }
