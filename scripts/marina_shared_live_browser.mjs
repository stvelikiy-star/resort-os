import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
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
function localShift(value, days) {
  const d=new Date(value+"T12:00:00Z");
  assert(!Number.isNaN(d.getTime()),"Invalid hotel-local business date");
  d.setUTCDate(d.getUTCDate()+days);
  return d.toISOString().slice(0,10);
}
async function createStayFixture(context,hotel) {
  const receipt=receipts[hotel];
  const list=await context.request.get(BASE+"/core/api/v1/admin/reception/reservations");
  assert.equal(list.status(),200);
  const localToday=(await list.json()).local_date;
  assert.match(localToday,/^\\d{4}-\\d{2}-\\d{2}$/);
  const stayStart=localShift(localToday,-1);
  const stayEnd=localShift(localToday,1);
  const input={room_id:receipt.room_id,check_in:stayStart,check_out:stayEnd,adults:2,children:0};
  const preview=await context.request.post(BASE+"/core/api/v1/admin/pms/reservations/new/preview",
    {data:input});
  assert.equal(preview.status(),200,await preview.text());
  const quoted=await preview.json();
  assert.equal(quoted.can_commit,true,"Stay fixture room must be available");
  const created=await context.request.post(BASE+"/core/api/v1/admin/pms/reservations/new/commit",{
    data:{...input,guest_name:"Synthetic Same-Day Guest "+hotel,
      phone:"+996555440011",expected_total_kgs:quoted.pricing.total_kgs,
      expected_pricing_source:quoted.pricing.source},
  });
  assert.equal(created.status(),201,await created.text());
  const booking=await created.json();
  receipt.stay_fixture={reservation_id:booking.reservation_id,
    booking_number:booking.booking_number,planned_start:stayStart,
    planned_end:stayEnd,checkout_local_date:localToday};
}
async function completeStayViaBrowser(page,hotel){
  const fixture=receipts[hotel].stay_fixture;
  await page.getByRole("button",{name:"Бронирования"}).click();
  const row=page.getByRole("row").filter({hasText:fixture.booking_number});
  const checkInResponse=page.waitForResponse(res=>
    res.url().endsWith("/core/api/v1/admin/stays/reservations/"+fixture.reservation_id+"/check-in") &&
    res.request().method()==="POST");
  await row.getByRole("button",{name:"Заселить"}).click();
  const checkedIn=await checkInResponse;
  assert.equal(checkedIn.status(),200,await checkedIn.text());
  const inData=await checkedIn.json();
  assert.equal(inData.reservation_id,fixture.reservation_id);
  assert.equal(inData.status,"CHECKED_IN");
  assert.match(inData.guest_access_pin,/^\\d{6}$/,"Missing one-time guest PIN");
  assert.equal(inData.guest_access_pin_display_once,true);
  await page.getByLabel("Одноразовый гостевой PIN").waitFor();
  const checkOutResponse=page.waitForResponse(res=>
    res.url().endsWith("/core/api/v1/admin/stays/reservations/"+fixture.reservation_id+"/check-out") &&
    res.request().method()==="POST");
  await row.getByRole("button",{name:"Выселить"}).click();
  const checkedOut=await checkOutResponse;
  assert.equal(checkedOut.status(),200,await checkedOut.text());
  const outData=await checkedOut.json();
  assert.equal(outData.reservation_id,fixture.reservation_id);
  assert.equal(outData.status,"CHECKED_OUT");
  assert.equal(outData.room_state,"DIRTY");
  assert.equal(outData.early_checkout_released_inventory,true);
  assert.match(outData.housekeeping_task_id,/^[0-9a-f-]{36}$/i);
  await page.getByLabel("Одноразовый гостевой PIN").waitFor({state:"detached"});
  fixture.stay_id=outData.stay_id;
  fixture.housekeeping_task_id=outData.housekeeping_task_id;
  const detail=await page.context().request.get(BASE+
    "/core/api/v1/admin/reception/reservations/"+fixture.reservation_id);
  assert.equal(detail.status(),200);
  const data=await detail.json();
  assert.equal(data.reservation?.status??data.status,"CHECKED_OUT");
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
  // Schedule/cancellation steps navigate to the bookings section; reopen the
  // hotel's scoped HOLD panel before releasing the earlier live hold.
  await page.getByRole("button",{name:"Шахматка"}).click();
  await page.getByRole("button",{name:"Показать HOLD"}).click();
  await page.getByRole("button",{name:"Освободить HOLD"}).waitFor();
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

async function changeSchedule(page,hotel) {
  const bookingNumber = receipts[hotel].booking_number;
  await page.getByRole("button",{name:"Бронирования"}).click();
  const row = page.getByRole("row").filter({hasText:bookingNumber});
  await row.getByRole("button",{name:"Управление"}).click();
  const section=page.getByRole("region",{name:"Управление бронью "+bookingNumber});
  await section.getByRole("button",{name:"Загрузить график"}).click();
  const form=section.getByRole("form",{name:"Изменение дат брони"});
  await form.waitFor();
  await form.getByLabel("Новый выезд").fill(day(5));
  const previewResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/pms/reservations/"+receipts[hotel].reservation_id+"/schedule/preview") &&
    res.request().method()==="POST");
  await form.getByRole("button",{name:"Проверить новые даты"}).click();
  const quoted=await previewResponse;
  assert.equal(quoted.status(),200,await quoted.text());
  const quote=await quoted.json();
  assert.equal(quote.can_commit,true);
  assert.equal(quote.proposed_check_out,day(5));
  assert.equal(quote.pricing.stored_total_will_change_on_commit,false);
  assert.equal(quote.pricing.suggested_total_kgs,expectedPrice[hotel]*3/2);
  const commitResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/pms/reservations/"+receipts[hotel].reservation_id+"/schedule/commit") &&
    res.request().method()==="POST");
  await section.getByRole("button",{name:"Сохранить даты"}).click();
  const response=await commitResponse;
  assert.equal(response.status(),200,await response.text());
  const result=await response.json();
  assert.equal(result.ok,true);
  assert.equal(result.stored_total_kgs,expectedPrice[hotel]);
  assert.equal(result.check_out,day(5));
  receipts[hotel].new_check_out=day(5);
  await section.getByText("Даты подтверждены сервером.",{exact:false}).waitFor();
}
async function recordManualPayment(page,hotel){
  const receipt=receipts[hotel], amount=hotel==="HOTEL_A"?1000:1500;
  const row=page.getByRole("row").filter({hasText:receipt.booking_number});
  await row.getByRole("button",{name:"Управление"}).click();
  const section=page.getByRole("region",{name:"Управление бронью "+receipt.booking_number});
  const panel=section.getByRole("region",{name:"Внутренняя оплата "+receipt.booking_number});
  await panel.getByRole("button",{name:"Записать полученную оплату"}).click();
  const readinessResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/booking/reservations/"+receipt.reservation_id+"/acquiring-readiness") &&
    res.request().method()==="GET");
  await panel.getByRole("button",{name:"Проверить остаток"}).click();
  const readiness=await readinessResponse;
  assert.equal(readiness.status(),200,await readiness.text());
  const read=await readiness.json();
  assert.equal(read.reservation_id,receipt.reservation_id);
  assert.equal(read.provider_connected,false,"No external acquiring should be claimed");
  assert.equal(read.remaining_kgs,receipt.total_kgs);
  const form=panel.getByRole("form",{name:"Форма ручной оплаты"});
  await form.getByLabel("Полученная сумма, KGS").fill(String(amount));
  await form.getByLabel("Способ получения").selectOption("CASH");
  await form.getByRole("checkbox",{name:"Деньги действительно уже получены, я проверил(а) сумму"}).check();
  const recordedResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/booking/reservations/"+receipt.reservation_id+"/payments") &&
    res.request().method()==="POST");
  await form.getByRole("button",{name:"Записать полученную сумму"}).click();
  const response=await recordedResponse;
  assert.equal(response.status(),201,await response.text());
  const recorded=await response.json();
  assert.equal(recorded.reservation_id,receipt.reservation_id);
  assert.equal(recorded.idempotent_replay,false);
  assert.equal(recorded.payment.status,"RECEIVED");
  assert.equal(recorded.payment.provider,"MANAGER_MANUAL");
  assert.equal(recorded.payment.amount_kgs,amount);
  assert.equal(recorded.finance.paid_kgs,amount);
  receipt.manual_payment_id=recorded.payment_id;
  receipt.manual_amount_kgs=amount;
  await panel.getByText("Учтена ранее полученная оплата",{exact:false}).waitFor();

  const review=await page.context().request.get(
    BASE+"/core/api/v1/admin/booking/reservations/"+receipt.reservation_id+"/acquiring-readiness");
  assert.equal(review.status(),200);
  assert.equal((await review.json()).remaining_kgs,receipt.total_kgs-amount);
  const forbiddenCancel=await page.context().request.post(
    BASE+"/core/api/v1/admin/pms/reservations/"+receipt.reservation_id+"/cancel");
  assert.equal(forbiddenCancel.status(),409,"Paid booking must not cancel on unpaid path");
}

