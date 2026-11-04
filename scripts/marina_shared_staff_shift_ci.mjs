import assert from "node:assert/strict";
import { chromium } from "playwright";

const staff = "https://localhost:13444";
const admin = "https://localhost:13443";
const password = process.env.MARINA_STAGING_FIXTURE_PASSWORD;
const pin = process.env.MARINA_STAGING_CERT_SPKI;
assert(password?.startsWith("synthetic-ci-only-"));
assert.match(pin ?? "", /^[A-Za-z0-9+/]{43}=$/);

const browser = await chromium.launch({ args: ["--ignore-certificate-errors-spki-list=" + pin] });
async function api(page, path, method = "GET", body) {
  return page.evaluate(async ({ path, method, body }) => {
    const response = await fetch("/core/api/v1/" + path, {
      method,
      ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
    return { status: response.status, data: await response.json().catch(() => null) };
  }, { path, method, body });
}

try {
  const tasks = {};
  for (const suffix of ["A", "B"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(admin + "/shared-auth-preview");
    await page.getByLabel("Код отеля").waitFor();
    const login = await api(page, "auth/login", "POST", {
      username: "owner", password, tenant_code: "tenant_" + suffix.toLowerCase(), property_code: "HOTEL_" + suffix,
    });
    assert.equal(login.status, 200);
    tasks[suffix] = {};
    for (const type of ["HOUSEKEEPING", "MAINTENANCE"]) {
      const title = `Synthetic ${type} ${suffix}`;
      const created = await api(page, "ops/tasks", "POST", { title, type });
      assert.equal(created.status, 201);
      tasks[suffix][type] = { title, id: created.data.id };
    }
    await context.close();
  }

  for (const [suffix, foreign, username, type, role] of [
    ["A", "B", "maid", "HOUSEKEEPING", "MAID"],
    ["A", "B", "technician", "MAINTENANCE", "TECHNICIAN"],
    ["B", "A", "maid", "HOUSEKEEPING", "MAID"],
    ["B", "A", "technician", "MAINTENANCE", "TECHNICIAN"],
  ]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(staff);
    await page.getByLabel("Код организации").fill("tenant_" + suffix.toLowerCase());
    await page.getByLabel("Код отеля").fill("HOTEL_" + suffix);
    await page.getByLabel("Логин").fill(username);
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();
    await page.getByRole("button", { name: "Выйти" }).waitFor();
    const me = await api(page, "auth/me");
    assert.equal(me.data.role, role);
    assert.equal(me.data.property_code, "HOTEL_" + suffix);

    await page.getByRole("button", { name: /можно взять/i }).click();
    const own = tasks[suffix][type];
    const other = tasks[foreign][type];
    const card = page.getByRole("article").filter({ hasText: own.title });
    await card.waitFor();
    assert.equal(await page.getByText(other.title, { exact: true }).count(), 0);
    assert.equal((await api(page, "ops/tasks/" + other.id + "/claim", "POST")).status, 404);
    await card.getByRole("button", { name: "Взять в работу" }).click();
    await card.getByText("В работе", { exact: true }).waitFor();

    // Submit the report through the real Staff form, not a direct API shortcut.
    await card.getByRole("button", { name: type === "HOUSEKEEPING" ? "Сдать уборку" : "Сдать ремонт" }).click();
    const report = page.locator(".shift-modal");
    const submitLabel = type === "HOUSEKEEPING" ? "Отправить на проверку" : "Завершить ремонт";
    await report.getByRole("textbox", { name: "Что сделано" }).fill("Synthetic browser verified work report");
    const checklist = [
      { code: "BED_LINEN", label: "Кровать и бельё", done: true },
      { code: "BATHROOM", label: "Санузел", done: true },
      { code: "SURFACES", label: "Пол и поверхности", done: true },
      { code: "AMENITIES", label: "Комплектация номера", done: true },
      { code: "FINAL_CHECK", label: "Финальная проверка", done: true },
    ];
    if (type === "HOUSEKEEPING") {
      // Incomplete housekeeping must be refused by Core, not auto-approved.
      await report.getByRole("button", { name: submitLabel }).click();
      await page.getByText("Отметьте все пункты чек-листа перед сдачей номера.").waitFor();
      const boxes = report.locator('input[type="checkbox"]');
      assert.equal(await boxes.count(), 5);
      for (let i = 0; i < 5; i += 1) await boxes.nth(i).check();
    } else {
      assert.equal(await report.locator('input[type="checkbox"]').count(), 0);
    }
    await report.getByRole("button", { name: submitLabel }).click();
    await report.waitFor({ state: "hidden" });
    const expectedStatus = type === "HOUSEKEEPING" ? "IN_INSPECTION" : "DONE";
    const taskList = await api(page, "ops/tasks?limit=250&type=" + type);
    assert.equal(taskList.status, 200);
    assert.equal(taskList.data.items.find((task) => task.id === own.id)?.status, expectedStatus);
    const completion = { summary: "Must not replay completed report", checklist: type === "HOUSEKEEPING" ? checklist : [], evidence_urls: [] };
    assert.equal((await api(page, "ops/tasks/" + own.id + "/complete-report", "POST", completion)).status, 409);
    if (type === "HOUSEKEEPING") {
      // A maid cannot approve an inspection, even for her own assigned task.
      assert.equal((await api(page, "ops/tasks/" + own.id + "/status", "PATCH", { status: "DONE" })).status, 403);
    } else {
      await page.getByRole("button", { name: /завершено/i }).click();
      await page.getByRole("article").filter({ hasText: own.title }).getByText("Готово", { exact: true }).waitFor();
    }

    await page.getByRole("button", { name: "Выйти" }).click();
    await page.getByLabel("Код отеля").waitFor();
    assert.equal((await api(page, "auth/me")).status, 401);

    // Reuse the SAME browser cookie jar for the other hotel. The previous
    // hotel's session and task list must never survive the transition.
    await page.getByLabel("Код организации").fill("tenant_" + foreign.toLowerCase());
    await page.getByLabel("Код отеля").fill("HOTEL_" + foreign);
    await page.getByLabel("Логин").fill(username);
    await page.getByLabel("Пароль").fill(password);
    await page.getByRole("button", { name: "Войти" }).click();
    await page.getByRole("button", { name: "Выйти" }).waitFor();
    const swapped = await api(page, "auth/me");
    assert.equal(swapped.status, 200);
    assert.equal(swapped.data.role, role);
    assert.equal(swapped.data.property_code, "HOTEL_" + foreign);
    assert.notEqual(swapped.data.property_id, me.data.property_id);
    assert.notEqual(swapped.data.tenant_id, me.data.tenant_id);
    const swappedTasks = await api(page, "ops/tasks?limit=250&type=" + type);
    assert.equal(swappedTasks.status, 200);
    assert(swappedTasks.data.items.some((task) => task.id === other.id), "Switched hotel task missing");
    assert(!swappedTasks.data.items.some((task) => task.id === own.id), "Stale task leaked after hotel switch");
    assert.equal((await api(page, "ops/tasks/" + own.id + "/claim", "POST")).status, 404);
    const foreignReport = { summary: "Cross-tenant report must fail", checklist: type === "HOUSEKEEPING" ? [
      { code: "BED_LINEN", label: "Кровать и бельё", done: true },
      { code: "BATHROOM", label: "Санузел", done: true },
      { code: "SURFACES", label: "Пол и поверхности", done: true },
      { code: "AMENITIES", label: "Комплектация номера", done: true },
      { code: "FINAL_CHECK", label: "Финальная проверка", done: true },
    ] : [], evidence_urls: [] };
    assert.equal((await api(page, "ops/tasks/" + own.id + "/complete-report", "POST", foreignReport)).status, 404);
    await page.getByRole("button", { name: "Выйти" }).click();
    await page.getByLabel("Код отеля").waitFor();
    assert.equal((await api(page, "auth/me")).status, 401);
    await context.close();
  }
  // Only management may accept an inspected housekeeping task.
  for (const suffix of ["A", "B"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(admin + "/shared-auth-preview");
    await page.getByLabel("Код отеля").waitFor();
    const login = await api(page, "auth/login", "POST", {
      username: "owner", password, tenant_code: "tenant_" + suffix.toLowerCase(), property_code: "HOTEL_" + suffix,
    });
    assert.equal(login.status, 200);
    const taskId = tasks[suffix].HOUSEKEEPING.id;
    const approved = await api(page, "ops/tasks/" + taskId + "/status", "PATCH", { status: "DONE" });
    assert.equal(approved.status, 200);
    assert.equal(approved.data.status, "DONE");
    await context.close();
  }
  console.log("PASS: Staff HTTPS four-role/property report lifecycles, inspection RBAC, replay denials, foreign 404 and hotel switch");
} finally {
  await browser.close();
}
