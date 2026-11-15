// C2 QA against the isolated synthetic Core, not live hotel or Android evidence.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE || import.meta.url)('playwright');
const out=process.env.C2_EVIDENCE || 'c2-evidence';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch();const evidence=[];
const root='.dashboard-shell[data-fl2-owner="true"]';
const blocks=`${root} .owner-executive,${root} .owner-v2`;
async function open(width,theme,mode='ready') {
 const context=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:'reduce'});
 await context.addInitScript(({theme,mode})=>{localStorage.setItem('marina-admin-ui',mode==='legacy'?'legacy':'future-luxury');localStorage.setItem('marina-fl2-theme',theme);},{theme,mode});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error'&&!/404|503/.test(m.text()))errors.push(m.text());});
 if(mode==='error'||mode==='loading')await page.route('**/core/api/v1/admin/intelligence/**',async route=>{
  if(!/owner-brief|operations-performance/.test(route.request().url()))return route.continue();
  if(mode==='error')return route.fulfill({status:503,json:{detail:'QA fixture: service unavailable'}});
  await new Promise(r=>setTimeout(r,5000));if(!page.isClosed())await route.continue().catch(()=>{});
 });
 if(mode==='empty')await page.route('**/core/api/v1/admin/intelligence/owner-brief**',async route=>{
  const response=await route.fetch();const body=await response.json();body.actions=[];body.forward.daily=[];
  for(const k of ['next_7_days','next_30_days'])for(const p of Object.keys(body.forward[k]))if(typeof body.forward[k][p]==='number')body.forward[k][p]=0;
  return route.fulfill({json:body});
 });
 await page.goto(process.env.ADMIN_URL||'http://127.0.0.1:3001',{waitUntil:mode==='loading'?'domcontentloaded':'networkidle'});
 await page.waitForSelector(mode==='legacy'?'.admin-tabs':root);
 return {page,context,errors};
}
async function inspect(page) {
 return page.evaluate((selector)=>{
  const nodes=[...document.querySelectorAll(selector)];
  const text=nodes.flatMap(n=>[n,...n.querySelectorAll('*')]).filter(e=>e.getClientRects().length&&[...e.childNodes].some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim()));
  const small=text.filter(e=>parseFloat(getComputedStyle(e).fontSize)<11.99).map(e=>({text:e.textContent.slice(0,70),font:getComputedStyle(e).fontSize}));
  const buttons=nodes.flatMap(n=>[...n.querySelectorAll('button')]);
  const smallButtons=buttons.filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height<43.9).map(e=>e.textContent);
  // Flat RGBA compositing model; background images/gradients are not a WCAG certification.
  const color=s=>{const m=s.match(/[\d.]+/g)?.map(Number);return m&&m.length>=3?[m[0],m[1],m[2],m[3]??1]:[0,0,0,0];};
  const over=(fg,bg)=>fg.slice(0,3).map((v,i)=>v*fg[3]+bg[i]*(1-fg[3]));
  const bg=e=>{const chain=[];for(let p=e;p;p=p.parentElement)chain.unshift(p);let rgb=[255,255,255];for(const p of chain)rgb=over(color(getComputedStyle(p).backgroundColor),rgb);return rgb;};
  const lum=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  const contrast=text.map(e=>{const b=bg(e),c=over(color(getComputedStyle(e).color),b);const l=[lum(c),lum(b)].sort((a,b)=>a-b);return {text:e.textContent.slice(0,70),ratio:(l[1]+.05)/(l[0]+.05)};});
  return {overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,blocks:nodes.length,buttons:buttons.length,small,smallButtons,contrastFailures:contrast.filter(c=>c.ratio<4.5),minimumContrast:Math.min(...contrast.map(c=>c.ratio)),textNodes:text.length};
 },blocks);
}
try {
 for(const width of [1440,768,390])for(const theme of ['dark','light']) {
  const {page,context,errors}=await open(width,theme);await page.locator('.owner-v2 .owner-forward-kpis').waitFor();await page.locator('.owner-executive-grid').first().waitFor();
  if(width===390) {
   const mobile=await page.locator('.owner-v2-head').evaluate(node=>{
    const heading=node.querySelector(':scope > div:first-child'),actions=node.querySelector('.owner-v2-actions');
    const h=heading?.getBoundingClientRect(),a=actions?.getBoundingClientRect();
    return {gap:h&&a?a.top-h.bottom:Infinity,buttons:actions?.querySelectorAll('button').length};
   });
   assert.ok(mobile.gap>=0&&mobile.gap<=24,`Owner mobile header gap: ${JSON.stringify(mobile)}`);
   assert.equal(mobile.buttons,2,'Snapshot and refresh controls must remain');
  }
  const m=await inspect(page);assert.equal(m.blocks,3);assert.equal(m.overflow,0);assert.deepEqual(m.small,[]);assert.deepEqual(m.smallButtons,[]);assert.deepEqual(m.contrastFailures,[]);assert.equal(m.buttons,5);assert.deepEqual(errors,[]);
  await page.screenshot({path:`${out}/owner-${width}-${theme}-full.png`,fullPage:true});
  await page.screenshot({path:`${out}/owner-${width}-${theme}-fold.png`});
  const region=page.locator('.owner-forward-chart');await region.focus();await page.keyboard.press('ArrowRight');
  if(width===390)assert.ok(await region.evaluate(e=>e.scrollWidth>e.clientWidth));
  evidence.push({width,theme,metrics:m,errors});await context.close();
 }
 const actions=await open(1440,'dark');let reads=0;actions.page.on('request',r=>{if(r.method()==='GET'&&r.url().includes('/admin/intelligence/owner-brief'))reads++;});
 await actions.page.locator('.owner-executive-grid').first().waitFor();
 await actions.page.locator('.owner-executive').first().getByRole('button',{name:'Обновить',exact:true}).click();await actions.page.waitForTimeout(300);assert.ok(reads>0);
 await actions.page.evaluate(()=>{window.print=()=>{window.__c2Printed=true;};});await actions.page.getByRole('button',{name:'Печать / PDF',exact:true}).click();assert.equal(await actions.page.evaluate(()=>window.__c2Printed),true);
 let captures=0;await actions.page.route('**/snapshots/capture**',r=>{captures++;return r.fulfill({json:{}});});await actions.page.getByRole('button',{name:'Контрольный снимок',exact:true}).click();await actions.page.waitForTimeout(200);assert.equal(captures,1);await actions.context.close();
 for(const mode of ['error','loading','empty'])for(const theme of ['dark','light']) {
  const {page,context,errors}=await open(390,theme,mode);
  if(mode==='error'){await page.locator('.owner-v2 .error-box').waitFor();assert.equal(await page.locator(`${root} .owner-executive .error-box,${root} .owner-v2 .error-box`).count(),3);}
  if(mode==='loading')await page.locator('.owner-v2-loading').waitFor();
  if(mode==='empty')await page.locator('.owner-v2 .owner-empty').first().waitFor();
  const m=await inspect(page);assert.equal(m.overflow,0);assert.deepEqual(m.smallButtons,[]);assert.deepEqual(errors,[]);await page.screenshot({path:`${out}/${mode}-390-${theme}.png`,fullPage:true});evidence.push({mode,theme,metrics:m});await context.close();
 }
 const legacy=await open(1440,'dark','legacy');await legacy.page.locator('.owner-v2 .owner-forward-kpis').waitFor();assert.equal(await legacy.page.locator('.owner-v2').evaluate(e=>getComputedStyle(e).color),'rgb(19, 41, 67)');await legacy.context.close();
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({syntheticData:true,physicalAndroid:false,contrastModel:'flat RGBA surfaces, not full WCAG certification',evidence,actions:{refresh:true,print:true,capture:true},legacy:true},null,2));
 console.log('C2_OWNER_THEME_PASS: 6 view/theme combinations; old analytics readable in both themes; 5 controls >=44px; no text under 12px; flat surface contrast >=4.5; loading/error/empty; refresh/print/capture preserved');
} catch(error) {
 fs.writeFileSync(`${out}/failure.txt`,String(error.stack||error));
 for(const context of browser.contexts())for(const page of context.pages()) {
  fs.writeFileSync(`${out}/failure-metrics.json`,JSON.stringify(await inspect(page).catch(()=>null),null,2));await page.screenshot({path:`${out}/failure-${page.viewportSize()?.width}.png`,fullPage:true}).catch(()=>{});
 }
 throw error;
} finally {await browser.close();}
