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
    // Shared-mode server password policy is eight characters minimum.
    const passwordInput = page.getByLabel("Пароль");
    assert.equal(await passwordInput.getAttribute("minlength"), "8");
    await passwordInput.fill("1234567");
    assert.equal(await passwordInput.evaluate(input => input.checkValidity()), false);
    await passwordInput.fill(password);
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
  // Accepted P0 shared dining: REAL COOK/WAITER browsers, canonical API,
  // synthetic PostgreSQL, two independent hotels, and cross-property denials.
  const diningOrderIds = {
    A: "11111111-2222-4333-8444-5555555555a1",
    B: "11111111-2222-4333-8444-5555555555b2",
  };
  for (const suffix of ["A", "B"]) {
    const other = suffix === "A" ? "B" : "A";
    for (const [username, role, heading] of [
      ["cook", "COOK", "Кухня · заказы"],
      ["waiter", "WAITER", "Официант · зал"],
    ]) {
      const context = await browser.newContext();
      const page = await context.newPage();
      await page.goto(staff);
      await page.getByLabel("Код организации").fill("tenant_" + suffix.toLowerCase());
      await page.getByLabel("Код отеля").fill("HOTEL_" + suffix);
      await page.getByLabel("Логин").fill(username);
      await page.getByLabel("Пароль").fill(password);
      await page.getByRole("button", { name: "Войти" }).click();
      await page.getByRole("heading", { name: heading }).waitFor();
      const me = await api(page, "auth/me");
      assert.equal(me.status, 200);
      assert.equal(me.data.role, role);
      assert.equal(me.data.property_code, "HOTEL_" + suffix);
      assert(me.data.module_permissions.includes("DINING"));

      const own = diningOrderIds[suffix];
      const foreign = diningOrderIds[other];
      const listPath = role === "COOK" ? "kitchen/orders?status=ACTIVE" : "dining/floor";
      const list = await api(page, listPath);
      assert.equal(list.status, 200);
      const orders = role === "COOK" ? list.data.items : list.data.orders;
      assert.deepEqual(orders.map(row => row.id), [own], "Shared dining data crossed hotel");
      if (role === "WAITER") assert.equal(list.data.current_user_id, me.data.id);
      const ownCard = page.getByRole("article").filter({ hasText: "CI-DINING-" + suffix });
      await ownCard.waitFor();
      assert.equal(await page.getByText("CI-DINING-" + other, { exact: true }).count(), 0);
      if (role === "COOK") {
        assert.equal((await api(page, "dining/floor")).status, 403,
          "Cook must not gain waiter floor");
        assert.equal((await api(page, "kitchen/orders/" + foreign + "/status",
          "PATCH", { status: "ACCEPTED" })).status, 404,
          "Cook may not patch foreign hotel order");
        await ownCard.getByRole("button", { name: "Принять в работу" }).click();
        await ownCard.getByText("ACCEPTED", { exact: false }).waitFor();
        const accepted = await api(page, "kitchen/orders?status=ACTIVE");
        assert.equal(accepted.data.items.find(item => item.id === own)?.status, "ACCEPTED");
        await ownCard.getByRole("button", { name: "Начать приготовление" }).click();
        await ownCard.getByText("COOKING", { exact: false }).waitFor();
        const cooking = await api(page, "kitchen/orders?status=ACTIVE");
        assert.equal(cooking.data.items.find(item => item.id === own)?.status, "COOKING");
        await ownCard.getByRole("button", { name: "Заказ готов" }).click();
        await ownCard.getByText("READY", { exact: false }).waitFor();
        const ready = await api(page, "kitchen/orders?status=ACTIVE");
        assert.equal(ready.data.items.find(item => item.id === own)?.status, "READY");
        assert.equal((await api(page, "kitchen/orders/" + own + "/status",
          "PATCH", { status: "READY" })).status, 409,
          "READY cannot be replayed");
      } else {
        assert.equal((await api(page, "kitchen/orders")).status, 403,
          "Waiter must not access kitchen queue");
        assert.equal((await api(page, "kitchen/orders/" + own + "/status",
          "PATCH", { status: "COOKING" })).status, 403,
          "Waiter cannot cook or change any other status");
        assert.equal((await api(page, "kitchen/orders/" + own + "/status",
          "PATCH", { status: "SERVED" })).status, 403,
          "Unassigned waiter may not serve even a READY order");
        assert.equal((await api(page, "kitchen/orders/" + foreign + "/status",
          "PATCH", { status: "SERVED" })).status, 404,
          "Foreign hotel order must be 404 for waiter");
        assert.equal((await api(page, "dining/orders/" + foreign + "/waiter",
          "PATCH", { waiter_id: me.data.id })).status, 404,
          "Waiter may not assign foreign order");
        assert.equal((await api(page, "dining/orders/" + own + "/waiter",
          "PATCH", { waiter_id: foreign })).status, 403,
          "Waiter may assign only self");
        await ownCard.getByRole("button", { name: "Назначить заказ себе" }).click();
        await page.getByText("Операция по заказу CI-DINING-" + suffix +
          " подтверждена.", { exact: true }).waitFor();
        const assigned = await api(page, "dining/floor");
        assert.equal(assigned.data.orders.find(item => item.id === own)?.waiter_id, me.data.id);
        assert.equal(assigned.data.orders.find(item => item.id === own)?.status, "READY");
        await ownCard.getByRole("button", { name: "Выдать гостю" }).click();
        await page.getByText("Заказ CI-DINING-" + suffix + " выдан гостю.", { exact: true }).waitFor();
        const servedFloor = await api(page, "dining/floor");
        assert.equal(servedFloor.status, 200);
        assert(!servedFloor.data.orders.some(item => item.id === own),
          "SERVED order must leave ACTIVE dining floor");
        assert.equal((await api(page, "kitchen/orders/" + own + "/status",
          "PATCH", { status: "SERVED" })).status, 409,
          "Serving the same order twice must be 409");
      }
      await page.getByRole("button", { name: "Выйти" }).click();
      await page.getByLabel("Код организации").waitFor();
      assert.equal((await api(page, "auth/me")).status, 401);
      await context.close();
    }
  }
  // Confirm real database-backed SERVED status via the canonical management read.
  for (const suffix of ["A", "B"]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(admin + "/shared-auth-preview");
    await page.getByLabel("Код отеля").waitFor();
    const signed = await api(page, "auth/login", "POST", {
      username: "owner", password, tenant_code: "tenant_" + suffix.toLowerCase(),
      property_code: "HOTEL_" + suffix,
    });
    assert.equal(signed.status, 200);
    const all = await api(page, "kitchen/orders?status=ALL");
    assert.equal(all.status, 200);
    assert.deepEqual(all.data.items.map(item => item.id), [diningOrderIds[suffix]]);
    assert.equal(all.data.items[0].status, "SERVED");
    assert.equal(all.data.items[0].financial_posting, "NONE_AUTOMATIC");
    await context.close();
  }
  console.log("PASS: two-hotel COOK accepted/cooking/ready -> assigned WAITER served; status transitions, no auto payment, 401/403/404/409");
  console.log("PASS: two-hotel COOK/WAITER HTTPS sessions, scoped orders, status/assignment and 403/404 denials");
  console.log("PASS: Staff HTTPS four-role/property report lifecycles, inspection RBAC, replay denials, foreign 404 and hotel switch");
} finally {
  await browser.close();
}
