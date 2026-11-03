import { chromium } from "playwright";

// The browser uses synthetic mocked API replies to verify frontend navigation/role UI.
// Canonical PostgreSQL + server-side tenant isolation are independently covered by
// verify_marina_shared_auth_postgres.py. Never mistake this UI test for provider/host E2E.
const BASE = process.env.MARINA_ADMIN_BROWSER_URL || "http://127.0.0.1:13001";
if (!["localhost", "127.0.0.1"].includes(new URL(BASE).hostname)) {
  throw new Error("Shared preview browser checks must target disposable localhost only");
}
const profiles = {
  HOTEL_A: { tenant: "tenant_a", user: "owner", role: "OWNER", name: "Owner A", rooms: ["A101"], sections: ["DASHBOARD","PMS","RESERVATIONS","STAFF"] },
  HOTEL_B: { tenant: "tenant_b", user: "owner", role: "OWNER", name: "Owner B", rooms: ["B202"], sections: ["DASHBOARD","PMS","RESERVATIONS","STAFF"] },
  HOTEL_R: { tenant: "tenant_r", user: "reception", role: "RECEPTION", name: "Reception R", rooms: ["R303"], sections: ["PMS","RESERVATIONS"] },
};
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
const errors = [];
page.on("pageerror", error => errors.push(error.message));
page.on("dialog", dialog => dialog.accept());
let active = null;
const staffByHotel = {};
const bookingIds = {
  HOTEL_A:"00000000-0000-4000-8000-000000000101",
  HOTEL_B:"00000000-0000-4000-8000-000000000202",
  HOTEL_R:"00000000-0000-4000-8000-000000000303",
};
const bookingStatus = Object.fromEntries(Object.keys(bookingIds).map(code => [code,"GUARANTEED"]));
function scopedBooking() {
  return {id:bookingIds[active.code],bookingNumber:active.code+"-BOOK",status:bookingStatus[active.code],
    checkIn:"2026-11-03",checkOut:"2026-11-05",room_code:active.rooms[0],
    room_state:"CLEAN",firstName:"Synthetic "+active.code,phone:null,
    totalKgs:9000,paidKgs:0,remainingKgs:9000};
}
const respond = (route, code, body) => route.fulfill({
  status: code, contentType: "application/json", body: JSON.stringify(body),
  headers: { "Cache-Control": "no-store" },
});
await page.route("**/core/api/v1/**", async route => {
  const request = route.request();
  const url = new URL(request.url());
  const path = url.pathname.replace(/^\/core/, "");
  const method = request.method();
  if (path === "/api/v1/auth/mode") return respond(route, 200, { mode:"shared_auth_preview", workspaces_available:false });
  if (path === "/api/v1/auth/login" && method === "POST") {
    const data = request.postDataJSON();
    const match = profiles[data.property_code];
    if (!match || match.tenant !== data.tenant_code || match.user !== data.username || data.password !== "synthetic-password-only") {
      return respond(route, 401, { detail:"Invalid username or password" });
    }
    active = { ...match, code:data.property_code };
    return respond(route, 200, { id:"browser-user", role:active.role, property_code:active.code });
  }
  if (path === "/api/v1/auth/me") {
    if (!active) return respond(route, 401, { detail:"Authentication required" });
    return respond(route, 200, {
      id:"browser-user", username:active.user, display_name:active.name, role:active.role,
      property_code:active.code, property_id:"synthetic-property-id",
      tenant_id:"synthetic-tenant-id", module_permissions:active.sections,
    });
  }
  if (path === "/api/v1/auth/logout" && method === "POST") {
    active = null;
    return respond(route, 204, {});
  }
  if (!active) return respond(route, 401, {detail:"Authentication required"});
  if (path === "/api/v1/admin/dashboard" && method === "GET") {
    if (!active.sections.includes("DASHBOARD")) return respond(route, 403, { detail:"Forbidden" });
    return respond(route, 200, {
      property:{ code:active.code, name:active.code },
      rooms:{ total:active.rooms.length, clean:1, dirty:0 },
      stays:{ in_house:0, arrivals_today:0, departures_today:0 },
      communications:{ needs_reply:0 },
    });
  }
  if (path === "/api/v1/pms/grid" && method === "GET") {
    if (!active.sections.includes("PMS")) return respond(route, 403, {detail:"Forbidden"});
    return respond(route, 200, {
      property:active.code,
      rooms:active.rooms.map(code=>({id:code,code,name:"Synthetic",operational_state:"CLEAN",blocks:[]})),
    });
  }
  if (path === "/api/v1/admin/reception/reservations" && method === "GET") {
    if (!active.sections.includes("RESERVATIONS")) return respond(route, 403, { detail:"Forbidden" });
    return respond(route, 200, { local_date:"2026-11-03", items:[scopedBooking()] });
  }
  if (path === "/api/v1/admin/staff/overview" && method === "GET") {
    if (!active.sections.includes("STAFF")) return respond(route, 403, {detail:"Forbidden"});
    return respond(route, 200, {
      staff:staffByHotel[active.code]||[], can_manage_access:active.role==="OWNER",
      managed_roles:["MANAGER","RECEPTION","MAID","TECHNICIAN","COOK","WAITER"],
    });
  }
  if (path === "/api/v1/admin/staff" && method === "POST") {
    if (active.role !== "OWNER") return respond(route, 403, {detail:"Forbidden"});
    const data=request.postDataJSON();
    const item={id:"synthetic-"+active.code+"-"+data.username,username:data.username,
      display_name:data.display_name,role:data.role,active:true,module_permissions:[]};
    staffByHotel[active.code]=[...(staffByHotel[active.code]||[]),item];
    return respond(route,201,item);
  }
  if (path.startsWith("/api/v1/admin/staff/") && method === "PATCH") {
    if (active.role !== "OWNER") return respond(route,403,{detail:"Forbidden"});
    const staff=staffByHotel[active.code]||[];
    const item=staff.find(r=>path.endsWith("/"+r.id));
    if (!item) return respond(route,404,{detail:"Not found"});
    item.active=request.postDataJSON().active;
    return respond(route,200,item);
  }
  return respond(route,503,{detail:"Blocked in shared preview"});
});
async function login(code, user="owner") {
  await page.getByLabel("Код организации").fill(profiles[code].tenant);
  await page.getByLabel("Код отеля").fill(code);
  await page.getByLabel("Логин").fill(user);
  await page.getByLabel("Пароль").fill("synthetic-password-only");
  await page.getByRole("button",{name:"Войти"}).click();
  await page.getByText("Подтверждённый вход:").waitFor();
}
try {
  // In shared mode, the usual Admin entry must not display a username-only login.
  await page.goto(BASE, {waitUntil:"domcontentloaded"});
  await page.waitForURL("**/shared-auth-preview", {timeout:20000});
  await page.getByLabel("Код организации").waitFor();
  await login("HOTEL_A");
  await page.getByRole("heading",{name:"HOTEL_A"}).waitFor();
  await page.getByRole("button",{name:"Шахматка"}).click();
  await page.getByText("A101").waitFor();
  if (await page.getByText("B202").count()) throw new Error("Foreign room visible in hotel A");
  await page.getByRole("button",{name:"Бронирования"}).click();
  await page.getByText("HOTEL_A-BOOK").waitFor();
  if (await page.getByText("HOTEL_B-BOOK").count()) throw new Error("Foreign reservation visible in hotel A");
  await page.getByRole("button",{name:"Заселить"}).waitFor();
  await page.getByRole("button",{name:"Персонал"}).click();
  await page.getByRole("heading",{name:"Сотрудники (0)"}).waitFor();
  await page.getByLabel("Создание сотрудника").getByLabel("Логин").fill("employee-a");
  await page.getByLabel("Создание сотрудника").getByLabel("Имя").fill("Synthetic Employee A");
  await page.getByLabel("Создание сотрудника").getByLabel("Пароль").fill("synthetic-long-staff-pass");
  await page.getByRole("button",{name:"Создать сотрудника"}).click();
  await page.getByText("Synthetic Employee A").waitFor();
  await page.getByRole("button",{name:"Отключить"}).click();
  await page.getByText("Отключён").waitFor();
  await page.getByRole("button",{name:"Выйти"}).click();
  await page.getByLabel("Код организации").waitFor();

  await login("HOTEL_B");
  await page.getByRole("heading",{name:"HOTEL_B"}).waitFor();
  await page.getByRole("button",{name:"Шахматка"}).click();
  await page.getByText("B202").waitFor();
  if (await page.getByText("A101").count()) throw new Error("Foreign room visible in hotel B");
  await page.getByRole("button",{name:"Бронирования"}).click();
  await page.getByText("HOTEL_B-BOOK").waitFor();
  await page.getByRole("button",{name:"Персонал"}).click();
  await page.getByRole("heading",{name:"Сотрудники (0)"}).waitFor();
  if (await page.getByText("Synthetic Employee A").count()) throw new Error("Foreign employee visible in hotel B");
  await page.getByRole("button",{name:"Выйти"}).click();
  await page.getByLabel("Код организации").waitFor();

  await login("HOTEL_R","reception");
  await page.getByRole("button",{name:"Шахматка"}).waitFor();
  if (await page.getByRole("button",{name:"Персонал"}).count()) throw new Error("Reception shown staff admin");
  if (await page.getByRole("button",{name:"Дашборд"}).count()) throw new Error("Reception shown owner dashboard");
  await page.getByText("R303").waitFor();
  if (errors.length) throw new Error(JSON.stringify(errors));
  console.log("MARINA_SHARED_ADMIN_BROWSER_PASS: main entry redirect, two hotel UI isolation, owner staff creation and revocation, reception restricted, 390px viewport");
} finally {
  await browser.close();
}
