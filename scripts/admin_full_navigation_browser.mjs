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
  "Шахматка",
  "Ресепшен",
  "Заявки",
  "WhatsApp / AI",
  "Цены / Сезоны",
  "Сервис гостя",
  "Уборка / Ремонт",
  "Главная",
  "Финансы",
];

const moreTabs = [
  "Групповая бронь",
  "Booking / Каналы продаж",
  "Агентства",
  "Все сообщения",
  "Гости / История",
  "Маркетинг",
  "Предложения гостям",
  "Отзывы / Рост",
  "Питание / Ресторан",
  "QR номеров",
  "QR зон",
  "Отчёты / Аналитика",
  "Персонал",
  "Знания отеля / MARINA AI",
  "Настройки услуг",
  "Сайт / Контент",
  "Настройки гостиницы",
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const pageErrors = [];
const coreServerErrors = [];

page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("response", (response) => {
  if (response.url().includes("/core/api/v1/") && response.status() >= 500) {
    coreServerErrors.push(response.status() + " " + response.request().method() + " " + response.url());
  }
});

async function assertHealthy(label) {
  await page.waitForTimeout(300);
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
  assert(await more.count() === 1, "All sections menu is missing");
  assert((await more.locator("summary").innerText()).trim() === "Все разделы", "Unexpected all-sections label");

  for (const label of moreTabs) {
    await more.evaluate((node) => { node.open = true; });
    const button = page.getByRole("button", { name: label, exact: true });
    assert(await button.count() === 1, label + ": expected exactly one secondary navigation button");
    await button.click();
    await assertHealthy(label);
  }

  await more.evaluate((node) => { node.open = true; });
  await page.getByRole("button", { name: "Booking / Каналы продаж", exact: true }).click();
  await page.getByRole("heading", { name: "Каналы продаж", exact: true }).waitFor();
  assert(await page.getByText("Автосинхронизация не подключена", { exact: true }).count() === 3,
    "Channel provider status must state that all three external connections are disabled");

  const mappingPanel = page.getByRole("region", {
    name: /Room and rate mapping|Сопоставление номеров и тарифов|Бөлмө жана тариф байланышы|Бөлме мен тариф сәйкестігі/,
  });
  const localizedLabels = {
    property: /External property ID|ID отеля на площадке|Платформадагы объект ID|Платформадағы нысан ID/,
    roomType: /External room type ID|ID категории на площадке|Платформадагы категория ID|Платформадағы санат ID/,
    ratePlan: /External rate plan ID|ID тарифа на площадке|Платформадагы тариф ID|Платформадағы тариф ID/,
    marinaRoomType: /MARINA room type|Категория MARINA|MARINA категориясы|MARINA санаты/,
    marinaRatePlan: /MARINA rate plan \(KGS\)|Тариф MARINA \(KGS\)|MARINA тарифи \(KGS\)|MARINA тарифі \(KGS\)/,
    save: /Save mapping|Сохранить связь|Байланышты сактоо|Байланысты сақтау/,
    saved: /Saved\. Platform is still disconnected\.|Сохранено\. Площадка ещё не подключена\.|Сакталды\. Платформа туташа элек\.|Сақталды\. Платформа әлі қосылмаған\./,
  };
  await mappingPanel.getByLabel(localizedLabels.property).fill("browser-synthetic");
  await mappingPanel.getByLabel(localizedLabels.roomType).fill("category-1");
  await mappingPanel.getByLabel(localizedLabels.ratePlan).fill("rate-1");
  for (const label of [localizedLabels.marinaRoomType, localizedLabels.marinaRatePlan]) {
    const select = mappingPanel.getByLabel(label);
    await select.locator("option").nth(1).waitFor({ state: "attached" });
    await select.selectOption({ index: 1 });
  }
  await mappingPanel.getByRole("button", { name: localizedLabels.save }).click();
  await mappingPanel.getByRole("status").filter({ hasText: localizedLabels.saved }).waitFor();
  assert(await mappingPanel.getByText("browser-synthetic / category-1 / rate-1", { exact: true }).count() === 1,
    "Mapping must persist exactly once while the provider stays disconnected");

  const csvPanel = page.getByRole("region", {
    name: /Bulk CSV import|Массовый импорт CSV|CSV топтук импорт|CSV топтық импорт/,
  });
  const csvInput = csvPanel.getByRole("textbox", {
    name: /CSV content|Содержимое CSV|CSV мазмуну|CSV мазмұны/,
  });
  const importButton = csvPanel.getByRole("button", { name: /Import|Импортировать|Импорттоо|Импорттау/ });
  assert(await importButton.isDisabled(), "CSV import must require a preview");
  await csvInput.fill("provider,external_id,revision,status\nAIRBNB,browser-preview-only,1,CANCELLED");
  await csvPanel.getByRole("button", { name: /Preview|Проверить|Текшерүү|Тексеру/ }).click();
  await csvPanel.getByRole("status").filter({ hasText: /Checked: 1|Проверено: 1|Текшерилди: 1|Тексерілді: 1/ }).waitFor();
  assert(await importButton.isEnabled(), "Successful CSV preview must enable import");
  await csvInput.fill("provider,external_id,revision,status\nAIRBNB,browser-preview-edited,1,CANCELLED");
  assert(await importButton.isDisabled(), "Editing CSV must invalidate the earlier preview");

  await page.setViewportSize({ width: 390, height: 844 });
  const channelPanel = page.locator("section[data-i18n-skip]");
  assert(await channelPanel.count() === 1, "Channel panel is missing on mobile");
  const bounds = await channelPanel.boundingBox();
  assert(bounds && bounds.width <= 390, "Channel panel overflows the mobile viewport");
  await assertHealthy("Booking / Каналы продаж");

  console.log("PASS: MARINA compact owner navigation, all enabled sections, channel disconnection truth, mapping persistence, CSV preview gating, responsive channel UI");
} finally {
  await browser.close();
}
