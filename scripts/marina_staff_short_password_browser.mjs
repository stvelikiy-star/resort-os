import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.MARINA_STAFF_BROWSER_URL || "http://127.0.0.1:13002";
const url = new URL(base);
assert(url.protocol === "http:" && ["127.0.0.1", "localhost"].includes(url.hostname), "Disposable localhost only");
const browser = await chromium.launch({ headless: true });
try {
  for (const [index, path] of ["/", "/kitchen", "/waiter"].entries()) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.route("https://telegram.org/js/telegram-web-app.js", route => route.fulfill({
      contentType: "application/javascript", body: "/* Non-Telegram browser fixture. */",
    }));
    await page.goto(new URL(path, base).href, { waitUntil: "networkidle" });
    await page.locator('input[autocomplete="username"]').fill(`synthetic-short-login-${index}`);
    await page.locator('input[autocomplete="current-password"]').fill("abc");
    const responsePromise = page.waitForResponse(response => response.request().method() === "POST"
      && new URL(response.url()).pathname === "/core/api/v1/auth/login");
    await page.locator('input[autocomplete="current-password"]').press("Enter");
    const response = await responsePromise;
    assert.equal(response.status(), 401, `${path}: short password must reach the real auth API`);
    await context.close();
  }
  console.log("MARINA_SHORT_PASSWORD_BROWSER_PASS: staff, kitchen and waiter forms submit a short password to the API");
} finally {
  await browser.close();
}
