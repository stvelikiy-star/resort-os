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
    assert.deepEqual(response.request().postDataJSON(), {
      username: `synthetic-short-login-${index}`, password: "abc",
    }, `${path}: browser must submit the entered credentials`);
    assert.equal(response.status(), 422, `${path}: non-demo server must enforce the 8-character policy`);
    const body = await response.json();
    assert(body.detail.some(item => item.msg.includes("Password must contain at least 8 characters")),
      `${path}: expected the server password policy validation error`);
    await context.close();
  }
  console.log("MARINA_SHORT_PASSWORD_BROWSER_PASS: staff, kitchen and waiter forms submit a short password to the API");
} finally {
  await browser.close();
}
