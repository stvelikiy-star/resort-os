import { chromium } from "/work/playwright/node_modules/playwright/index.mjs";

const base = "http://127.0.0.1:15661/qa-guest-handoff";
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const errors = [];
ctx.on("page", (page) => page.on("pageerror", (error) => errors.push(error.message)));
const aiResult = {
  answer: "The hotel receptionist can help with your question.",
  read_only: true,
  can_mutate: false,
  human_handoff: {
    available: true,
    status: "NOT_REQUESTED",
    request_code: "ADMIN",
    requires_explicit_guest_action: true,
    action: "CREATE_GUEST_REQUEST",
    endpoint_suffix: "/requests",
    http_method: "POST",
    body: { request_code: "ADMIN" },
    task_created: false,
  },
};

async function readyPage(requestBehavior = "success", result = aiResult) {
  let posts = 0;
  const page = await ctx.newPage();
  await page.route("**/core/api/v1/guest-os/rooms/synthetic-guest-token/assistant/chat", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(result) });
  });
  await page.route("**/core/api/v1/guest-os/rooms/synthetic-guest-token/requests", async (route) => {
    posts += 1;
    const input = route.request().postDataJSON();
    if (input.request_code !== "ADMIN" || input.description !== "Прошу помочь с заселением") {
      throw new Error("Wrong handoff request payload: " + JSON.stringify(input));
    }
    if (requestBehavior === "fail") {
      await route.abort("failed");
      return;
    }
    if (requestBehavior === "duplicate") {
      await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({detail:{code:"GUEST_REQUEST_DUPLICATE_ACTIVE",task_id:"synthetic-task"}}) });
      return;
    }
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({id:"synthetic-task",request_code:"ADMIN",status:"OPEN"}) });
  });
  const response = await page.goto(base, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (response.status() !== 200) throw new Error("QA fixture not served");
  await page.locator("summary").click();
  await page.getByRole("textbox", { name: "Ваш вопрос" }).fill("Прошу помочь с заселением");
  await page.getByRole("button", { name: "Спросить" }).click();
  await page.getByText(aiResult.answer).waitFor();
  return { page, getPosts: () => posts };
}

try {
  const ok = await readyPage();
  if (ok.getPosts() !== 0) throw new Error("Request created without explicit guest action");
  await ok.page.getByRole("button", { name: "Позвать администратора" }).click();
  if (ok.getPosts() !== 0) throw new Error("Request created after only first click");
  await ok.page.getByRole("button", { name: "Отмена" }).click();
  if (ok.getPosts() !== 0) throw new Error("Request created despite cancel");
  await ok.page.getByRole("button", { name: "Позвать администратора" }).click();
  await ok.page.getByRole("button", { name: "Подтвердить заявку" }).click();
  await ok.page.getByText("Заявка администратору создана. Статус появится в ваших заявках.").waitFor();
  if (ok.getPosts() !== 1) throw new Error("Expected exactly one guest request, got " + ok.getPosts());
  if (await ok.page.locator("body").getAttribute("data-reloaded") !== "true") throw new Error("Parent request list not refreshed");
  console.log("PASS_MOBILE_EXPLICIT_CONFIRMATION_ONLY_ONE_TASK_POST");
  await ok.page.close();

  const duplicate = await readyPage("duplicate");
  await duplicate.page.getByRole("button", { name: "Позвать администратора" }).click();
  await duplicate.page.getByRole("button", { name: "Подтвердить заявку" }).click();
  await duplicate.page.getByText("У вас уже есть активная заявка администратору. Проверьте её статус.").waitFor();
  if (duplicate.getPosts() !== 1) throw new Error("Duplicate was retried");
  console.log("PASS_DUPLICATE_409_NO_RETRY");
  await duplicate.page.close();

  const failure = await readyPage("fail");
  await failure.page.getByRole("button", { name: "Позвать администратора" }).click();
  await failure.page.getByRole("button", { name: "Подтвердить заявку" }).click();
  await failure.page.getByText("Не удалось подтвердить создание заявки. Проверьте список заявок, прежде чем повторять.").waitFor();
  if (failure.getPosts() !== 1) throw new Error("Ambiguous network failure was retried");
  console.log("PASS_NETWORK_UNKNOWN_OUTCOME_NO_RETRY");
  await failure.page.close();

  const rejected = await readyPage("success", { ...aiResult, human_handoff: { ...aiResult.human_handoff, task_created: true } });
  if (await rejected.page.getByRole("button", { name: "Позвать администратора" }).count()) throw new Error("Untrusted handoff metadata was accepted");
  console.log("PASS_UNREVIEWED_HANDOFF_METADATA_REJECTED");
  await rejected.page.close();

  if (errors.length) throw new Error("React browser exceptions: " + errors.join("; "));
  console.log("GUEST_EXPLICIT_HANDOFF_PLAYWRIGHT_PASS");
} finally {
  await ctx.close();
  await browser.close();
}
