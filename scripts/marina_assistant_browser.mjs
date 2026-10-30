import assert from "node:assert/strict";
import { chromium } from "playwright";

const username = process.env.BOOTSTRAP_OWNER_USERNAME;
const password = process.env.BOOTSTRAP_OWNER_PASSWORD;
const surfaces = [
  process.env.MARINA_ADMIN_BROWSER_URL || "http://127.0.0.1:13001",
  process.env.MARINA_STAFF_BROWSER_URL || "http://127.0.0.1:13002",
];
assert(username && password, "Synthetic owner credentials required");
for (const base of surfaces) {
  const url = new URL(base);
  assert(url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname), "Disposable localhost only");
}
const copy = {
  ru: ["Открыть MARINA AI", "Объясни этот экран", "временно недоступен"],
  kg: ["MARINA AI ачуу", "Бул экранды түшүндүр", "убактылуу жеткиликсиз"],
  kz: ["MARINA AI ашу", "Бұл экранды түсіндір", "уақытша қолжетімсіз"],
  en: ["Open MARINA AI", "Explain this screen", "temporarily unavailable"],
};
const browser = await chromium.launch({ headless: true });
try {
  for (const base of surfaces) {
    const context = await browser.newContext();
    const login = await context.request.post(`${base}/core/api/v1/auth/login`, { data: { username, password } });
    assert.equal(login.status(), 200, "Real synthetic owner login must succeed");
    const page = await context.newPage();
    // This is the ordinary web login flow, not a Telegram Mini App. Keep an
    // unrelated external SDK/network policy from breaking the assistant test.
    await page.route("https://telegram.org/js/telegram-web-app.js", route => route.fulfill({
      contentType: "application/javascript", body: "/* Non-Telegram browser fixture. */",
    }));
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    for (const [locale, [open, quick, unavailable]] of Object.entries(copy)) {
      await page.setViewportSize(locale === "ru" ? { width: 1440, height: 900 } : { width: 390, height: 844 });
      await page.goto(base, { waitUntil: "networkidle" });
      const targetLocale = locale === "kg" ? "ky" : locale === "kz" ? "kk" : locale;
      const languageButton = page.getByRole("button", { name: locale.toUpperCase(), exact: true });
      // A server-rendered button may be clickable before client hydration.
      // Wait for the locale handler to become active; repeat the *same* click
      // only when hydration swallowed it, not after a successful language switch.
      for (let attempt = 0; attempt < 4; attempt += 1) {
        if (await page.evaluate(expected => document.documentElement.lang.toLowerCase() === expected, targetLocale)) break;
        await languageButton.click();
        try {
          await page.waitForFunction(expected => document.documentElement.lang.toLowerCase() === expected, targetLocale, { timeout: 5000 });
          break;
        } catch (error) {
          if (attempt === 3) throw new Error(`Locale ${locale} did not activate on ${base} after hydration retries: ${error.message}`);
        }
      }
      assert.equal(await page.locator("html").getAttribute("lang"), targetLocale);
      await page.getByRole("button", { name: open, exact: true }).click();
      const panel = page.getByRole("region", { name: "MARINA AI", exact: true });
      const received = page.waitForResponse(response => response.request().method() === "POST"
        && new URL(response.url()).pathname === "/core/api/v1/assistant/chat");
      await panel.getByRole("button", { name: quick, exact: true }).click();
      const response = await received;
      const payload = response.request().postDataJSON();
      assert.equal(payload.locale, locale);
      assert.deepEqual(payload.messages, [{ role: "user", content: quick }], "First question must contain no blank placeholder");
      assert.equal(response.status(), 503, "Provider-free CI must reach the real provider-not-configured boundary, never 422");
      await panel.getByText(new RegExp(unavailable)).waitFor();
      assert.deepEqual(errors, []);
    }
    await context.close();
  }
  console.log("MARINA_ASSISTANT_BROWSER_PASS: Admin and Staff, four locales, first question reaches real API, honest provider error, no runtime errors");
} finally {
  await browser.close();
}
