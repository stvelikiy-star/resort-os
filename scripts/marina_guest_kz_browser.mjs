import { chromium } from "playwright";

const BASE_URL = process.env.PUBLIC_BASE_URL || "http://127.0.0.1:3000";
const TOKEN = "marina-kz-browser-token";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function installMocks(page) {
  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}/requests**`, async (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
    }
    return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ id: "request-test" }) });
  });
  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}/service-policy**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        scheduled_housekeeping_interval_days: 3,
        scheduled_linen_change_included: true,
        on_demand_housekeeping_price_kgs: 1500,
        on_demand_linen_price_kgs: 1500,
      }),
    });
  });
  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}/kitchen/menu**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ service_date: "2026-09-29", items: [], meal_ordering: {}, delivery: { enabled: true, fee_kgs: 200 } }),
    });
  });
  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}/offers**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        qr_valid: true,
        authenticated: true,
        verification_required: false,
        active_stay: true,
        room: { code: "101", name: "101", room_type_name: "Стандарт" },
        guest: { first_name: "Ayan" },
        stay: { check_in: "2026-09-29", check_out: "2026-10-02" },
      }),
    });
  });
}

async function expectLocale(page, locale, htmlLang, visibleText) {
  await page.waitForFunction((expected) => document.documentElement.lang === expected, htmlLang);
  assert((await page.locator("html").getAttribute("lang")) === htmlLang, `${locale}: html lang is not ${htmlLang}`);
  assert((await page.locator("body").innerText()).includes(visibleText), `${locale}: missing visible text ${visibleText}`);
  const button = page.getByRole("button", { name: locale.toUpperCase(), exact: true });
  await button.waitFor({ state: "visible" });
  assert((await button.getAttribute("aria-pressed")) === "true", `${locale}: language button is not active`);
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await installMocks(page);

  let response = await page.goto(`${BASE_URL}/g/${TOKEN}?lang=kz`, { waitUntil: "networkidle" });
  assert(response && response.status() === 200, "Guest KZ route did not return HTTP 200");
  await expectLocale(page, "kz", "kk", "Қош келдіңіз");

  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expectLocale(page, "en", "en", "Welcome");

  await page.getByRole("button", { name: "KZ", exact: true }).click();
  await expectLocale(page, "kz", "kk", "Қош келдіңіз");

  response = await page.goto(`${BASE_URL}/g/${TOKEN}`, { waitUntil: "networkidle" });
  assert(response && response.status() === 200, "Guest persisted-locale route did not return HTTP 200");
  await expectLocale(page, "kz", "kk", "Қош келдіңіз");

  const stored = await page.evaluate(() => ({
    guest: localStorage.getItem("three-crowns-guest-language"),
    site: localStorage.getItem("three-crowns-site-language"),
  }));
  assert(stored.guest === "kz" && stored.site === "kz", `KZ persistence failed: ${JSON.stringify(stored)}`);

  console.log("MARINA_GUEST_KZ_BROWSER_PASS switch=PASS html-lang=kk persistence=PASS mobile=PASS");
  await context.close();
} finally {
  await browser.close();
}
