import assert from "node:assert/strict";
import { chromium } from "playwright";

// Real Chromium -> Next rewrite -> canonical FastAPI -> disposable PostgreSQL.
// No request interception or mocked responses.
const BASE=process.env.MARINA_SHARED_BROWSER_URL||"";
const url=new URL(BASE);
assert(["localhost","127.0.0.1"].includes(url.hostname));
assert.equal(process.env.MARINA_SHARED_BROWSER_CI_CONFIRM,"DISPOSABLE_TWO_HOTEL_BROWSER_CI");
assert.equal(process.env.MARINA_SHARED_THIRD_HOTEL_CONFIRM,
  "DISPOSABLE_THIRD_HOTEL_ADDITIVE_CI_ONLY");
const password=process.env.MARINA_SHARED_BROWSER_CI_PASSWORD;
assert(password?.startsWith("synthetic-ci-only-"));
const browser=await chromium.launch({headless:true});
try {
  const ctx=await browser.newContext({viewport:{width:390,height:844}});
  const page=await ctx.newPage();
  await page.goto(BASE,{waitUntil:"domcontentloaded"});
  await page.waitForURL("**/shared-auth-preview",{timeout:25000});
  await page.getByLabel("Код организации").fill("tenant_c");
  await page.getByLabel("Код отеля").fill("HOTEL_C");
  await page.getByLabel("Логин").fill("owner");
  await page.getByLabel("Пароль").fill(password);
  const login=page.waitForResponse(r=>r.url().includes("/core/api/v1/auth/login")&&r.request().method()==="POST");
  await page.getByRole("button",{name:"Войти"}).click();
  const response=await login;
  assert.equal(response.status(),200,await response.text());
  const auth=await response.json();
  assert.equal(auth.property_code,"HOTEL_C");
  assert.equal(auth.role,"OWNER");
  await page.getByText("Подтверждённый вход:",{exact:false}).waitFor();
  await page.getByRole("button",{name:"Шахматка",exact:true}).click();
  const grid=page.getByRole("region",{name:"Шахматка"});
  await grid.getByText("Номеров: 0",{exact:true}).waitFor();
  assert.equal(await grid.getByText("A101",{exact:false}).count(),0);
  assert.equal(await grid.getByText("B202",{exact:false}).count(),0);
  const overview=await ctx.request.get(BASE+"/core/api/v1/admin/staff/overview");
  assert.equal(overview.status(),200,await overview.text());
  const users=(await overview.json()).staff;
  assert.equal(users.length,1);
  assert.equal(users[0].username,"owner");
  const tasks=await ctx.request.get(BASE+"/core/api/v1/ops/tasks");
  assert.equal(tasks.status(),200,await tasks.text());
  assert.deepEqual((await tasks.json()).items,[]);
  for(const other of ["HOTEL_A","HOTEL_B"]){
    assert.notEqual(auth.property_code,other);
  }
  console.log("MARINA_SHARED_THIRD_HOTEL_BROWSER_PASS: Chromium mobile viewport login, empty independent grid, one owner and zero foreign tasks");
}finally{
  await browser.close();
}
