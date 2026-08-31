import { chromium } from "playwright";

const BASE_URL = process.env.PUBLIC_BASE_URL || "http://127.0.0.1:3000";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function verifyServerHtml() {
  const response = await fetch(`${BASE_URL}/`, { redirect: "follow" });
  assert(response.ok, `SSR home returned HTTP ${response.status}`);
  const html = await response.text();
  const transfer = html.indexOf('data-service-code="TRANSFER"');
  const excursions = html.indexOf('data-service-code="EXCURSIONS"');
  assert(transfer >= 0, "SSR home is missing TRANSFER service card");
  assert(excursions >= 0, "SSR home is missing EXCURSIONS service card");
  assert(transfer < excursions, "SSR home must render TRANSFER before EXCURSIONS");
  assert(html.includes("Манас: седан 6 500 / минивен 7 500 сом"), "SSR home is missing owner-approved Manas transfer price");
  assert(html.includes("MIX TOUR.KG"), "SSR home is missing owner-approved 2026 tour source text");
  assert(!/30\s*%[^<]{0,120}предоплат|предоплат[^<]{0,120}30\s*%/i.test(html), "SSR home contains forbidden fixed 30% prepayment claim");
}

async function installCoreMocks(page) {
  await page.route("**/core/api/v1/booking/check-availability**", async (route) => {
    const url = new URL(route.request().url());
    const checkIn = url.searchParams.get("check_in") || "2026-09-01";
    const checkOut = url.searchParams.get("check_out") || "2026-09-03";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        check_in: checkIn,
        check_out: checkOut,
        nights: 2,
        adults: Number(url.searchParams.get("adults") || 2),
        children: Number(url.searchParams.get("children") || 0),
        results: [
          {
            room_type_id: "11111111-1111-1111-1111-111111111111",
            room_type_code: "DOUBLE_STANDARD_BASEMENT",
            room_type_name: "Двухместный стандарт, цоколь",
            capacity_adults: 2,
            capacity_children: null,
            children_capacity_confirmed: false,
            area: "20",
            available_count: 2,
            available_rooms: [
              { id: "22222222-2222-2222-2222-222222222222", code: "101" },
              { id: "33333333-3333-3333-3333-333333333333", code: "102" },
            ],
            pricing: {
              sellable: true,
              total_kgs: 12000,
              reason: null,
              nights: [
                { date: checkIn, price_kgs: 6000, meal_included: "NONE", status: "PRICED" },
                { date: checkOut, price_kgs: 6000, meal_included: "NONE", status: "PRICED" },
              ],
            },
          },
        ],
      }),
    });
  });

  await page.route("**/core/api/v1/booking/requests", async (route) => {
    assert(route.request().method() === "POST", "Booking request must use POST");
    const payload = route.request().postDataJSON();
    assert(payload.source === "WEB", "BookingRequest source must remain WEB");
    assert(payload.room_type_code === "DOUBLE_STANDARD_BASEMENT", "BookingRequest must preserve selected room type");
    assert(!Object.hasOwn(payload, "payment_confirmed"), "Public BookingRequest must not confirm payment");
    assert(!Object.hasOwn(payload, "prepayment_percent"), "Public BookingRequest must not invent a prepayment percent");
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "44444444-4444-4444-4444-444444444444" }),
    });
  });
}

async function serviceCodes(page) {
  await page.waitForSelector('.v3-extra-grid article[data-service-code="TRANSFER"]');
  await page.waitForSelector('.v3-extra-grid article[data-service-code="EXCURSIONS"]');
  return page.locator(".v3-extra-grid article").evaluateAll((cards) => cards.map((card) => card.dataset.serviceCode || ""));
}

async function assertServiceOrderAndLocale(page, locale, expectedHtmlLang) {
  await page.goto(`${BASE_URL}/${locale === "ru" ? "" : `?lang=${locale}`}`, { waitUntil: "networkidle" });
  const codes = await serviceCodes(page);
  const transfer = codes.indexOf("TRANSFER");
  const excursions = codes.indexOf("EXCURSIONS");
  assert(transfer >= 0 && excursions >= 0, `${locale}: service cards are incomplete`);
  assert(transfer < excursions, `${locale}: TRANSFER must render before EXCURSIONS`);
  const lang = await page.locator("html").getAttribute("lang");
  assert(lang === expectedHtmlLang, `${locale}: expected html lang=${expectedHtmlLang}, got ${lang}`);
  const transferText = await page.locator('[data-service-code="TRANSFER"]').innerText();
  assert(/6[\s,]500|6\s500/.test(transferText), `${locale}: transfer price is missing from hydrated UI`);
}

async function verifyDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  await installCoreMocks(page);

  await assertServiceOrderAndLocale(page, "ru", "ru");
  assert(await page.locator(".desktop-nav").isVisible(), "Desktop navigation is not visible");
  assert(await page.locator("#booking").isVisible(), "Booking widget is not visible on desktop");

  await assertServiceOrderAndLocale(page, "kg", "ky");
  await assertServiceOrderAndLocale(page, "en", "en");

  await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => {
    const input = document.querySelector('input[type="date"]');
    return Boolean(input && input.value);
  });
  await page.locator("form.booking-bar button.search-button").click();
  await page.waitForSelector("#availability .availability-card");
  assert((await page.locator("#availability").innerText()).includes("12 000") || (await page.locator("#availability").innerText()).includes("12 000"), "Availability result does not show mocked full-stay price");
  await page.locator(".availability-card button").click();
  await page.locator('input[autocomplete="name"]').fill("Тестовый гость");
  await page.locator('input[autocomplete="tel"]').fill("+996700000000");
  await page.locator("button.request-submit").click();
  await page.waitForSelector(".booking-notice.success");
  const successText = await page.locator(".booking-notice.success").innerText();
  assert(successText.includes("Заявка"), "Booking request success feedback is missing");
  assert(successText.includes("не является подтверждённой бронью"), "Booking request must explicitly remain unconfirmed");

  await context.close();
}

async function verifyMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const page = await context.newPage();
  await installCoreMocks(page);
  await page.goto(`${BASE_URL}/?lang=kg`, { waitUntil: "networkidle" });

  assert(await page.locator(".menu-toggle").isVisible(), "Mobile menu toggle is not visible");
  assert(await page.locator(".mobile-book").isVisible(), "Mobile booking CTA is not visible");
  const overflow = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
  assert(overflow.scrollWidth <= overflow.width + 2, `Mobile page has horizontal overflow: ${overflow.scrollWidth} > ${overflow.width}`);

  await page.locator(".menu-toggle").click();
  await page.waitForSelector("#mobile-menu.is-open");
  assert(await page.locator(".mobile-language").isVisible(), "Mobile language switcher is not visible when menu opens");

  const codes = await serviceCodes(page);
  assert(codes.indexOf("TRANSFER") < codes.indexOf("EXCURSIONS"), "Mobile KG services must keep TRANSFER before EXCURSIONS");
  await context.close();
}

const browser = await chromium.launch({ headless: true });
try {
  await verifyServerHtml();
  await verifyDesktop(browser);
  await verifyMobile(browser);
  console.log("PASS: public browser acceptance (SSR, desktop, mobile, RU/KG/EN, booking request UX)");
} finally {
  await browser.close();
}
