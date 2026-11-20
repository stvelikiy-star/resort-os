// Palette proof against real production DOM with synthetic OWNER data. Not live hotel evidence.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE||import.meta.url)('playwright');
const spec=JSON.parse(fs.readFileSync('docs/design/FL2_WEB_REFERENCE_PALETTE.json','utf8'));
const out='foundation-evidence';fs.mkdirSync(out,{recursive:true});const browser=await chromium.launch();const evidence=[];
const rgb=h=>`rgb(${[1,3,5].map(i=>parseInt(h.slice(i,i+2),16)).join(', ')})`;
async function inspect(page){return page.evaluate(()=>{
 const style=getComputedStyle(document.documentElement),vars={};
 for(const key of ['bg','surface','accent','info','ink','accent-ink','chart-line'])vars[key]=style.getPropertyValue('--mx-'+key).trim();
 const resolve=variable=>{const e=document.createElement('span');e.style.color=`var(${variable})`;document.body.append(e);const c=getComputedStyle(e).color;e.remove();return c;};
 const bridge=Object.fromEntries(['--fl2-bg','--fl2-accent','--fl2-feedback-text','--fl2-feedback-muted'].map(k=>[k,resolve(k)]));
 return {vars,bridge,bodyColor:getComputedStyle(document.body).color,bodyBackground:getComputedStyle(document.body).backgroundColor,scheme:style.colorScheme,overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,button:document.querySelector('.fl2-nav-group [aria-current="page"]')?{color:getComputedStyle(document.querySelector('.fl2-nav-group [aria-current="page"]')).color,background:getComputedStyle(document.querySelector('.fl2-nav-group [aria-current="page"]')).backgroundColor}:null};
});}
try{
 for(const width of [1440,768,390])for(const theme of ['dark','light']){
  const c=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:'reduce'});await c.addInitScript(theme=>{localStorage.setItem('marina-admin-ui','future-luxury');if(!localStorage.getItem('marina-fl2-theme'))localStorage.setItem('marina-fl2-theme',theme);},theme);
  const p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(String(e)));await p.goto(process.env.ADMIN_URL||'http://127.0.0.1:3001',{waitUntil:'networkidle'});await p.locator('.owner-v2 .owner-forward-kpis').waitFor();
  const m=await inspect(p);for(const [key,value]of Object.entries(m.vars))assert.equal(value,spec[theme][key],`${theme}/${key}`);assert.equal(m.overflow,0);assert.equal(m.scheme,theme);assert.equal(m.bodyColor,rgb(spec[theme].ink));assert.equal(m.bodyBackground,rgb(spec[theme].bg));assert.equal(m.bridge['--fl2-bg'],rgb(spec[theme].bg));assert.equal(m.bridge['--fl2-accent'],rgb(spec[theme].accent));assert.equal(m.button.color,rgb(spec[theme]['accent-ink']));assert.equal(m.button.background,rgb(spec[theme].accent));assert.deepEqual(errors,[]);
  await p.screenshot({path:`${out}/owner-reference-${width}-${theme}.png`,fullPage:true});
  await p.locator('.fl2-account-settings summary').click();const opposite=theme==='dark'?'light':'dark';await p.getByRole('button',{name:opposite==='light'?'Светлая тема':'Тёмная тема',exact:true}).click();await p.waitForFunction(t=>document.documentElement.dataset.fl2Theme===t,opposite);const switched=await inspect(p);assert.equal(switched.vars.accent,spec[opposite].accent);assert.equal(switched.scheme,opposite);await p.reload({waitUntil:'networkidle'});assert.equal((await inspect(p)).vars.bg,spec[opposite].bg);
  evidence.push({width,theme,metrics:m,liveThemeSwitch:true,persisted:true,errors});await c.close();
 }
 fs.writeFileSync(`${out}/results.json`,JSON.stringify({source:spec.source,syntheticData:true,scope:'Web shared foundation; Mobile unchanged',evidence},null,2));console.log('REFERENCE_BROWSER_PASS: exact runtime palette and bridge colors; body/nav consistency; live theme switch and persistence; 6 viewport/themes; 0 page overflow');
}catch(e){fs.writeFileSync(`${out}/failure.txt`,String(e.stack||e));for(const c of browser.contexts())for(const p of c.pages()){fs.writeFileSync(`${out}/failure-metrics.json`,JSON.stringify(await inspect(p).catch(()=>null),null,2));await p.screenshot({path:`${out}/failure-${p.viewportSize()?.width}.png`,fullPage:true}).catch(()=>{});}throw e;}finally{await browser.close();}
