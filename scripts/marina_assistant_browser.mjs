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
      await page.getByRole("button", { name: locale.toUpperCase(), exact: true }).click();
      // Verify the page switched languages before asserting assistant translations.
      // A click may precede React hydration, especially after a fresh navigation.
      await page.waitForFunction(expected => document.documentElement.lang.toLowerCase() === expected, locale === "kg" ? "ky" : locale === "kz" ? "kk" : locale);
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
