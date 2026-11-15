// Browser-only C3 acceptance for real compiled Folio/Payments/Group components.
// Synthetic QA Core; business mutations explicitly blocked.
import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
const { chromium } = createRequire(process.env.PLAYWRIGHT_PACKAGE || import.meta.url)("playwright");
const output = process.env.EXTENDED_PMS_EVIDENCE || "extended-pms-evidence";
fs.mkdirSync(output, { recursive: true });
const browser = await chromium.launch({headless:true});
const evidence = [];
const stay = {id:"qa-res-1",bookingNumber:"QA-808",status:"CHECKED_IN",checkIn:"2026-11-14",checkOut:"2026-11-18",adults:2,children:0,totalKgs:24000,paidKgs:12000,remainingKgs:12000,firstName:"Гость QA",phone:"+996000000000",room_code:"301",room_type_name:"Люкс",room_state:"CLEAN",schedule_segments:1,has_room_move:false};
const money = {accommodation_kgs:24000,extras_kgs:4000,grand_total_kgs:28000,paid_kgs:12000,remaining_kgs:16000,overpaid_kgs:0};
function respond(route,object,status=200){return route.fulfill({status,json:object});}
async function visit(width,theme) {
 const context=await browser.newContext({viewport:{width,height:width===390?844:1024},reducedMotion:"reduce"});
 await context.addInitScript(theme=>{localStorage.setItem("marina-admin-ui","future-luxury");localStorage.setItem("marina-fl2-theme",theme);},theme);
 const page=await context.newPage();const errors=[],writes=[];
 page.on("pageerror",e=>errors.push(String(e)));
 await page.route("**/core/api/v1/**",async route=>{
  const request=route.request(),url=new URL(request.url()),path=url.pathname.replace(/^\/core/,""),method=request.method();
  const json=value=>respond(route,value);
  if(path==="/api/v1/auth/me")return json({id:"qa-owner",role:"OWNER",username:"qa",display_name:"QA OWNER",property_code:"QA",module_permissions:["DASHBOARD","PMS","RESERVATIONS","GROUPS"],module_permissions_custom:true});
  if(path==="/api/v1/admin/hotel-setup/modules")return json({enabled_modules:["GROUPS"],hotel_name:"QA Resort (synthetic)"});
  if(path==="/api/v1/runtime/capabilities")return json({profile:"FULL",capabilities:{payment_operations:true,mkassa:false}});
  if(path==="/api/v1/admin/reception/reservations")return json({local_date:"2026-11-15",items:[stay]});
  if(path==="/api/v1/admin/agents-context/reservations")return json({agents:[],reservations:[]});
  if(path==="/api/v1/admin/booking/reservations/qa-res-1")return json({local_date:"2026-11-15",reservation:{id:stay.id,booking_number:stay.bookingNumber,status:stay.status,check_in:stay.checkIn,check_out:stay.checkOut,adults:2,children:0,total_kgs:24000,notes:null,created_at:"2026-11-01"},guest:{first_name:"Гость",last_name:"QA",phone:stay.phone},source:{channel:"DIRECT"},room:{id:"qa-room",code:"301",state:"CLEAN",room_type_name:"Люкс",segment_start:stay.checkIn,segment_end:stay.checkOut},schedule:[],finance:{total_kgs:24000,paid_kgs:12000,remaining_kgs:12000,payments:[]},room_tasks:[],audit:[]});
  if(path==="/api/v1/admin/folio/reservations/qa-res-1")return json({totals:money,charges:[{id:"qa-charge",source_type:"DINING",code:"DINING",description:"Ужин QA",amount_kgs:4000,status:"OPEN",created_at:"2026-11-15"}],payments:[{id:"qa-payment",amount_kgs:12000,method:"CASH",status:"PAID",paid_at:"2026-11-15",recorded_at:"2026-11-15"}]});
  if(path==="/api/v1/admin/pms/groups" && method==="GET")return json({items:[{id:"qa-group",code:"QA-G01",name:"Группа QA",contact_name:"Контакт QA",contact_phone:"+996000000000",check_in:"2026-11-16",check_out:"2026-11-19",status:"GUARANTEED",room_count:2,total_kgs:30000,paid_kgs:10000}]});
  if(path==="/api/v1/admin/pms/groups/availability" && method==="POST")return json({available_count:2,priced_count:2,items:[301,302].map((n,i)=>({room_id:"qa-room-"+n,code:String(n),name:"Номер QA "+n,room_type_code:"SUITE",room_type_name:"Люкс",building_or_zone:"Главный корпус",floor:"1",capacity_adults:2,capacity_children:1,children_capacity_confirmed:true,operational_state:"CLEAN",available:true,pricing:{sellable:true,total_kgs:15000+i*1000}}))});
  if(method!=="GET"){writes.push({path,method});return respond(route,{detail:"QA: mutation blocked"},403);}
  return route.continue();
 });
 await page.goto(process.env.ADMIN_URL||"http://127.0.0.1:3001",{waitUntil:"domcontentloaded"});
 await page.locator(".admin-shell-actions").waitFor();
 async function go(name){ if(width<=1100)await page.locator(".fl2-navigation-toggle").click(); await page.locator('[data-section="'+name+'"]').click(); }
 await go("RESERVATIONS");
 await page.locator(".reception-card").waitFor();
 await page.getByRole("button",{name:"Карточка",exact:true}).first().click();
 const folio=page.locator(".reservation-detail").getByText("Финансы гостя",{exact:true});await folio.waitFor();
 await page.getByText("Ужин QA",{exact:true}).waitFor();
 const folioMetrics=await page.evaluate(()=>{
  const root=[...document.querySelectorAll("section")].find(e=>e.textContent?.includes("Финансы гостя")&&e.querySelector('input[type="number"]'));
  const modal=document.querySelector(".reservation-detail");
  return {overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,modalOverflow:modal?.scrollWidth-modal?.clientWidth,small:[...(root?.querySelectorAll("button,input,select")||[])].filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height<43.9&&!(e.matches('input[type="checkbox"]')&&e.closest("label")?.getBoundingClientRect().height>=43.9)).map(e=>({label:e.textContent,height:e.getBoundingClientRect().height})),modalWidth:modal?.getBoundingClientRect().width};
 });
 assert.ok(folioMetrics.overflow<=1,JSON.stringify({width,theme,folioMetrics}));
 assert.deepEqual(folioMetrics.small,[]);
 await page.locator(".reservation-detail").screenshot({path:output+"/folio-"+width+"-"+theme+".png"});
 await page.locator(".reservation-detail").getByRole("button",{name:"Закрыть"}).click();
 await go("GROUPS");
 await page.getByRole("heading",{name:"Групповая бронь"}).waitFor();
 await page.getByRole("button",{name:"Найти свободные"}).click();
 await page.getByText("Свободные номера · 2").waitFor();
 const groupMetrics=await page.evaluate(()=>{
  const root=document.querySelector('main[class*="shell"]');
  return {overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,cardOverflow:root?.scrollWidth-root?.clientWidth,small:[...(root?.querySelectorAll("button,input,select,textarea")||[])].filter(e=>e.getClientRects().length&&e.getBoundingClientRect().height<43.9&&!(e.matches('input[type="checkbox"]')&&e.closest("label")?.getBoundingClientRect().height>=43.9)).map(e=>({label:e.textContent,height:e.getBoundingClientRect().height}))};
 });
 assert.ok(groupMetrics.overflow<=1,JSON.stringify({width,theme,groupMetrics}));
 assert.deepEqual(groupMetrics.small,[]);
 assert.ok(writes.every(write=>write.path==="/api/v1/ops/housekeeping/schedule/ensure" && write.method==="POST"),"Only the pre-existing, blocked housekeeping initialization request is permitted");
 assert.equal(writes.filter(write=>/\/folio\/|\/payments\b|\/pms\/groups\b/.test(write.path)).length,0,"No payment, folio or group mutation attempted");
 assert.deepEqual(errors,[],"No browser errors allowed");
 await page.locator('main[class*="shell"]').last().screenshot({path:output+"/group-"+width+"-"+theme+".png"});
 evidence.push({width,theme,folioMetrics,groupMetrics,writes,errors});
 await context.close();
}
try{
 for(const width of [1440,768,390])for(const theme of ["dark","light"])await visit(width,theme);
 fs.writeFileSync(output+"/results.json",JSON.stringify({syntheticData:true,visualOnly:true,evidence},null,2));
 console.log("EXTENDED_PMS_BROWSER_PASS: folio/payments and group booking 1440/768/390 Dark/Light; no business writes");
}catch(err){fs.writeFileSync(output+"/failure.txt",String(err.stack||err));throw err;}finally{await browser.close();}
