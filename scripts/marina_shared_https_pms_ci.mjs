import assert from "node:assert/strict";
import { chromium } from "playwright";

const origin = "https://localhost:13443";
const core = origin + "/core/api/v1";
const pin = process.env.MARINA_STAGING_CERT_SPKI;
const password = process.env.MARINA_STAGING_FIXTURE_PASSWORD;
assert.match(pin ?? "", /^[A-Za-z0-9+/]{43}=$/);
assert(password?.startsWith("synthetic-ci-only-"));

function dateAfter(days) {
  return new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
}

const browser = await chromium.launch({
  args: ["--ignore-certificate-errors-spki-list=" + pin],
});
try {
  const hotels = [];
  for (const suffix of ["A", "B"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const code = "HOTEL_" + suffix;
    await page.goto(origin);
    await page.waitForURL(origin + "/shared-auth-preview");
    await page.getByLabel("Код организации").fill("tenant_" + suffix.toLowerCase());
    await page.getByLabel("Код отеля").fill(code);
    await page.getByLabel("Логин").fill("owner");
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();
    await page.getByText("Подтверждённый вход:", { exact: false }).waitFor();
    await page.getByRole("button", { name: "Шахматка" }).click();

    const form = page.getByRole("form", { name: "Форма бронирования" });
    const room = suffix === "A" ? "A101" : "B202";
    await form.getByLabel("Номер").selectOption({ label: room + " · CI Room" });
    await form.getByLabel("Заезд").fill(dateAfter(2));
    await form.getByLabel("Выезд").fill(dateAfter(4));
    await form.getByLabel("Имя гостя").fill("Synthetic HTTPS Guest " + suffix);
    await form.getByLabel("Телефон гостя").fill("+996555771122");
    await form.getByRole("button", { name: "Проверить доступность и цену" }).click();
    const confirm = page.getByRole("button", { name: "Подтвердить бронь", exact: true });
    await confirm.waitFor();
    // Guest/phone changes invalidate the server quote before booking commit.
    await form.getByLabel("Телефон гостя").fill("+996555771123");
    await confirm.waitFor({ state: "hidden" });
    await form.getByRole("button", { name: "Проверить доступность и цену" }).click();
    await confirm.waitFor();
    await form.getByLabel("Имя гостя").fill("Synthetic HTTPS Guest " + suffix + " Updated");
    await confirm.waitFor({ state: "hidden" });
    await form.getByRole("button", { name: "Проверить доступность и цену" }).click();
    await confirm.waitFor();
    page.once("dialog", dialog => dialog.accept());
    const committed = page.waitForResponse(response =>
      response.url() === core + "/admin/pms/reservations/new/commit" &&
      response.request().method() === "POST");
    await confirm.click();
    const response = await committed;
    assert.equal(response.status(), 201, code + " booking commit");
    const booking = await response.json();
    assert.equal(booking.total_kgs, suffix === "A" ? 6000 : 9000);
    assert.equal(booking.payment_created, false);
    assert.match(booking.reservation_id, /^[0-9a-f-]{36}$/i);
    hotels.push({ page, id: booking.reservation_id, roomId: await form.getByLabel("Номер").inputValue() });
  }

  assert.notEqual(hotels[0].id, hotels[1].id);
  for (const [own, foreign] of [hotels, hotels.slice().reverse()]) {
    const route = core + "/admin/reception/reservations/";
    const status = url => own.page.evaluate(async target =>
      (await fetch(target, { credentials: "same-origin", redirect: "error" })).status, url);
    assert.equal(await status(route + own.id), 200);
    assert.equal(await status(route + foreign.id), 404);
  }
  // P0 reception: real browser login -> server CORE_RATE quote -> PostgreSQL booking.
  // The shared RC3 source-locked page remains unchanged; navigation is additive.
  const receptionBookings = [];
  for (const [index, suffix] of ["A", "B"].entries()) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const hotel = "HOTEL_" + suffix;
    await page.goto(origin + "/shared-auth-preview");
    await page.getByRole("link", { name: "Ресепшен: создать бронь" }).click();
    await page.waitForURL(origin + "/shared-reception");
    const login = page.getByRole("form", { name: "Вход ресепшен" });
    await login.getByLabel("Код организации").fill("tenant_" + suffix.toLowerCase());
    await login.getByLabel("Код отеля").fill(hotel);
    await login.getByLabel("Логин").fill("reception");
    await login.getByLabel("Пароль").fill(password);
    await login.getByRole("button", { name: "Войти как ресепшен" }).click();
    await page.getByText("Подтверждённый отель:", { exact: false }).waitFor();

    const bookingForm = page.getByRole("form", { name: "Форма бронирования" });
    const ownRoom = hotels[index].roomId;
    const foreignRoom = hotels[1 - index].roomId;
    const roomCode = suffix === "A" ? "A101" : "B202";
    await bookingForm.getByLabel("Номер").selectOption({ label: roomCode + " · CI Room" });
    await bookingForm.getByLabel("Заезд").fill(dateAfter(6));
    await bookingForm.getByLabel("Выезд").fill(dateAfter(8));
    await bookingForm.getByLabel("Имя гостя").fill("Reception HTTPS Guest " + suffix);
    await bookingForm.getByLabel("Телефон гостя").fill("+996555771188");

    const api = (path, payload) => page.evaluate(async ({ path, payload }) => {
      const response = await fetch("/core/api/v1/" + path, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    }, { path, payload });
    const fields = {
      room_id: ownRoom, check_in: dateAfter(6), check_out: dateAfter(8),
      adults: 2, children: 0, guest_phone: "+996555771188",
    };
    const previewPath = "admin/pms/reservations/new/preview";
    const commitPath = "admin/pms/reservations/new/commit";
    assert.equal((await api(previewPath, {
      ...fields, room_id: foreignRoom,
    })).status, 404, "Reception may not quote foreign room");
    for (const changes of [
      { manager_total_kgs: 1 },
      { discount_percent: 50 },
      { extra_bed_count: 1, extra_bed_unit_kgs: 500 },
      { hold_id: "11111111-1111-4111-8111-111111111111" },
      { agent_id: "11111111-1111-4111-8111-111111111111" },
    ]) {
      assert.equal((await api(previewPath, { ...fields, ...changes })).status, 403,
        "Reception override must be forbidden");
    }
    assert.equal((await api(commitPath, {
      ...fields, guest_name: "Forbidden override", phone: "+996555771188",
      expected_total_kgs: 1, expected_pricing_source: "MANAGER_OVERRIDE",
    })).status, 403, "Reception may not commit manager price");

    const quotedResponse = page.waitForResponse(response =>
      response.url() === core + "/admin/pms/reservations/new/preview" &&
      response.request().method() === "POST");
    await bookingForm.getByRole("button", { name: "Проверить доступность и цену" }).click();
    const quoted = await quotedResponse;
    assert.equal(quoted.status(), 200);
    const quote = await quoted.json();
    assert.equal(quote.pricing.source, "CORE_RATE");
    assert.equal(quote.pricing.discount_percent, 0);
    assert.equal(quote.pricing.total_kgs, suffix === "A" ? 6000 : 9000);
    // The confirmation button is intentionally OUTSIDE the quote form.
    // Scope preview to the form, but locate confirmation from the page.
    page.once("dialog", dialog => dialog.accept());
    const committedResponse = page.waitForResponse(response =>
      response.url() === core + "/admin/pms/reservations/new/commit" &&
      response.request().method() === "POST");
    await page.getByRole("button", { name: "Подтвердить бронь", exact: true }).click();
    const committed = await committedResponse;
    assert.equal(committed.status(), 201, "Reception booked own room");
    const result = await committed.json();
    assert.equal(result.room_id, ownRoom);
    assert.equal(result.pricing_source, "CORE_RATE");
    assert.equal(result.payment_terms, "RECEPTION_CORE_RATE");
    assert.equal(result.payment_created, false);
    assert.equal(result.total_kgs, suffix === "A" ? 6000 : 9000);

    // Replaying the same booking cannot double-sell the occupied room.
    assert.equal((await api(commitPath, {
      ...fields, guest_name: "Reception HTTPS Guest " + suffix,
      phone: "+996555771188", expected_total_kgs: quote.pricing.total_kgs,
      expected_pricing_source: "CORE_RATE",
    })).status, 409, "Duplicate room/date must be rejected");
    const own = await page.evaluate(async id =>
      (await fetch("/core/api/v1/admin/reception/reservations/" + id)).status,
    result.reservation_id);
    const foreign = await page.evaluate(async id =>
      (await fetch("/core/api/v1/admin/reception/reservations/" + id)).status,
    hotels[1 - index].id);
    assert.equal(own, 200);
    assert.equal(foreign, 404);
    receptionBookings.push(result.reservation_id);
    await context.close();
  }
  assert.notEqual(receptionBookings[0], receptionBookings[1]);
  console.log("PASS: Chromium HTTPS owner/reception bookings, core-rate ceilings and bidirectional hotel isolation");
} finally {
  await browser.close();
}
