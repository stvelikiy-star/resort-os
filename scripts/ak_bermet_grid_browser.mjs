import { chromium } from "playwright";

const BASE = process.env.ADMIN_BASE_URL || "http://127.0.0.1:3001";
const USERNAME = process.env.BOOTSTRAP_OWNER_USERNAME || "akb-ci-owner";
const PASSWORD = process.env.BOOTSTRAP_OWNER_PASSWORD || "AKB-CI-Owner-Strong-2026";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

try {
  await page.goto(BASE, { waitUntil: "networkidle" });
  if (await page.locator('input[autocomplete="username"]').count()) {
    await page.locator('input[autocomplete="username"]').fill(USERNAME);
    await page.locator('input[autocomplete="current-password"]').fill(PASSWORD);
    await page.locator("button.login-button").click();
  }

  await page.getByRole("button", { name: "Супершахматка", exact: true }).waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Супершахматка", exact: true }).click();
  await page.locator(".owner-grid-shell").waitFor({ state: "visible" });
  await page.locator(".owner-grid-loading").waitFor({ state: "detached" }).catch(() => {});

  const allRows = page.locator(".owner-room-row");
  const cleanRows = page.locator(".owner-room-row.state-CLEAN");
  const blockedRows = page.locator(".owner-room-row.state-TECH_BLOCK");

  assert(await allRows.count() === 169, `AK BERMET grid expected 169 rooms, got ${await allRows.count()}`);
  assert(await cleanRows.count() === 137, `AK BERMET grid expected 137 CLEAN rooms, got ${await cleanRows.count()}`);
  assert(await blockedRows.count() === 32, `AK BERMET grid expected 32 TECH_BLOCK rooms, got ${await blockedRows.count()}`);

  const blockedFreeCells = blockedRows.locator('.owner-night-cell[data-free="true"]');
  assert(await blockedFreeCells.count() === 0, "TECH_BLOCK rooms must never render a free booking cell");

  assert(await page.locator(".owner-day-head").count() === 31, "AK BERMET owner grid must open with the 31-day view");
  const metrics = await page.locator(".owner-grid-scroll").evaluate((node) => ({
    clientWidth: node.clientWidth,
    scrollWidth: node.scrollWidth,
  }));
  assert(metrics.scrollWidth <= metrics.clientWidth + 2, `31-day grid must fit desktop width: ${JSON.stringify(metrics)}`);

  const freeCell = page.locator('.owner-room-row.state-CLEAN .owner-night-cell[data-free="true"]').first();
  await freeCell.scrollIntoViewIfNeeded();
  await freeCell.click();
  await page.locator(".owner-booking-modal").waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const facts = document.querySelector(".owner-stay-facts")?.textContent || "";
    const loading = document.querySelector(".owner-price-card")?.textContent?.includes("Проверяем…");
    return !loading && /Ночей\s*1/.test(facts);
  }, { timeout: 10000 });

  const facts = await page.locator(".owner-stay-facts").innerText();
  assert(/Ночей\s*1/.test(facts), `one square must represent one night: ${facts}`);
  const priceCard = page.locator(".owner-price-card", { hasText: "Расчёт MARINA SMART" });
  await priceCard.waitFor({ state: "visible", timeout: 10000 });
  assert(await priceCard.count() === 1, "sellable AK BERMET room must load exactly one MARINA SMART price preview");

  await page.locator(".owner-booking-head .owner-quiet-btn").click();
  await page.locator(".owner-booking-modal").waitFor({ state: "detached" });

  console.log("AK_BERMET_GRID_BROWSER_PASS rooms=169 clean=137 blocked=32 window=31 one-night-preview=PASS");
} finally {
  await browser.close();
}
