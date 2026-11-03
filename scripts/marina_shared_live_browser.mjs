import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { chromium } from "playwright";

// Real network acceptance: DO NOT route/mock/intercept API calls.
// GitHub Actions runs local Next.js -> ASGI -> disposable PostgreSQL.
const BASE = process.env.MARINA_SHARED_BROWSER_URL || "http://127.0.0.1:13001";
const url = new URL(BASE);
assert(["127.0.0.1", "localhost"].includes(url.hostname), "localhost required");
assert.equal(process.env.MARINA_SHARED_BROWSER_CI_CONFIRM, "DISPOSABLE_TWO_HOTEL_BROWSER_CI");
const password = process.env.MARINA_SHARED_BROWSER_CI_PASSWORD;
assert(password?.startsWith("synthetic-ci-only-") && password.length >= 16);
const receipts = {};
const browser = await chromium.launch({ headless: true });
const today = new Date();
function day(offset) {
  const date = new Date(today);
  date.setDate(date.getDate() + offset);
  return date.getFullYear() + "-" + String(date.getMonth() + 1).padStart(2, "0") +
    "-" + String(date.getDate()).padStart(2, "0");
}
const checkIn = day(2), checkOut = day(4);
const expectedPrice = { HOTEL_A:6000, HOTEL_B:9000 };
async function signIn(page, code) {
  await page.goto(BASE, { waitUntil:"domcontentloaded" });
  await page.waitForURL("**/shared-auth-preview", { timeout:25000 });
  await page.getByLabel("Код организации").fill("tenant_" + code.at(-1).toLowerCase());
  await page.getByLabel("Код отеля").fill(code);
  await page.getByLabel("Логин").fill("owner");
  await page.getByLabel("Пароль").fill(password);
  const loginResponse = page.waitForResponse(r =>
    r.url().includes("/core/api/v1/auth/login") && r.request().method()==="POST");
  await page.getByRole("button",{name:"Войти"}).click();
  const response = await loginResponse;
  assert.equal(response.status(),200,"Real HTTP login must succeed");
  await page.getByText("Подтверждённый вход:", {exact:false}).waitFor();
  await page.getByRole("button",{name:"Шахматка"}).click();
  await page.getByRole("form",{name:"Форма бронирования"}).waitFor();
  const me = await page.context().request.get(BASE + "/core/api/v1/auth/me");
  assert.equal(me.status(),200);
  const identity = await me.json();
  assert.equal(identity.property_code,code);
  return identity;
}
async function book(page, hotel, roomCode) {
  const form = page.getByRole("form",{name:"Форма бронирования"});
  const selector = form.getByLabel("Номер");
  await selector.selectOption({label:roomCode + " · CI Room"});
  const roomId = await selector.inputValue();
  assert.match(roomId, /^[0-9a-f-]{36}$/i);
  await form.getByLabel("Заезд").fill(checkIn);
  await form.getByLabel("Выезд").fill(checkOut);
  await form.getByLabel("Имя гостя").fill("Synthetic Browser Guest " + hotel);
  await form.getByLabel("Телефон гостя").fill("+996555771122");
  const previewResponse = page.waitForResponse(r =>
    r.url().endsWith("/core/api/v1/admin/pms/reservations/new/preview") &&
    r.request().method()==="POST");
  await form.getByRole("button",{name:"Проверить доступность и цену"}).click();
  const preview = await previewResponse;
  assert.equal(preview.status(),200);
  const quote = await preview.json();
  assert.equal(quote.room.id,roomId);
  assert.equal(quote.can_commit,true);
  assert.equal(quote.pricing.source,"CORE_RATE");
  assert.equal(quote.pricing.total_kgs,expectedPrice[hotel]);
  await page.getByRole("button",{name:"Подтвердить бронь"}).waitFor();
  const commitResponse = page.waitForResponse(r =>
    r.url().endsWith("/core/api/v1/admin/pms/reservations/new/commit") &&
    r.request().method()==="POST");
  await page.getByRole("button",{name:"Подтвердить бронь"}).click();
  const committed = await commitResponse;
  assert.equal(committed.status(),201,await committed.text());
  const data = await committed.json();
  assert.equal(data.status,"GUARANTEED");
  assert.equal(data.total_kgs,expectedPrice[hotel]);
  assert.equal(data.room_id,roomId);
  assert.equal(data.payment_created,false);
  assert.match(data.reservation_id,/^[0-9a-f-]{36}$/i);
  await page.getByText("Бронирование " + data.booking_number + " создано сервером.",{exact:false}).waitFor();
  receipts[hotel]={
    reservation_id:data.reservation_id,room_id:roomId,
    total_kgs:data.total_kgs,booking_number:data.booking_number,
  };
  // HTTP request genuinely executes against the database; stale client quote must not
  // create a second booking for the occupied room.
  const replayPreview = await page.context().request.post(
    BASE + "/core/api/v1/admin/pms/reservations/new/preview", {
      data:{room_id:roomId,check_in:checkIn,check_out:checkOut,adults:2,children:0},
    });
  assert.equal(replayPreview.status(),200);
  assert.equal((await replayPreview.json()).can_commit,false,"Booked room must no longer be available");
  return roomId;
}
async function makeHold(page, hotel, roomCode) {
  await page.getByRole("button",{name:"Показать HOLD"}).click();
  const form = page.getByRole("form",{name:"Форма HOLD"});
  await form.waitFor();
  await form.getByLabel("Номер HOLD").selectOption({label:roomCode + " · CI Room"});
  await form.getByLabel("Заезд HOLD").fill(day(6));
  await form.getByLabel("Выезд HOLD").fill(day(8));
  await form.getByLabel("Гость HOLD").fill("Synthetic Hold " + hotel);
  await form.getByLabel("Телефон HOLD").fill("+996555771122");
  const createResponse = page.waitForResponse(r =>
    r.url().endsWith("/core/api/v1/admin/pms/holds") &&
    r.request().method()==="POST");
  await form.getByRole("button",{name:"Удержать на 60 минут"}).click();
  const res = await createResponse;
  assert.equal(res.status(),201,await res.text());
  const result = await res.json();
  assert.equal(result.status,"HELD");
  assert.equal(result.duration_minutes,60);
  assert.match(result.id,/^[0-9a-f-]{36}$/i);
  await page.getByRole("button",{name:"Освободить HOLD"}).waitFor();
  receipts[hotel].hold_id = result.id;
  return result.id;
}
async function releaseHold(page, hotel) {
  const releaseResponse = page.waitForResponse(r =>
    r.url().endsWith("/core/api/v1/admin/pms/holds/" + receipts[hotel].hold_id) &&
    r.request().method()==="DELETE");
  await page.getByRole("button",{name:"Освободить HOLD"}).click();
  const res = await releaseResponse;
  assert.equal(res.status(),200,await res.text());
  const released = await res.json();
  assert.equal(released.id,receipts[hotel].hold_id);
  assert.equal(released.status,"RELEASED");
  await page.getByText("Активных удержаний нет.").waitFor();
}

