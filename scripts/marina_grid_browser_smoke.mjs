import { chromium } from "playwright";

const BASE = process.env.MARINA_ADMIN_BROWSER_URL || "http://127.0.0.1:13001";
const USERNAME = process.env.BOOTSTRAP_OWNER_USERNAME;
const PASSWORD = process.env.BOOTSTRAP_OWNER_PASSWORD;
if (!USERNAME || !PASSWORD || !new URL(BASE).hostname.match(/^(127\.0\.0\.1|localhost)$/)) {
  throw new Error("Synthetic local-only browser credentials and URL required");
}
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
const serverErrors = [];
page.on("pageerror", e => pageErrors.push(e.message));
page.on("response", r => {
  if (r.url().includes("/core/api/v1/") && r.status() >= 500) {
    serverErrors.push(r.status() + " " + r.url());
  }
});
try {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.locator('input[autocomplete="username"]').fill(USERNAME);
  await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
  await page.locator("button.login-button").click();
  await page.getByRole("button", { name: "Шахматка", exact: true }).waitFor({ state: "visible", timeout: 20000 });
  await page.getByRole("button", { name: "Шахматка", exact: true }).click();
  await page.locator(".owner-grid-shell").waitFor({ state: "visible", timeout: 20000 });
  await page.locator(".owner-grid-loading").waitFor({ state: "hidden", timeout: 20000 });
  await page.getByRole("heading", { name: "Номер × ночь" }).waitFor();
  const cells = page.locator("[data-room-code]");
  if (await cells.count() === 0) throw new Error("No calendar cells for synthetic hotel");
  const month = page.getByRole("combobox", { name: "Месяц" });
  const year = page.getByRole("combobox", { name: "Год" });
  if (await month.count() !== 1 || await year.count() !== 1) throw new Error("Month or year filter missing");
  await page.getByRole("button", { name: "Следующий месяц" }).click();
  await page.locator(".owner-grid-loading").waitFor({ state: "hidden", timeout: 20000 });
  // The loading state can disappear before the next month's cells commit to the DOM.
  // Wait for actual visible cells; a genuinely empty calendar must still fail.
  await cells.first().waitFor({ state: "visible", timeout: 20000 });
  if (await cells.count() === 0) throw new Error("Grid empty after month navigation");
  await page.getByRole("button", { name: "Показать 31 дней" }).click();
  if (await page.locator('.owner-grid-scroll[data-window-days="31"]').count() !== 1) throw new Error("31-day calendar not activated");
  await page.setViewportSize({ width: 390, height: 844 });
  if (!(await page.locator(".owner-grid-shell").isVisible())) throw new Error("Grid hidden on mobile");
  const scroll = page.locator(".owner-grid-scroll");
  if (!(await scroll.isVisible())) throw new Error("Calendar scrolling not available on mobile");
  const bounds = await page.locator(".owner-grid-shell").boundingBox();
  if (!bounds || bounds.width > 395) throw new Error("Grid shell overflows 390px viewport");
  // Verify owner can configure actual per-hotel rules through the existing UI.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator("details.admin-more-menu summary").click();
  await page.getByRole("button", { name: "Знания отеля / MARINA AI", exact: true }).click();
  await page.getByRole("heading", { name: "Правила и знания отеля для MARINA AI", exact: true }).waitFor();
  await page.getByRole("button", { name: /^04 · Оплата, отмена и бронирование/ }).click();
  await page.getByLabel("Как берём предоплату?").selectOption("FIRST_NIGHT");
  await page.getByLabel("Бесплатная отмена за сколько дней до заезда?").fill("7");
  await page.getByRole("button", { name: /^01 · О гостинице и контактах/ }).click();
  await page.getByLabel("Полный адрес").fill("Тестовый адрес MARINA FULL CI");
  await page.getByLabel("Как представить гостиницу гостю").fill("Синтетический гостиничный объект MARINA");
  await page.getByRole("button", { name: /^02 · Заезд и правила проживания/ }).click();
  await page.getByLabel("Животные").fill("По согласованию с владельцем");
  await page.getByRole("button", { name: "Сохранить знания и правила" }).click();
  await page.getByText("Сохранено. MARINA AI будет использовать обновлённые правила в следующих ответах.").waitFor();
  await page.reload({ waitUntil: "networkidle" });
  await page.locator("details.admin-more-menu summary").click();
  await page.getByRole("button", { name: "Знания отеля / MARINA AI", exact: true }).click();
  await page.getByRole("heading", { name: "Правила и знания отеля для MARINA AI", exact: true }).waitFor();
  await page.getByRole("button", { name: /^02 · Заезд и правила проживания/ }).click();
  if (await page.getByLabel("Животные").inputValue() !== "По согласованию с владельцем") {
    throw new Error("Saved hotel rules not preserved after browser reload");
  }
  await page.getByRole("button", { name: /^01 · О гостинице и контактах/ }).click();
  if (await page.getByLabel("Полный адрес").inputValue() !== "Тестовый адрес MARINA FULL CI") {
    throw new Error("Hotel knowledge not preserved after browser reload");
  }
  // Complete the cancellation in the real owner UI against a disposable CI hotel.
  const testDate = new Date();
  testDate.setUTCDate(testDate.getUTCDate() + 14);
  const checkIn = testDate.toISOString().slice(0, 10);
  testDate.setUTCDate(testDate.getUTCDate() + 2);
  const checkOut = testDate.toISOString().slice(0, 10);
  const bookingBase = `${BASE}/core/api/v1`;
  const availabilityResponse = await page.request.get(`${bookingBase}/booking/check-availability?` + new URLSearchParams({
    check_in: checkIn, check_out: checkOut, adults: "2", children: "0",
  }));
  if (!availabilityResponse.ok()) throw new Error("UI booking fixture availability failed: " + availabilityResponse.status());
  const available = await availabilityResponse.json();
  const roomId = available.results?.flatMap(item => item.available_rooms || []).find(room => room.id)?.id;
  if (!roomId) throw new Error("No available room for disposable UI cancellation test");
  const input = { room_id: roomId, check_in: checkIn, check_out: checkOut, adults: 2, children: 0 };
  const quoteResponse = await page.request.post(`${bookingBase}/admin/pms/reservations/new/preview`, { data: input });
  if (!quoteResponse.ok()) throw new Error("UI booking fixture preview failed: " + quoteResponse.status());
  const quote = await quoteResponse.json();
  if (!quote.can_commit || !quote.pricing?.total_kgs) throw new Error("UI booking fixture cannot commit");
  const guest = "Synthetic UI Cancellation";
  const commitResponse = await page.request.post(`${bookingBase}/admin/pms/reservations/new/commit`, {
    data: {
      ...input, guest_name: guest, phone: "+996555000101",
      expected_total_kgs: quote.pricing.total_kgs,
      expected_pricing_source: quote.pricing.source,
    },
  });
  if (commitResponse.status() !== 201) throw new Error("UI booking fixture commit failed: " + commitResponse.status());
  const created = await commitResponse.json();
  await page.getByRole("button", { name: "Шахматка", exact: true }).click();
  await page.locator(".owner-grid-shell").waitFor({ state: "visible" });
  await page.getByRole("combobox", { name: "Год" }).selectOption(String(Number(checkIn.slice(0, 4))));
  await page.getByRole("combobox", { name: "Месяц" }).selectOption(String(Number(checkIn.slice(5, 7)) - 1));
  await page.getByRole("button", { name: "Показать 31 дней" }).click();
  const bookingBar = page.locator(".owner-booking-bar").filter({ hasText: guest });
  await bookingBar.first().waitFor({ state: "visible", timeout: 20000 });
  await bookingBar.first().click();
  await page.getByRole("dialog").getByRole("button", { name: "Отменить неоплаченную бронь" }).click();
  await page.getByRole("group", { name: "Подтвердить отмену брони" }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Да, отменить бронь" }).click();
  await page.getByRole("dialog").waitFor({ state: "hidden", timeout: 20000 });
  await bookingBar.first().waitFor({ state: "hidden", timeout: 20000 });
  const cancelledResponse = await page.request.post(`${bookingBase}/admin/pms/reservations/${created.reservation_id}/cancel`);
  if (cancelledResponse.status() !== 409) throw new Error("UI cancellation did not persist a terminal reservation state");
  if (pageErrors.length || serverErrors.length) throw new Error(JSON.stringify({ pageErrors, serverErrors }));
  console.log("MARINA_BROWSER_GRID_PASS: owner auth, compact grid, cancellation via UI, month/year, mobile viewport, no runtime 5xx");
} finally {
  await browser.close();
}
