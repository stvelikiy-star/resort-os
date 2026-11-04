// Real shared Admin Next/Inbox browser on one TLS origin and two PostgreSQL hotels.
// No mocked HTTP API routes, provider transport or AI model.
import assert from "node:assert/strict";
import { chromium, request } from "playwright";

const BASE = "https://localhost:18447";
assert.equal(process.env.MARINA_SHARED_WHATSAPP_BROWSER_CI_CONFIRM,
  "DISPOSABLE_TWO_HOTEL_WHATSAPP_BROWSER_ONLY");
const pwd = process.env.MARINA_SHARED_BROWSER_CI_PASSWORD;
const adapters = JSON.parse(process.env.MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON || "[]");
assert(pwd?.startsWith("synthetic-ci-only-") && adapters.length === 2);
const adapter = Object.fromEntries(adapters.map(a => [a.property_code.slice(-1), a]));

const provider = await request.newContext({ ignoreHTTPSErrors: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 390, height: 844 } });
const page = await context.newPage();

async function assertStatus(response, status, name) {
  assert.equal(response.status(), status,
    name + " expected " + status + " got " + response.status() +
    " " + (await response.text()).slice(0, 220));
  return response.json().catch(() => ({}));
}

async function ingest(hotel) {
  return assertStatus(await provider.post(BASE + "/core/api/v1/automation/inbox/messages", {
    headers: { "X-Resort-Service-Key": adapter[hotel].service_key },
    data: {
      idempotency_key: "shared-wa-ui-ci-" + hotel + "-inbound",
      channel_code: "WA_MAIN",
      channel_kind: "WHATSAPP",
      channel_display_name: "WhatsApp",
      external_account_id: adapter[hotel].external_account_id,
      external_conversation_id: "one-identical-chat-id-for-both",
      external_message_id: "one-identical-message-id-for-both",
      sender_type: "GUEST",
      direction: "INBOUND",
      contact_name: "CI WhatsApp Guest " + hotel,
      text: "SYNTHETIC-WHATSAPP-" + hotel + "-ONLY",
      delivery_status: "RECEIVED",
    },
  }), 201, "Hotel " + hotel + " inbound");
}

async function login(hotel, role) {
  const r = await context.request.post(BASE + "/core/api/v1/auth/login", {
    data: {
      tenant_code: "tenant_" + hotel.toLowerCase(), property_code: "HOTEL_" + hotel,
      username: role.toLowerCase(), password: pwd,
    },
  });
  const user = await assertStatus(r, 200, "login " + hotel + " " + role);
  assert.equal(user.property_code, "HOTEL_" + hotel);
}

async function verifyHotel(hotel, role) {
  await page.goto(BASE + "/shared-whatsapp", { waitUntil: "domcontentloaded" });
  try {
    await page.getByRole("heading", { name: "Диалоги WhatsApp" }).waitFor({ timeout: 20000 });
  } catch (error) {
    console.error("WhatsApp workspace render debug:", await page.locator("body").innerText().catch(() => "<unavailable>"));
    throw error;
  }
  const status = await page.locator('section[aria-label="WhatsApp своей гостиницы"] p[role="status"]').innerText();
  assert.match(status, new RegExp("HOTEL_" + hotel), "Hotel header: " + status);
  assert.match(status, new RegExp(role), "Role header: " + status);
  await page.locator(".inbox-row").getByText("CI WhatsApp Guest " + hotel).waitFor({ timeout: 20000 });
  const foreign = hotel === "A" ? "B" : "A";
  assert.equal(await page.getByText("CI WhatsApp Guest " + foreign).count(), 0,
    "Foreign hotel contact leaked into " + hotel + " browser");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 8);
  assert.equal(overflow, false, "WhatsApp screen overflowing 390px viewport");
}

try {
  const first = await ingest("A");
  const second = await ingest("B");
  assert.notEqual(first.conversation_id, second.conversation_id);

  await page.goto(BASE + "/shared-whatsapp", { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Нужен вход в гостиницу" }).waitFor({ timeout: 20000 });

  await login("A", "OWNER");
  await verifyHotel("A", "OWNER");
  await page.locator(".inbox-row").first().click();
  await page.getByRole("dialog").getByText("SYNTHETIC-WHATSAPP-A-ONLY").waitFor({ timeout: 20000 });
  await page.getByRole("dialog").getByRole("button", { name: "Закрыть" }).click();

  // SAME browser cookie jar, switched to unrelated owner HOTEL_B.
  await login("B", "OWNER");
  await verifyHotel("B", "OWNER");
  await page.locator(".inbox-row").first().click();
  await page.getByRole("dialog").getByText("SYNTHETIC-WHATSAPP-B-ONLY").waitFor({ timeout: 20000 });
  assert.equal(await page.getByText("SYNTHETIC-WHATSAPP-A-ONLY").count(), 0);
  await page.getByRole("dialog").getByRole("button", { name: "Закрыть" }).click();

  // Reception uses the same hotel Inbox but cannot provision Green API QR.
  await login("B", "RECEPTION");
  await verifyHotel("B", "RECEPTION");
  assert.equal(await page.getByRole("button", { name: "Получить QR-код" }).count(), 0);
  await page.locator(".inbox-row").first().click();
  await page.getByRole("dialog").getByRole("button", { name: "Взять диалог" }).click();
  await page.getByRole("dialog").getByText("Synthetic RECEPTION B").waitFor({ timeout: 20000 });
  await page.getByRole("dialog").locator(".internal-note-form textarea").fill("B receptionist human handoff note");
  await page.getByRole("dialog").getByRole("button", { name: "Добавить заметку" }).click();
  await page.getByRole("dialog").getByText("B receptionist human handoff note").waitFor({ timeout: 20000 });
  assert.equal(await page.getByRole("button", { name: "Отправить в WhatsApp" }).count(), 0);

  // Authentication loss unmounts prior hotel's Inbox and message history.
  await assertStatus(await context.request.post(BASE + "/core/api/v1/auth/logout"), 200, "logout");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Нужен вход в гостиницу" }).waitFor({ timeout: 20000 });
  assert.equal(await page.getByText("CI WhatsApp Guest B").count(), 0);
  console.log("PASS: real two-hotel shared WhatsApp Admin UI, same TLS origin and cookie jar, "
    + "owner switch isolation, reception handoff/notes, no simulated provider sending");
} finally {
  await context.close();
  await browser.close();
  await provider.dispose();
}
