import assert from "node:assert/strict";
import { chromium } from "playwright";

const base = process.env.MARINA_GUEST_BROWSER_URL || "http://127.0.0.1:13000";
assert(["127.0.0.1", "localhost"].includes(new URL(base).hostname), "Local fixture browser only");
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  let property = { name: "Synthetic First Hotel", check_out_time: "10:30",
    official_contact: "+996700000001", whatsapp: "996700000002", checkout_instructions: "Synthetic instructions" };
  const token = "synthetic-guest-browser-token-only";
  await page.route("**/core/api/v1/**", async route => {
    if (new URL(route.request().url()).pathname === `/core/api/v1/guest-os/rooms/${token}`) {
      return route.fulfill({ json: { qr_valid: true, authenticated: true, active_stay: true,
        verification_required: false, property, room: { code: "101", name: "Synthetic room", room_type_name: "Standard" },
        guest: { first_name: "Synthetic" }, stay: { check_in: "2026-10-25", check_out: "2026-10-28" } } });
    }
    // Optional services are unavailable in this focused identity fixture.
    return route.fulfill({ status: 404, json: { detail: "Fixture service unavailable" } });
  });
  for (const locale of ["ru", "kg", "kz", "en"]) {
    await page.goto(`${base}/g/${token}?lang=${locale}`, { waitUntil: "networkidle" });
    await page.locator(".concierge-brand strong").filter({ hasText: property.name }).waitFor();
    assert.equal(await page.locator('a[href="tel:+996700000001"]').count(), 1);
    assert.equal(await page.locator('a[href="https://wa.me/996700000002"]').count(), 1);
    assert.match(await page.locator(".concierge-stay").innerText(), /10:30/);
    assert.equal(await page.locator('a[href*="996501772233"]').count(), 0);
    assert(!(await page.title()).includes("AK BERMET"));
  }
  property = { name: "Synthetic Second Hotel", check_out_time: null,
    official_contact: "Ask reception", whatsapp: "javascript:alert(1)", checkout_instructions: "" };
  await page.reload({ waitUntil: "networkidle" });
  await page.locator(".concierge-brand strong").filter({ hasText: property.name }).waitFor();
  assert.equal(await page.locator('.concierge-info-grid a[href^="tel:"]').count(), 0);
  assert.equal(await page.locator('.concierge-info-grid a[href*="wa.me"]').count(), 0);
  assert(!(await page.locator(".concierge-stay").innerText()).includes("10:30"));
  assert(!(await page.locator(".concierge-page").first().innerText()).includes("Synthetic First Hotel"));
  assert.deepEqual(errors, []);
  console.log("MARINA_GUEST_IDENTITY_BROWSER_PASS: four locales, mobile, hotel settings, contact safety, no stale hotel data");
} finally {
  await browser.close();
}
