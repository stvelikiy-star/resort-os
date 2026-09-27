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

  console.log("PASS: MARINA SMART owner navigation browser acceptance (" + primaryTabs.length + " primary + " + moreTabs.length + " secondary tabs; compact Ещё preserved; no React crash; no Core 5xx)");
} finally {
  await browser.close();
}
