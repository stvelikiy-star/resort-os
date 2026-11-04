// Real Chromium acceptance against /g/[token] Next on one HTTPS origin,
// canonical Guest OS routes, and disposable PostgreSQL. No mocked APIs.
import assert from "node:assert/strict";
import { chromium, request } from "playwright";

const BASE = "https://localhost:18443";
const password = process.env.MARINA_SHARED_BROWSER_CI_PASSWORD;
assert.equal(process.env.MARINA_GUEST_QR_CI_CONFIRM, "ISOLATED_TWO_HOTEL_GUEST_QR_CI_ONLY");
assert(password?.startsWith("synthetic-ci-only-") && password.length >= 30);
const browser = await chromium.launch({ headless: true });
const owners = {};
const fixtures = {};

async function api(ctx, method, path, data = undefined) {
  const response = await ctx.fetch(BASE + path, { method, ...(data ? { data } : {}) });
  const body = await response.json().catch(() => null);
  return { status: response.status(), body };
}
function expectStatus(result, status, action) {
  assert.equal(result.status, status, action + " status " + result.status + ": " +
    JSON.stringify(result.body?.detail ?? null).slice(0, 200));
  return result.body;
}
async function prepare(hotel) {
  const suffix = hotel.toLowerCase(), code = "HOTEL_" + hotel;
  const ctx = await request.newContext({ ignoreHTTPSErrors: true, baseURL: BASE,
    extraHTTPHeaders: { "User-Agent": "marina-guest-browser-owner-" + suffix } });
  owners[hotel] = ctx;
  expectStatus(await api(ctx, "POST", "/api/v1/auth/login", {
    tenant_code: "tenant_" + suffix, property_code: code,
    username: "owner", password,
  }), 200, "owner login " + code);
  const me = expectStatus(await api(ctx, "GET", "/api/v1/auth/me"), 200, "owner identity");
  assert.equal(me.property_code, code);
  const list = expectStatus(await api(ctx, "GET", "/api/v1/admin/guest-os/room-qrs"), 200, "room registry");
  assert.equal(list.property, code);
  assert.equal(list.items.length, 1);
  const room = list.items[0];
  const issue = expectStatus(await api(ctx, "POST", "/api/v1/admin/guest-os/room-qrs/" + room.room_id + "/issue"), 201, "QR issue");
  assert(issue.public_url.startsWith(BASE + "/g/"));
  const today = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Bishkek" }));
  function isoWithOffset(days) {
    const date = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate() + days));
    return date.toISOString().slice(0, 10);
  }
  const body = { room_id: room.room_id, check_in: isoWithOffset(-1), check_out: isoWithOffset(1), adults: 1, children: 0 };
  const preview = expectStatus(await api(ctx, "POST", "/api/v1/admin/pms/reservations/new/preview", body), 200, "booking preview");
  assert(preview.can_commit && preview.pricing.source === "CORE_RATE");
  const reservation = expectStatus(await api(ctx, "POST", "/api/v1/admin/pms/reservations/new/commit", {
    ...body, guest_name: "Browser Hotel " + hotel + " Guest",
    phone: "+9965559920" + (hotel === "A" ? "01" : "02"),
    expected_total_kgs: preview.pricing.total_kgs, expected_pricing_source: preview.pricing.source,
  }), 201, "booking commit");
  const checkin = expectStatus(await api(ctx, "POST",
    "/api/v1/admin/stays/reservations/" + reservation.reservation_id + "/check-in"), 200, "check-in");
  assert.match(checkin.guest_access_pin, /^\d{6}$/);
  fixtures[hotel] = { hotel, url: issue.public_url, pin: checkin.guest_access_pin,
    room_code: room.room_code, reservation_id: reservation.reservation_id, property_id: me.property_id };
}
async function verifyPage(page, hotel) {
  const fixture = fixtures[hotel];
  await page.goto(fixture.url, { waitUntil: "domcontentloaded" });
  await page.locator(".concierge-auth").waitFor({ timeout: 20000 });
  const brand = await page.locator(".concierge-brand strong").textContent();
  assert.equal(brand?.trim(), "CI Hotel " + hotel);
  assert.equal(await page.locator(".concierge-hero").count(), 0);
  await page.locator(".concierge-auth input").fill(fixture.pin);
  await page.locator(".concierge-auth button").click();
  await page.locator(".concierge-hero").waitFor({ timeout: 20000 });
  assert.match(await page.locator(".concierge-hero").innerText(), new RegExp(fixture.room_code));
  assert.match(await page.locator(".concierge-hero").innerText(), new RegExp("Browser Hotel " + hotel));
}

