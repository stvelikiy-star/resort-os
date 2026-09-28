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
  await page.getByRole("button", { name: "Главная", exact: true }).waitFor({ state: "visible" });
}

const primaryTabs = [
  "Главная",
  "Супершахматка",
  "Ресепшен / Брони",
  "CRM / Заявки",
  "Финансы",
  "Сервис гостя",
  "Уборка / Ремонт",
  "Отчёты / Аналитика",
  "Настройки",
];

const moreTabs = [
  "Цены / Сезоны",
  "Групповая бронь",
  "Агенты",
  "Маркетинг",
  "Питание / Ресторан",
  "Настройки услуг",
  "Гости / История",
  "Офферы гостю",
  "QR номеров",
  "QR зон",
  "Рост / Отзывы",
  "Сайт / Контент",
  "Персонал",
  "Сообщения",
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
const coreServerErrors = [];

page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("response", (response) => {
  const url = response.url();
  if (url.includes("/core/api/v1/") && response.status() >= 500) {
    coreServerErrors.push(response.status() + " " + response.request().method() + " " + url);
  }
});

async function assertHealthy(label) {
  await page.waitForTimeout(450);
  const activeTexts = (await page.locator(".admin-tabs button.active").allTextContents()).map((value) => value.trim());
  assert(activeTexts.includes(label), label + ": navigation button did not become active; active=" + JSON.stringify(activeTexts));
  assert(await page.getByText("Application error", { exact: false }).count() === 0, label + ": Next.js Application error is visible");
  assert(await page.getByText("Unhandled Runtime Error", { exact: false }).count() === 0, label + ": runtime error UI is visible");
  assert(pageErrors.length === 0, label + ": browser page error(s): " + pageErrors.join(" | "));
  assert(coreServerErrors.length === 0, label + ": Core HTTP 5xx response(s): " + coreServerErrors.join(" | "));
}

try {
  await login(page);

  const localeExpectations = [
    { code: "RU", label: "Главная", finance: "Финансы", settings: "Настройки", more: "Ещё", rates: "Цены / Сезоны", htmlLang: "ru", stored: "ru" },
    { code: "KG", label: "Башкы", finance: "Каржы", settings: "Жөндөөлөр", more: "Дагы", rates: "Баалар / Сезондор", htmlLang: "ky", stored: "kg" },
    { code: "KZ", label: "Басты бет", finance: "Қаржы", settings: "Баптаулар", more: "Тағы", rates: "Бағалар / Маусымдар", htmlLang: "kk", stored: "kz" },
    { code: "EN", label: "Home", finance: "Finance", settings: "Settings", more: "More", rates: "Rates / Seasons", htmlLang: "en", stored: "en" },
  ];

  for (const item of localeExpectations) {
    const localeButton = page.locator(".admin-locale-switcher button", { hasText: item.code });
    assert(await localeButton.count() === 1, item.code + ": locale button is missing or duplicated");
    await localeButton.click();
    await page.getByRole("button", { name: item.label, exact: true }).waitFor({ state: "visible" });
    await page.getByRole("button", { name: item.finance, exact: true }).waitFor({ state: "visible" });
    await page.getByRole("button", { name: item.settings, exact: true }).waitFor({ state: "visible" });
    assert((await page.locator("details.admin-more-menu summary").innerText()).trim() === item.more, item.code + ": compact More label did not translate");
    assert(await page.locator("details.admin-more-menu button").filter({ hasText: item.rates }).count() === 1, item.code + ": secondary Rates / Seasons label did not translate");
    assert(await page.locator("html").getAttribute("lang") === item.htmlLang, item.code + ": unexpected html lang");
    assert(await page.evaluate(() => localStorage.getItem("three-crowns-admin-locale")) === item.stored, item.code + ": locale persistence key mismatch");
  }

  await page.getByRole("button", { name: "KZ", exact: true }).click();
  await page.getByRole("button", { name: "Басты бет", exact: true }).waitFor({ state: "visible" });
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Басты бет", exact: true }).waitFor({ state: "visible" });
  assert(await page.locator("html").getAttribute("lang") === "kk", "KZ: html lang was not restored after reload");
  assert(await page.evaluate(() => localStorage.getItem("three-crowns-admin-locale")) === "kz", "KZ: locale was not restored after reload");

  await page.getByRole("button", { name: "RU", exact: true }).click();
  await page.getByRole("button", { name: "Главная", exact: true }).waitFor({ state: "visible" });

  for (const label of primaryTabs) {
    const button = page.getByRole("button", { name: label, exact: true });
    assert(await button.count() === 1, label + ": expected exactly one primary navigation button");
    await button.click();
    await assertHealthy(label);
  }

  const more = page.locator("details.admin-more-menu");
  assert(await more.count() === 1, "Ещё: compact secondary menu is missing");
  const summary = more.locator("summary");
  assert((await summary.innerText()).trim() === "Ещё", "Ещё: unexpected summary label");

  for (const label of moreTabs) {
    await more.evaluate((node) => { node.open = true; });
    const button = page.getByRole("button", { name: label, exact: true });
    assert(await button.count() === 1, label + ": expected exactly one secondary navigation button");
    await button.click();
    await assertHealthy(label);
  }

  console.log("PASS: MARINA SMART owner navigation + RU/KG/KZ/EN browser acceptance (" + primaryTabs.length + " primary + " + moreTabs.length + " secondary tabs; locale persistence verified; compact Ещё preserved; no React crash; no Core 5xx)");
} finally {
  await browser.close();
}
