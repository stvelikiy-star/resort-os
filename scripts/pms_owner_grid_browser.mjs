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

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
try {
  await login(page);

  const rows = page.locator(".owner-room-row");
  assert(await rows.count() === 84, `expected 84 physical room rows, got ${await rows.count()}`);
  assert(await page.locator(".owner-pms-tools-panel").count() === 0, "operational panels must be collapsed by default");
  assert(await page.locator(".owner-pms-advanced-panel").count() === 0, "advanced V9 must be collapsed by default");

  const room112 = page.locator(".owner-room-label", { hasText: "112" }).first();
  await room112.scrollIntoViewIfNeeded();
  const room112Text = await room112.innerText();
  assert(room112Text.includes("1сп+1сп"), `room 112 must expose owner bed shorthand, got ${JSON.stringify(room112Text)}`);
  assert(await page.getByText("2х улучшенный", { exact: true }).count() > 0, "owner category heading 2х улучшенный is missing");

  const firstNight = page.locator('.owner-night-cell[data-room-code="112"][data-free="true"]').first();
  const box = await firstNight.boundingBox();
  assert(box && box.width <= 43 && box.height <= 40, `owner night cell is not compact: ${JSON.stringify(box)}`);

  await firstNight.click();
  await page.locator(".owner-booking-modal").waitFor({ state: "visible" });
  await page.locator(".owner-price-card").waitFor({ state: "visible" });
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
  await page.locator(".owner-price-card").waitFor({ state: "visible" });
  const multiFacts = await page.locator(".owner-stay-facts").innerText();
  assert(/Ночей\s*4/.test(multiFacts), `drag across four cells must preview 4 nights: ${JSON.stringify(multiFacts)}`);
  assert((await page.locator(".owner-nightly-prices span").count()) === 4, "four-night preview must contain four nightly rates");

  await page.locator('input[placeholder="Как обращаться"]').fill("Browser Owner Grid Guest");
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
  await page.getByRole("button", { name: "Готово" }).click();
  await page.locator(".owner-booking-modal").waitFor({ state: "detached" });

  await page.waitForFunction(() => Array.from(document.querySelectorAll(".owner-booking-bar strong")).some((node) => node.textContent?.includes("Browser Owner Grid Guest")), null, { timeout: 10000 });

  await page.getByRole("button", { name: "Операционный центр" }).click();
  await page.locator(".owner-pms-tools-panel").waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Скрыть операционный центр" }).click();
  assert(await page.locator(".owner-pms-tools-panel").count() === 0, "operational center must collapse again");

  await page.getByRole("button", { name: "Перенос / разрез / расширенная V9" }).click();
  await page.locator(".owner-pms-advanced-panel").waitFor({ state: "visible" });
  assert(await page.locator(".v8-board").count() > 0 || await page.locator(".v8-shell").count() > 0, "existing advanced V9 chessboard is not preserved");

  console.log("PASS: owner PMS browser acceptance (84 rooms, owner shorthand, compact cells, 1-night click, 4-night drag, Core preview, commit, collapsed tools, advanced V9 preserved)");
} finally {
  await browser.close();
}