try {
  const contextA = await browser.newContext({ viewport:{width:390,height:844} });
  const pageA = await contextA.newPage();
  pageA.on("dialog",dialog=>dialog.accept());
  const ownerA = await signIn(pageA,"HOTEL_A");
  await pageA.getByRole("cell",{name:"A101 · CI Room"}).waitFor();
  assert.equal(await pageA.getByText("B202").count(),0);
  const roomA = await book(pageA,"HOTEL_A","A101");
  await makeHold(pageA,"HOTEL_A","A101");

  const contextB = await browser.newContext({ viewport:{width:390,height:844} });
  const pageB = await contextB.newPage();
  pageB.on("dialog",dialog=>dialog.accept());
  const ownerB = await signIn(pageB,"HOTEL_B");
  await pageB.getByRole("cell",{name:"B202 · CI Room"}).waitFor();
  assert.notEqual(ownerA.property_id,ownerB.property_id);
  assert.notEqual(ownerA.tenant_id,ownerB.tenant_id);
  assert.equal(await pageB.getByText("A101").count(),0);
  assert.equal(await pageB.getByText(receipts.HOTEL_A.booking_number).count(),0);

  // Forged hotel-selector headers must not bypass the DB-verified session.
  const crossPreview = await contextB.request.post(
    BASE + "/core/api/v1/admin/pms/reservations/new/preview", {
      headers:{"X-Property-Id":ownerA.property_id,"X-Tenant-Id":ownerA.tenant_id,"X-Role":"OWNER"},
      data:{room_id:roomA,check_in:checkIn,check_out:checkOut,adults:2,children:0},
    });
  assert.equal(crossPreview.status(),404,"Foreign room must not be discoverable");
  const crossDetail = await contextB.request.get(
    BASE + "/core/api/v1/admin/reception/reservations/" + receipts.HOTEL_A.reservation_id, {
      headers:{"X-Property-Id":ownerA.property_id,"X-Tenant-Id":ownerA.tenant_id,"X-Role":"OWNER"},
    });
  assert.equal(crossDetail.status(),404,"Foreign reservation must not be readable");

  await book(pageB,"HOTEL_B","B202");
  const foreignHold = await contextB.request.get(
    BASE + "/core/api/v1/admin/pms/holds/" + receipts.HOTEL_A.hold_id, {
      headers:{"X-Property-Id":ownerA.property_id,"X-Tenant-Id":ownerA.tenant_id,"X-Role":"OWNER"},
    });
  assert.equal(foreignHold.status(),404,"Foreign HOLD must not be readable");
  await makeHold(pageB,"HOTEL_B","B202");
  const reverseHold = await contextA.request.get(
    BASE + "/core/api/v1/admin/pms/holds/" + receipts.HOTEL_B.hold_id);
  assert.equal(reverseHold.status(),404,"Reverse direction foreign HOLD");
  await releaseHold(pageA,"HOTEL_A");
  await releaseHold(pageB,"HOTEL_B");
  const aDetail = await contextA.request.get(
    BASE + "/core/api/v1/admin/reception/reservations/" + receipts.HOTEL_B.reservation_id);
  assert.equal(aDetail.status(),404,"Reverse direction foreign reservation leak");
  const sameHotelA = await contextA.request.get(
    BASE + "/core/api/v1/admin/reception/reservations/" + receipts.HOTEL_A.reservation_id);
  assert.equal(sameHotelA.status(),200,"Own reservation detail must be readable");
  const sameHotelB = await contextB.request.get(
    BASE + "/core/api/v1/admin/reception/reservations/" + receipts.HOTEL_B.reservation_id);
  assert.equal(sameHotelB.status(),200,"Own reservation detail must be readable");

  writeFileSync("/tmp/marina_shared_browser_receipts.json", JSON.stringify(receipts));
  console.log("MARINA_SHARED_LIVE_BROWSER_HTTP_PASS: two real sessions, 2 bookings, 2 created/released HOLDs, conflict, bidirectional tenant isolation at 390px");
} finally {
  await browser.close();
}
