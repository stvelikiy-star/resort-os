import { chromium } from "playwright";

const BASE_URL = process.env.PUBLIC_BASE_URL || "http://127.0.0.1:3000";
const TOKEN = "marina-i18n-browser-token";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const expectations = {
  ru: {
    html: "ru",
    welcome: "Добро пожаловать",
    housekeeping: "Плановая уборка и дополнительные услуги",
    market: "Всё, что можно заказать — в одном месте",
    menu: "Овсяная каша с фруктами",
    offer: "SPA-вечер",
    forbidden: ["Кош келиңиз", "Қош келдіңіз", "Welcome"],
  },
  kg: {
    html: "ky",
    welcome: "Кош келиңиз",
    housekeeping: "Пландуу тазалоо жана кошумча кызматтар",
    market: "Буйрутма берүүгө боло турган кызматтардын баары бир жерде",
    menu: "Мөмөлүү сулу боткосу",
    offer: "SPA кечеси",
    forbidden: ["Добро пожаловать", "Қош келдіңіз", "Welcome"],
  },
  kz: {
    html: "kk",
    welcome: "Қош келдіңіз",
    housekeeping: "Жоспарлы тазалау және қосымша қызметтер",
    market: "Тапсырыс беруге болатынның бәрі — бір жерде",
    menu: "Жеміс қосылған сұлы ботқасы",
    offer: "SPA кеші",
    forbidden: ["Добро пожаловать", "Кош келиңиз", "Welcome"],
  },
  en: {
    html: "en",
    welcome: "Welcome",
    housekeeping: "Scheduled cleaning and extra services",
    market: "Everything you can request, in one place",
    menu: "Oatmeal with fruit",
    offer: "SPA evening",
    forbidden: ["Добро пожаловать", "Кош келиңиз", "Қош келдіңіз"],
  },
};

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
      body: JSON.stringify({
        service_date: "2026-09-29",
        items: [{
          id: "11111111-1111-1111-1111-111111111111",
          code: "PORRIDGE",
          category: "BREAKFAST",
          name_ru: "Овсяная каша с фруктами",
          name_kg: "Мөмөлүү сулу боткосу",
          name_kz: "Жеміс қосылған сұлы ботқасы",
          name_en: "Oatmeal with fruit",
          price_kgs: 190,
          is_active: true,
          is_draft: false,
          sort_order: 10,
          meal_types: ["BREAKFAST"],
        }],
        meal_ordering: {
          BREAKFAST: { configured: true, open: true, start: "10:00", cutoff_at: "2099-09-29T09:00:00+06:00", cutoff_minutes: 60 },
          LUNCH: { configured: true, open: true, start: "14:00", cutoff_at: "2099-09-29T13:00:00+06:00", cutoff_minutes: 60 },
          DINNER: { configured: true, open: true, start: "19:00", cutoff_at: "2099-09-29T18:00:00+06:00", cutoff_minutes: 60 },
          OTHER: { configured: true, open: true, start: null, cutoff_at: null, cutoff_minutes: 60 },
        },
        delivery: { enabled: true, fee_kgs: 200 },
      }),
    });
  });

  await page.route(`**/core/api/v1/guest-os/rooms/${TOKEN}/offers**`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [{
          id: "22222222-2222-2222-2222-222222222222",
          code: "SPA_EVENING",
          title_ru: "SPA-вечер",
          title_kg: "SPA кечеси",
          title_kz: "SPA кеші",
          title_en: "SPA evening",
          hook_ru: "Спокойный вечер в SPA.",
          hook_kg: "SPAда тынч кеч.",
          hook_kz: "SPA-дағы тыныш кеш.",
          hook_en: "A calm evening at the SPA.",
          cta_ru: "Запросить",
          cta_kg: "Өтүнмө берүү",
          cta_kz: "Сұрау",
          cta_en: "Request",
          action_type: "GUEST_REQUEST",
          request_code: "SAUNA",
        }],
      }),
    });
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

async function expectLocale(page, locale) {
  const e = expectations[locale];
  await page.waitForFunction((expected) => document.documentElement.lang === expected, e.html);
  await page.waitForFunction(
    ({ welcome, housekeeping, market, menu, offer }) => {
      const body = document.body.innerText;
      return [welcome, housekeeping, market, menu, offer].every((text) => body.includes(text));
    },
    { welcome: e.welcome, housekeeping: e.housekeeping, market: e.market, menu: e.menu, offer: e.offer },
  );

  const body = await page.locator("body").innerText();
  assert((await page.locator("html").getAttribute("lang")) === e.html, `${locale}: html lang is not ${e.html}`);
  for (const marker of [e.welcome, e.housekeeping, e.market, e.menu, e.offer]) {
    assert(body.includes(marker), `${locale}: missing ${marker}`);
  }
  for (const old of e.forbidden) {
    assert(!body.includes(old), `${locale}: mixed-language marker is still visible: ${old}`);
  }

  const button = page.getByRole("button", { name: locale.toUpperCase(), exact: true });
  await button.waitFor({ state: "visible" });
  assert((await button.getAttribute("aria-pressed")) === "true", `${locale}: language button is not active`);
}

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of [
    { width: 1440, height: 900, isMobile: false, hasTouch: false },
    { width: 390, height: 844, isMobile: true, hasTouch: true },
  ]) {
    const context = await browser.newContext(viewport);
    const page = await context.newPage();
    await installMocks(page);

    let response = await page.goto(`${BASE_URL}/g/${TOKEN}?lang=kz`, { waitUntil: "networkidle" });
    assert(response && response.status() === 200, "Guest KZ route did not return HTTP 200");
    await expectLocale(page, "kz");

    for (const locale of ["ru", "kg", "en", "kz"]) {
      await page.getByRole("button", { name: locale.toUpperCase(), exact: true }).click();
      await expectLocale(page, locale);
    }

    response = await page.goto(`${BASE_URL}/g/${TOKEN}`, { waitUntil: "networkidle" });
    assert(response && response.status() === 200, "Guest persisted-locale route did not return HTTP 200");
    await expectLocale(page, "kz");

    const stored = await page.evaluate(() => ({
      marina: localStorage.getItem("marina-smart-guest-locale"),
      guest: localStorage.getItem("marina-smart-guest-locale"),
      site: localStorage.getItem("marina-smart-site-language"),
    }));
    assert(
      stored.marina === "kz" && stored.guest === "kz" && stored.site === "kz",
      `KZ persistence failed: ${JSON.stringify(stored)}`,
    );

    await context.close();
  }

  console.log("MARINA_GUEST_I18N_BROWSER_PASS ru=PASS kg=PASS kz=PASS en=PASS sync=PASS persistence=PASS desktop=PASS mobile=PASS");
} finally {
  await browser.close();
}
