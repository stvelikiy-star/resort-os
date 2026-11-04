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
    const committed = page.waitForResponse(response =>
      response.url() === core + "/admin/pms/reservations/new/commit" &&
      response.request().method() === "POST");
    await form.getByRole("button", { name: "Подтвердить бронь" }).click();
    const response = await committed;
    assert.equal(response.status(), 201, code + " booking commit");
    const booking = await response.json();
    assert.equal(booking.total_kgs, suffix === "A" ? 6000 : 9000);
    assert.equal(booking.payment_created, false);
    assert.match(booking.reservation_id, /^[0-9a-f-]{36}$/i);
    hotels.push({ page, id: booking.reservation_id });
  }

  assert.notEqual(hotels[0].id, hotels[1].id);
  for (const [own, foreign] of [hotels, hotels.slice().reverse()]) {
    const route = core + "/admin/reception/reservations/";
    const status = url => own.page.evaluate(async target =>
      (await fetch(target, { credentials: "same-origin", redirect: "error" })).status, url);
    assert.equal(await status(route + own.id), 200);
    assert.equal(await status(route + foreign.id), 404);
  }
  console.log("PASS: Chromium HTTPS bookings, hotel-specific rates and bidirectional isolation");
} finally {
  await browser.close();
}