try {
  await prepare("A");
  await prepare("B");
  assert.notEqual(fixtures.A.property_id, fixtures.B.property_id);
  assert.notEqual(fixtures.A.url, fixtures.B.url);
  // This IS the full shared Resort Core app: unrelated capabilities must
  // remain closed by the frozen RC3 boundary while Guest QR is admitted.
  for (const path of [
    "/api/v1/assistant/capabilities",
    "/api/v1/admin/inbox/conversations",
    "/api/v1/guest-os/rooms/" + fixtures.A.url.split("/").at(-1) + "/service-policy",
  ]) {
    expectStatus(await api(owners.A, "GET", path), 503, "unreviewed shared route");
  }
  expectStatus(await api(owners.A, "POST",
    "/api/v1/admin/guest-os/room-qrs/issue-missing", {}), 503,
    "unreviewed batch room QR issuance");
  // ONE cookie jar: Hotel A session must not unlock Hotel B.
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await verifyPage(page, "A");
  await page.goto(fixtures.B.url, { waitUntil: "domcontentloaded" });
  await page.locator(".concierge-auth").waitFor({ timeout: 20000 });
  assert.equal(await page.locator(".concierge-hero").count(), 0);
  assert.equal((await page.locator(".concierge-brand strong").textContent())?.trim(), "CI Hotel B");
  await page.locator(".concierge-auth input").fill(fixtures.B.pin);
  await page.locator(".concierge-auth button").click();
  await page.locator(".concierge-hero").waitFor({ timeout: 20000 });
  assert.match(await page.locator(".concierge-hero").innerText(), /Browser Hotel B Guest/);
  await page.goto(fixtures.A.url, { waitUntil: "domcontentloaded" });
  await page.locator(".concierge-auth").waitFor({ timeout: 20000 });
  assert.equal(await page.locator(".concierge-hero").count(), 0, "B cookie leaked A guest");
  await page.goto(fixtures.B.url, { waitUntil: "domcontentloaded" });
  await page.locator(".concierge-hero").waitFor({ timeout: 20000 });

  // The real shared RC4 UI advertises only server-reviewed nonfinancial
  // services. No unavailable AI or paid/provider action is clickable.
  const actions = page.locator(".concierge-actions button");
  assert.deepEqual(await actions.evaluateAll((nodes) =>
    nodes.map((n) => n.getAttribute("data-service-code"))), ["MAINTENANCE", "ADMIN"]);
  assert.equal(await page.locator('section[aria-label*="MARINA AI"]').count(), 0);
  await page.locator('.concierge-actions button[data-service-code="MAINTENANCE"]').click();
  await page.locator(".concierge-modal textarea").fill("Synthetic browser maintenance request B");
  await page.locator(".concierge-modal .concierge-submit").click();
  await page.locator(".concierge-request-list").getByText("Synthetic browser maintenance request B").waitFor({ timeout: 20000 });
  // No charge to the guest folio or provider dispatch is allowed in RC4.
  const paid = await context.request.post(
    BASE + "/api/v1/guest-os/rooms/" + fixtures.B.url.split("/").at(-1) + "/requests",
    { data: { request_code: "HOUSEKEEPING" } });
  assert.equal(paid.status(), 503, "paid housekeeping must remain blocked in RC4");
  assert.equal((await paid.json()).detail.code, "SHARED_GUEST_SERVICE_NOT_REVIEWED");

  // Fresh guest context for A; locale switches must not change hotel identity.
  const aContext = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
  const aPage = await aContext.newPage();
  await verifyPage(aPage, "A");
  assert.equal(await aPage.locator('section[aria-label*="MARINA AI"]').count(), 0);
  assert.equal(await aPage.locator(".concierge-actions button").count(), 2);
  for (const locale of ["KG", "EN", "RU"]) {
    await aPage.locator(".concierge-langs button").filter({ hasText: locale }).click();
    assert.equal((await aPage.locator(".concierge-brand strong").textContent())?.trim(), "CI Hotel A");
    assert.match(await aPage.locator(".concierge-hero").innerText(), /A101/);
    const overflow = await aPage.evaluate(() => document.documentElement.scrollWidth > innerWidth + 8);
    assert.equal(overflow, false, locale + " guest screen overflows mobile viewport");
  }
  await aPage.locator(".concierge-signout").click();
  await aPage.locator(".concierge-auth").waitFor({ timeout: 20000 });
  await aContext.close();

  for (const hotel of ["A", "B"]) {
    const checkout = expectStatus(await api(owners[hotel], "POST",
      "/api/v1/admin/stays/reservations/" + fixtures[hotel].reservation_id + "/check-out"), 200, "checkout " + hotel);
    assert.equal(checkout.status, "CHECKED_OUT");
  }
  await page.goto(fixtures.B.url, { waitUntil: "domcontentloaded" });
  await page.locator(".concierge-state").waitFor({ timeout: 20000 });
  assert.equal(await page.locator(".concierge-hero").count(), 0);
  await context.close();
  console.log("PASS: full shared Resort Core RC4 + real Next guest page over one HTTPS origin; "
    + "2 hotels, exact route 503s, secure PIN and cookies, no paid actions, RU/KG/EN, mobile, checkout");
} finally {
  await browser.close();
  for (const ctx of Object.values(owners)) await ctx.dispose();
}
