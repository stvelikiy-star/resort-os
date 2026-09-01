import { chromium } from "playwright";

const BASE = process.env.ADMIN_BASE_URL || "http://127.0.0.1:3001";
const USERNAME = process.env.BOOTSTRAP_OWNER_USERNAME || "ci-owner";
const PASSWORD = process.env.BOOTSTRAP_OWNER_PASSWORD || "CI-Only-Strong-Password-2026";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function login(page) {
  await page.goto(BASE, { waitUntil: "networkidle" });
  if (await page.locator('input[autocomplete="username"]').count()) {
    await page.locator('input[autocomplete="username"]').fill(USERNAME);
    await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
    await page.locator("button.login-button").click();
  }
  await page.getByRole("button", { name: "Супершахматка" }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Супершахматка" }).click();
  await page.locator(".owner-grid-shell").waitFor({ state: "visible" });
  await page.locator(".owner-grid-loading").waitFor({ state: "detached" }).catch(() => {});
}

async function closeBooking(page) {
  if (await page.locator(".owner-booking-modal").count()) {
    await page.locator(".owner-booking-head .owner-quiet-btn").click();
    await page.locator(".owner-booking-modal").waitFor({ state: "detached" });
  }
}

async function waitForNightPreview(page, nights) {
  await page.waitForFunction((expected) => {
    const facts = document.querySelector(".owner-stay-facts")?.textContent || "";
    const loading = document.querySelector(".owner-price-card")?.textContent?.includes("Проверяем…");
    return !loading && new RegExp(`Ночей\\s*${expected}`).test(facts);
  }, nights, { timeout: 10000 });
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
try {
  await login(page);

  const rows = page.locator(".owner-room-row");
  assert(await rows.count() === 84, `expected 84 physical room rows, got ${await rows.count()}`);
  assert(await page.locator(".owner-pms-tools-panel").count() === 0, "operational panels must be collapsed by default");
  assert(await page.locator(".owner-pms-advanced-panel").count() === 0, "advanced V9 must be collapsed by default");

  assert(await page.locator(".owner-day-head").count() === 31, `default owner window must render 31 day columns, got ${await page.locator(".owner-day-head").count()}`);
  assert(await page.locator('.owner-grid-scroll[data-window-days="31"]').count() === 1, "owner grid must expose the actual 31-day window state");

  const gridMetrics31 = await page.locator(".owner-grid-scroll").evaluate((node) => ({
    clientWidth: node.clientWidth,
    scrollWidth: node.scrollWidth,
    clientHeight: node.clientHeight,
  }));
  assert(gridMetrics31.clientHeight >= 540, `owner grid viewport is too short for desktop workflow: ${JSON.stringify(gridMetrics31)}`);
  assert(gridMetrics31.scrollWidth <= gridMetrics31.clientWidth + 2, `31-day owner grid must fit the 1440px desktop viewport without hiding days behind horizontal scrolling: ${JSON.stringify(gridMetrics31)}`);

  await page.getByRole("button", { name: "Показать 14 дней" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".owner-day-head").length === 14);
  assert(await page.locator(".owner-day-head").count() === 14, "14-day switch must render exactly 14 day columns");
  await page.getByRole("button", { name: "Показать 31 дней" }).click();
  await page.waitForFunction(() => document.querySelectorAll(".owner-day-head").length === 31);
  assert(await page.locator(".owner-day-head").count() === 31, "31-day switch must render exactly 31 day columns, not keep the 14-day window");

  const room112 = page.locator(".owner-room-label", { hasText: "112" }).first();
  await room112.scrollIntoViewIfNeeded();
  const room112Text = (await room112.innerText()).replace(/\s+/g, " ").trim();
  assert(room112Text.includes("112 (1сп+1сп)"), `room 112 must expose the familiar owner shorthand in one label, got ${JSON.stringify(room112Text)}`);
  assert(await page.getByText("2х улучшенный", { exact: true }).count() > 0, "owner category heading 2х улучшенный is missing");

  const firstNight = page.locator('.owner-night-cell[data-room-code="112"][data-free="true"]').first();
  const box = await firstNight.boundingBox();
  assert(box && box.width <= 32 && box.height <= 40, `31-day owner night cell is not compact enough: ${JSON.stringify(box)}`);

  await firstNight.click();
  await page.locator(".owner-booking-modal").waitFor({ state: "visible" });
  await waitForNightPreview(page, 1);
  const oneNightFacts = await page.locator(".owner-stay-facts").innerText();
  assert(/Ночей\s*1/.test(oneNightFacts), `one selected square must preview 1 night: ${JSON.stringify(oneNightFacts)}`);
  assert((await page.locator(".owner-nightly-prices span").count()) === 1, "one-night preview must contain exactly one nightly rate");
  await closeBooking(page);

  const freeCells = page.locator('.owner-night-cell[data-room-code="112"][data-free="true"]');
  assert(await freeCells.count() >= 4, "room 112 needs at least four free visible nights for browser acceptance");
  const first = freeCells.nth(0);
  const fourth = freeCells.nth(3);
  const firstBox = await first.boundingBox();
  const fourthBox = await fourth.boundingBox();
  assert(firstBox && fourthBox, "could not resolve drag cell geometry");
  await page.mouse.move(firstBox.x + firstBox.width / 2, firstBox.y + firstBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(fourthBox.x + fourthBox.width / 2, fourthBox.y + fourthBox.height / 2, { steps: 8 });
  await page.mouse.up();
  await page.locator(".owner-booking-modal").waitFor({ state: "visible" });
  await waitForNightPreview(page, 4);
  const multiFacts = await page.locator(".owner-stay-facts").innerText();
  assert(/Ночей\s*4/.test(multiFacts), `drag across four cells must preview 4 nights: ${JSON.stringify(multiFacts)}`);
  assert((await page.locator(".owner-nightly-prices span").count()) === 4, "four-night preview must contain four nightly rates");

  const guestName = "Browser Owner Grid Guest";
  await page.locator('input[placeholder="Как обращаться"]').fill(guestName);
  await page.locator('input[placeholder="+996 ..."]').fill("+996555020202");
  const submit = page.getByRole("button", { name: "Подтвердить бронь" });
  await submit.waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const button = Array.from(document.querySelectorAll("button")).find((item) => item.textContent?.includes("Подтвердить бронь"));
    return Boolean(button && !button.disabled);
  });
  await submit.click();
  await page.getByText("Бронь создана", { exact: true }).waitFor({ state: "visible" });
  const createdText = await page.locator(".owner-created").innerText();
  assert(createdText.includes("платеж не создавался автоматически"), "browser commit must state that payment was not fabricated");
  const bookingNumber = (await page.locator(".owner-created b").innerText()).trim();
  assert(Boolean(bookingNumber), "created booking number is missing");
  await page.getByRole("button", { name: "Готово" }).click();
  await page.locator(".owner-booking-modal").waitFor({ state: "detached" });

  await page.waitForFunction((name) => Array.from(document.querySelectorAll(".owner-booking-bar strong")).some((node) => node.textContent?.includes(name)), guestName, { timeout: 10000 });

  const reservation = await page.evaluate(async (targetBooking) => {
    const response = await fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" });
    const body = await response.json();
    return (body.items || []).find((item) => item.bookingNumber === targetBooking) || null;
  }, bookingNumber);
  assert(reservation?.id, `created reservation ${bookingNumber} is missing from reception truth`);
  assert(reservation.paidKgs === 0, `new owner-grid reservation must start without fabricated payment, got paid=${reservation.paidKgs}`);

  const paymentResult = await page.evaluate(async ({ reservationId, idempotencyKey }) => {
    const response = await fetch(`/core/api/v1/admin/booking/reservations/${reservationId}/payments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount_kgs: 5000,
        method: "CASH",
        external_ref: "OWNER-GRID-BROWSER-5000",
        note: "Owner workflow regression",
        idempotency_key: idempotencyKey,
      }),
    });
    return { status: response.status, body: await response.json() };
  }, { reservationId: reservation.id, idempotencyKey: `owner-grid-browser-${reservation.id}-5000` });

  assert(paymentResult.status === 201, `recording 5000 payment failed: ${paymentResult.status} ${JSON.stringify(paymentResult.body)}`);
  assert(paymentResult.body?.payment?.amount_kgs === 5000, `payment fact must stay exactly 5000, got ${JSON.stringify(paymentResult.body)}`);
  assert(paymentResult.body?.finance?.paid_kgs === 5000, `paid total must be exactly 5000 after one payment, got ${JSON.stringify(paymentResult.body?.finance)}`);
  assert(paymentResult.body?.finance?.remaining_kgs === Math.max(reservation.totalKgs - 5000, 0), `remaining balance must be total minus 5000, got ${JSON.stringify(paymentResult.body?.finance)}`);

  await page.locator(".owner-refresh").click();
  await page.waitForFunction((name) => {
    const bar = Array.from(document.querySelectorAll(".owner-booking-bar")).find((node) => node.textContent?.includes(name));
    return bar?.getAttribute("data-paid-kgs") === "5000";
  }, guestName, { timeout: 10000 });

  const bookingBar = page.locator(".owner-booking-bar", { hasText: guestName }).first();
  const bookingText = (await bookingBar.innerText()).replace(/\s+/g, " ").trim();
  assert(bookingText.includes("Опл. 5 000"), `booking bar must show the actual 5000 payment fact, not only the remaining balance: ${JSON.stringify(bookingText)}`);
  const bookingTitle = await bookingBar.getAttribute("title");
  assert(bookingTitle?.includes("Оплачено 5 000 сом"), `booking tooltip must preserve paid amount: ${JSON.stringify(bookingTitle)}`);
  assert(bookingTitle?.includes("Остаток"), `booking tooltip must show remaining balance separately: ${JSON.stringify(bookingTitle)}`);

  await page.getByRole("button", { name: "Операционный центр" }).click();
  await page.locator(".owner-pms-tools-panel").waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Скрыть операционный центр" }).click();
  assert(await page.locator(".owner-pms-tools-panel").count() === 0, "operational center must collapse again");

  await page.getByRole("button", { name: "Перенос / разрез / расширенная V9" }).click();
  await page.locator(".owner-pms-advanced-panel").waitFor({ state: "visible" });
  assert(await page.locator(".v8-board").count() > 0 || await page.locator(".v8-shell").count() > 0, "existing advanced V9 chessboard is not preserved");

  console.log("PASS: owner PMS browser acceptance (84 rooms, exact legacy shorthand, 14/31 windows, full desktop 31-day viewport, compact cells, 1-night click, 4-night drag, Core preview, 5000 payment fact vs remaining balance, collapsed tools, advanced V9 preserved)");
} finally {
  await browser.close();
}
