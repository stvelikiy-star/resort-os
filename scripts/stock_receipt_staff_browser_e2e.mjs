/** Real Staff Web proxy -> API -> PostgreSQL; inject lost POST response, reload and replay. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdtemp,rm} from 'node:fs/promises';
import {spawn,execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import path from 'node:path';
if(process.env.ALLOW_STOCK_RECEIPT_TEST_WRITES!=='1')throw new Error('Disposable CI opt-in required');
const base='http://127.0.0.1:3002';
const require=createRequire(import.meta.url);
const {chromium}=require('/tmp/marina-receipt-browser/node_modules/playwright');
const fixture=JSON.parse(await readFile('/tmp/marina-stock-receipt-fixture.json','utf8'));
const temp=await mkdtemp(path.join(tmpdir(),'marina-receipt-web-'));
const app=spawn('npm',['run','start'],{cwd:path.resolve('apps/staff'),env:process.env,stdio:'ignore',detached:true});
let browser;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
try{
 for(let i=0;i<120;i++){
  if(app.exitCode!==null)throw new Error('Disposable Staff Web exited');
  try{if((await fetch(base)).ok)break;}catch{}
  if(i===119)throw new Error('Staff Web not ready');await pause(250);
 }
 let executable;
 for(const name of ['google-chrome','google-chrome-stable','chromium','chromium-browser']){
  try{executable=execFileSync('which',[name],{encoding:'utf8'}).trim();break;}catch{}
 }
 if(!executable)throw new Error('Chrome executable unavailable');
 browser=await chromium.launch({executablePath:executable,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage();page.on('dialog',dialog=>dialog.accept());
 const login=await page.request.post(base+'/core/api/v1/auth/login',{data:{username:process.env.PROC_STORE_USERNAME,password:process.env.PROC_STORE_PASSWORD}});
 assert.equal(login.status(),200);assert.equal((await login.json()).id,fixture.store_user_id);
 async function balance(){const r=await page.request.get(base+'/core/api/v1/kitchen/stock');assert.equal(r.status(),200);return Number((await r.json()).items.find(x=>x.id===fixture.stock_item_id).balance);}
 const initial=await balance();const sent=[];let lose=true;let notifyLost;const lost=new Promise(resolve=>{notifyLost=resolve;});
 await page.route('**/core/api/v1/kitchen/stock/receipts',async route=>{
  sent.push(route.request().postDataJSON());const result=await route.fetch();assert.equal(result.status(),201);
  if(lose){lose=false;await route.abort('failed');notifyLost();}else await route.fulfill({response:result});
 });
 await page.goto(base);
 const panel=page.getByTestId('direct-stock-receipt');await panel.waitFor();
 await panel.getByLabel('Продукт прихода').selectOption(fixture.stock_item_id);
 await panel.getByLabel('Количество прихода').fill('7');
 await panel.getByRole('button',{name:'Записать приход',exact:true}).click();
 await lost;assert.equal(await balance(),initial+7);
 const pending=page.getByTestId('pending-receipt');await pending.waitFor();const first=await pending.innerText();
 await page.reload();await page.getByTestId('pending-receipt').waitFor();assert.equal(await page.getByTestId('pending-receipt').innerText(),first);
 const retry=page.getByRole('button',{name:'Проверить / повторить тот же приход',exact:true});
 await retry.click();await page.getByTestId('pending-receipt').waitFor({state:'hidden'});
 assert.equal(sent.length,2);assert.deepEqual(sent[0],sent[1]);assert.equal(await balance(),initial+7);
 await writeFile('/tmp/marina-stock-receipt-browser-result.json',JSON.stringify(sent[0]));
 console.log('STAFF WEB RECEIPT PASS: real Next proxy, server commit + dropped response, page reload, identical persisted ID/payload retry; stock +7 only');
}finally{
 await browser?.close();try{process.kill(-app.pid,'SIGTERM');}catch{}await rm(temp,{recursive:true,force:true});
}
