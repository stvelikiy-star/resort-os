import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
const {chromium}=createRequire(process.env.PLAYWRIGHT_PACKAGE||import.meta.url)('playwright');
const out='operational-visual-evidence';fs.mkdirSync(out,{recursive:true});
const dist=path.resolve('dist');
const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.png':'image/png','.ttf':'font/ttf'};
const server=createServer((req,res)=>{
  const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\/+/, '');
  let file=path.resolve(dist,relative||'index.html');
  if(!file.startsWith(dist+path.sep)){res.writeHead(403);res.end();return;}
  if(!fs.existsSync(file)||fs.statSync(file).isDirectory())file=path.join(dist,'index.html');
  res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
});
await new Promise(resolve=>server.listen(8099,'127.0.0.1',resolve));
const browser=await chromium.launch();const results=[];
try{
  for(const locale of ['ru','kg','en'])for(const theme of ['dark','light'])for(const width of [320,375,430]){
    const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
    const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));
    await page.goto(`http://127.0.0.1:8099/qa-operational?locale=${locale}&theme=${theme}&role=OWNER`);
    await page.getByTestId('owner-expenses').waitFor();await page.getByTestId('procurement-create').waitFor();
    const metrics=await page.evaluate(()=>({overflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),
      clipped:[...document.querySelectorAll('[data-testid="owner-expenses"] [dir="auto"]')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>e.textContent)}));
    assert.equal(metrics.overflow,0,JSON.stringify({locale,theme,width,metrics}));
    assert.deepEqual(metrics.clipped,[],JSON.stringify({locale,theme,width,metrics}));
    for(const section of ['qa-expenses','qa-stock','qa-procurement']){
      await page.getByTestId(section).scrollIntoViewIfNeeded();
      await page.screenshot({path:`${out}/${locale}-${theme}-${width}-${section}.png`});
    }
    assert.deepEqual(errors,[]);results.push({locale,theme,width,metrics});await context.close();
  }
  for(const role of ['MANAGER','COOK','STORE_STAFF']){
    const page=await browser.newPage({viewport:{width:320,height:900},reducedMotion:'reduce'});
    await page.goto(`http://127.0.0.1:8099/qa-operational?locale=en&theme=dark&role=${role}`);
    await page.getByTestId('procurement-create').waitFor();
    assert.equal(await page.getByTestId('owner-expenses').count(),0,role+' saw owner ledger');
    await page.getByTestId('qa-procurement').scrollIntoViewIfNeeded();
    await page.screenshot({path:`${out}/role-${role}-320.png`});await page.close();
  }
  for(const state of ['loading','empty','error']){
    const page=await browser.newPage({viewport:{width:320,height:900},reducedMotion:'reduce'});
    await page.goto(`http://127.0.0.1:8099/qa-operational?locale=en&theme=light&role=OWNER&state=${state}`);
    await page.getByTestId('owner-expenses').waitFor();
    if(state==='error')await page.getByText('QA · test connection unavailable').first().waitFor();
    await page.screenshot({path:`${out}/state-${state}-320.png`});await page.close();
  }
  const motionContext=await browser.newContext({viewport:{width:375,height:900},reducedMotion:'no-preference',recordVideo:{dir:out}});
  const motionPage=await motionContext.newPage();
  await motionPage.goto('http://127.0.0.1:8099/qa-operational?locale=en&theme=dark&role=OWNER');
  await motionPage.getByTestId('procurement-create').waitFor();
  await motionPage.getByTestId('qa-procurement').scrollIntoViewIfNeeded();
  const product=motionPage.getByRole('button',{name:/Рис.*KG/}).first();
  await product.scrollIntoViewIfNeeded();
  const box=await product.boundingBox();assert.ok(box);
  await motionPage.mouse.move(box.x+box.width/2,box.y+box.height/2);
  await motionPage.mouse.down();await motionPage.waitForTimeout(180);await motionPage.mouse.up();
  await motionPage.waitForTimeout(450);
  const category=motionPage.getByRole('button',{name:'Maintenance',exact:true});
  await category.scrollIntoViewIfNeeded();await category.click();
  await motionPage.waitForTimeout(450);await motionContext.close();
  fs.writeFileSync(`${out}/results.json`,JSON.stringify({source:'genuine React Native components exported to Expo Web, synthetic read adapters, writes disabled',sha:process.env.GITHUB_SHA||null,physicalAndroid:false,results},null,2));
  console.log('OPERATIONAL_VISUAL_PASS: 18 locale/theme/width combinations, role isolation, loading/empty/error and browser motion video');
}finally{await browser.close();server.close();}