async function createCancellationFixture(context,hotel){
  const url=BASE+"/core/api/v1/admin/pms/reservations/new/";
  const payload={room_id:receipts[hotel].room_id,check_in:day(10),check_out:day(12),adults:2,children:0};
  const quoteResponse=await context.request.post(url+"preview",{data:payload});
  assert.equal(quoteResponse.status(),200,await quoteResponse.text());
  const quote=await quoteResponse.json();
  assert.equal(quote.can_commit,true);
  const committed=await context.request.post(url+"commit",{data:{
    ...payload,guest_name:"Synthetic Cancel Fixture "+hotel,phone:"+996555110022",
    expected_total_kgs:quote.pricing.total_kgs,expected_pricing_source:quote.pricing.source,
  }});
  assert.equal(committed.status(),201,await committed.text());
  const result=await committed.json();
  receipts[hotel].cancel_fixture={reservation_id:result.reservation_id,booking_number:result.booking_number};
}
async function cancelFixture(page,hotel){
  const fixture=receipts[hotel].cancel_fixture;
  // Navigate away and back to load freshly persisted backend reservations.
  await page.getByRole("button",{name:"Шахматка"}).click();
  await page.getByRole("button",{name:"Бронирования"}).click();
  const row=page.getByRole("row").filter({hasText:fixture.booking_number});
  await row.getByRole("button",{name:"Управление"}).click();
  const section=page.getByRole("region",{name:"Управление бронью "+fixture.booking_number});
  const reviewResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/booking/reservations/"+fixture.reservation_id+"/cancellation-finance-review") &&
    res.request().method()==="GET");
  const cancelledResponse=page.waitForResponse(res =>
    res.url().endsWith("/core/api/v1/admin/pms/reservations/"+fixture.reservation_id+"/cancel") &&
    res.request().method()==="POST");
  await section.getByRole("button",{name:"Отменить неоплаченную бронь"}).click();
  const reviewed=await reviewResponse;
  assert.equal(reviewed.status(),200,await reviewed.text());
  assert.equal((await reviewed.json()).unpaid_cancel_path_eligible,true);
  const cancelled=await cancelledResponse;
  assert.equal(cancelled.status(),200,await cancelled.text());
  const result=await cancelled.json();
  assert.equal(result.reservation_id,fixture.reservation_id);
  assert.equal(result.status,"CANCELLED");
  assert.equal(result.payment_refunded,false);
  assert.equal(result.released_blocks,1);
  const apiAfterCancel=await page.context().request.get(
    BASE+"/core/api/v1/admin/reception/reservations/"+fixture.reservation_id);
  assert.equal(apiAfterCancel.status(),200);
  const detail=await apiAfterCancel.json();
  assert.equal(detail.reservation?.status ?? detail.status,"CANCELLED");
  // The Admin locale sanitizer renders Russian labels for enum statuses.
  // Verify visible state as well as the unchanged canonical API enum.
  await row.getByRole("cell",{name:/^(?:ОТМЕНЕНО|CANCELLED)$/}).waitFor();
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
  await changeSchedule(pageA,"HOTEL_A");
  await createCancellationFixture(contextA,"HOTEL_A");
  await cancelFixture(pageA,"HOTEL_A");
  await recordManualPayment(pageA,"HOTEL_A");

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
  await changeSchedule(pageB,"HOTEL_B");
  await createCancellationFixture(contextB,"HOTEL_B");
  await cancelFixture(pageB,"HOTEL_B");
  await recordManualPayment(pageB,"HOTEL_B");
  const reverseHold = await contextA.request.get(
    BASE + "/core/api/v1/admin/pms/holds/" + receipts.HOTEL_B.hold_id);
  assert.equal(reverseHold.status(),404,"Reverse direction foreign HOLD");
  const crossPayment=await contextB.request.post(
    BASE+"/core/api/v1/admin/booking/reservations/"+receipts.HOTEL_A.reservation_id+"/payments",{
      headers:{"X-Property-Id":ownerA.property_id,"X-Tenant-Id":ownerA.tenant_id,"X-Role":"OWNER"},
      data:{amount_kgs:100,method:"CASH",idempotency_key:randomUUID()},
    });
  assert.equal(crossPayment.status(),404,"Foreign manual payment must not be allowed");
  const foreignSchedule=await contextB.request.get(BASE+
    "/core/api/v1/admin/pms/reservations/"+receipts.HOTEL_A.reservation_id+"/schedule");
  assert.equal(foreignSchedule.status(),404,"Foreign reservation schedule leak");
  const foreignCancel=await contextB.request.post(BASE+
    "/core/api/v1/admin/pms/reservations/"+receipts.HOTEL_A.reservation_id+"/cancel");
  assert.equal(foreignCancel.status(),404,"Foreign cancellation must fail");
  await releaseHold(pageA,"HOTEL_A");
  await releaseHold(pageB,"HOTEL_B");
  await createStayFixture(contextA,"HOTEL_A");
  await createStayFixture(contextB,"HOTEL_B");
  await completeStayViaBrowser(pageA,"HOTEL_A");
  await completeStayViaBrowser(pageB,"HOTEL_B");
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
  console.log("MARINA_SHARED_LIVE_BROWSER_HTTP_PASS: 2 hotels booking, schedule, HOLD, cancellation, manual receipt, check-in+one-time PIN, check-out+housekeeping, tenant isolation");
} finally {
  await browser.close();
}
