// Visual-only acceptance for Staff Shift CSS. Synthetic page, no real role/API operations.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createRequire } from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE || import.meta.url)('playwright');
const out=process.env.STAFF_VISUAL_EVIDENCE||'staff-shift-evidence';
fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true});
const results=[];
try {
 for(const width of [320,390,768,1440])for(const theme of ['dark','light']){
  const context=await browser.newContext({viewport:{width,height:width<600?844:900},colorScheme:theme,reducedMotion:'reduce'});
  const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const res=await page.goto(process.env.STAFF_QA_URL||'http://127.0.0.1:3002/qa-staff-shift',{waitUntil:'networkidle'});
  assert.equal(res?.status(),200);
  await page.locator('[data-staff-qa-fixture="true"]').waitFor();
  assert.equal(await page.locator('nextjs-portal').count(),0,'Visual acceptance must run without Next.js dev overlay');
  await page.locator('.staff-locale-switcher summary').click();
  const m=await page.evaluate(()=>{
   const buttons=[...document.querySelectorAll('.staff-locale-switcher button,.shift-modal-head button')];
   const rects=buttons.map(x=>({text:x.getAttribute('aria-label')||x.textContent,width:x.getBoundingClientRect().width,height:x.getBoundingClientRect().height}));
   const styles=getComputedStyle(document.body);
   const header=document.querySelector('.shift-head');
   return {width:window.innerWidth,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,rects,bg:styles.backgroundColor,ink:styles.color,headerOverflow:header?.scrollWidth-header?.clientWidth,
    responsiveTask:document.querySelector('.shift-task')?.getBoundingClientRect().width};
  });
  assert.ok(m.overflow<=1,'Page overflow '+JSON.stringify({width,theme,m}));
  assert.ok(m.headerOverflow<=1,'Staff header overflow '+JSON.stringify({width,theme,m}));
  assert.equal(m.rects.length,5,'Expected 4 authentic locale buttons and 1 dialog close');
  assert.ok(m.rects.every(x=>x.width>=43.9&&x.height>=43.9),'Staff target smaller than 44px '+JSON.stringify({width,theme,m}));
  await page.locator('.staff-locale-switcher summary').click();
  await page.locator('.shift-modal-head button').focus();
  const focus=await page.locator('.shift-modal-head button').evaluate(e=>({outline:getComputedStyle(e).outlineStyle,width:getComputedStyle(e).outlineWidth}));
  assert.notEqual(focus.outline,'none','Keyboard focus invisible');
  assert.deepEqual(errors,[]);
  await page.screenshot({path:`${out}/staff-${width}-${theme}.png`,fullPage:true});
  results.push({width,theme,...m,focus,errors});
  await context.close();
 }
 for(const width of [320,390,768,1440]){
  const light=results.find(x=>x.width===width&&x.theme==='light');
  const dark=results.find(x=>x.width===width&&x.theme==='dark');
  assert.notEqual(light.bg,dark.bg,'Dark/Light backgrounds not distinguished');
 }
 fs.writeFileSync(out+'/results.json',JSON.stringify({visualFixture:true,authenticatedRoleE2E:false,results},null,2));
 console.log('STAFF_SHIFT_VISUAL_PASS: 4 sizes x Dark/Light, >=44px 5 controls, no overflow, focus');
}catch(error){fs.writeFileSync(out+'/failure.txt',String(error.stack||error));throw error;}
finally{await browser.close();}
