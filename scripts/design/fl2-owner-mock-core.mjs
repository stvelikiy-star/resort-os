// QA-ONLY synthetic Core API for visual capture of the Admin OWNER dashboard.
// Never import from product code. All names/numbers below are placeholders so layouts can be
// photographed; they are NOT hotel facts and must never be used in screenshots presented as live data.
import http from "node:http";

const today = "2026-11-14";
const addDays = (n) => { const d = new Date(2026, 10, 14 + n); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const stay = (i, room, name) => ({ id: `s${i}`, booking_number: `QA-${1000 + i}`, guest_name: name, phone: null, room_code: room, check_in: today, check_out: addDays(3) });
const daily = Array.from({ length: 30 }, (_, i) => {
  const booked = Math.round(34 + 14 * Math.sin(i / 4) + i * 0.3);
  return { date: addDays(i), available_rooms: 60, booked_rooms: booked, occupancy_on_books_percent: Math.round(booked / 60 * 1000) / 10, allocated_booked_value_kgs: booked * 5200, arrivals: 3 + (i % 5), departures: 2 + (i % 4) };
});
const period = (days, booked) => ({ days, booked_room_nights: booked, available_room_nights: days * 60, occupancy_on_books_percent: Math.round(booked / (days * 60) * 1000) / 10, allocated_booked_value_kgs: booked * 5200, arrivals: days * 4, departures: days * 4 });
const actions = [
  { code: "NOT_READY_ARRIVALS", severity: "CRITICAL", count: 2, label: "Заезды сегодня без статуса «Готов»" },
  { code: "DEBT_ARRIVALS", severity: "HIGH", count: 3, label: "Заезды с остатком к оплате" },
];
const range = (days) => ({ from: today, to: today, days });
const kpi = (k) => ({ occupancy_percent: 71.4 * k, adr_kgs: 5400 * k, revpar_kgs: 3860 * k, allocated_booked_value_kgs: 2100000 * k, received_payments_kgs: 1600000 * k, active_outstanding_kgs: 340000, active_debtor_count: 7 });
const task = (s) => ({ created_in_period: 20, completed_in_period: 16, active_now: 4, urgent_now: 1, avg_completion_minutes: 42, max_completion_minutes: 120, ...s });

const routes = {
  "/api/v1/auth/mode": () => ({ mode: "standard" }),
  "/api/v1/auth/me": () => ({ id: "qa-owner", username: "owner", display_name: "QA Owner", role: "OWNER", property_code: "QA", module_permissions: ["DASHBOARD","PMS","RATES","GROUPS","REQUESTS","AGENTS","RESERVATIONS","SERVICES","DINING","SERVICE_SETTINGS","GUESTS","OFFERS","MARKETING","GROWTH","FINANCE","REPORTS","OPS","STAFF","INBOX","WHATSAPP","CONTENT","ROOM_QR","POINT_QR","HOTEL_RULES","SETTINGS","CHANNELS"], module_permissions_custom: false }),
  "/api/v1/admin/hotel-setup/modules": () => ({ enabled_modules: ["GROUPS","AGENTS","MARKETING","DINING","OFFERS","GROWTH","CONTENT","ROOM_QR","POINT_QR","INBOX"], hotel_name: "QA Resort (synthetic)" }),
  "/api/v1/admin/dashboard": () => ({
    property: { name: "QA Resort (synthetic)", code: "QA", timezone: "Asia/Bishkek", currency: "KGS", local_date: today },
    rooms: { total: 60, clean: 31, dirty: 9, in_inspection: 4, tech_block: 2, unknown: 14 },
    stays: { arrivals_today: 8, departures_today: 6, in_house: 41, guaranteed: 19, occupied_rooms: 43, occupancy_percent: 72 },
    requests: { new: 5, quoted: 3, awaiting_prepayment: 2, active: 10 },
    tasks: { housekeeping_active: 7, maintenance_active: 3, guest_requests_active: 4, urgent_active: 1 },
    communications: { active: 12, needs_reply: 4, oldest_waiting_seconds: 5400, sla_rule: null },
    finance: { confirmed_payments_today_kgs: 184000, active_reservations_total_kgs: 4120000, active_reservations_paid_kgs: 2760000, active_reservations_remaining_kgs: 1360000, scope_note: "" },
    today: { arrivals: [stay(1, "101", "Гость А (QA)"), stay(2, "204", "Гость Б (QA)"), stay(3, "Вилла 7", "Гость В (QA)")], departures: [stay(4, "305", "Гость Г (QA)"), stay(5, "112", "Гость Д (QA)")] },
    attention_tasks: [
      { id: "t1", type: "MAINTENANCE", status: "NEW", priority: "URGENT", title: "Не работает кондиционер", room_code: "204", assigned_to: null, created_at: today },
      { id: "t2", type: "HOUSEKEEPING", status: "IN_PROGRESS", priority: "HIGH", title: "Уборка перед заездом", room_code: "101", assigned_to: "Сотрудник QA", created_at: today },
    ],
  }),
  "/api/v1/admin/intelligence/owner-brief": () => ({
    property: { name: "QA Resort (synthetic)", local_date: today, timezone: "Asia/Bishkek" },
    forward: { next_7_days: period(7, 300), next_30_days: period(30, 1180), daily },
    actions,
    details: { not_ready_arrivals_today: [], unassigned_arrivals_72h: [], debt_arrivals_72h: [] },
    guest_segments: { repeat_profiles: 14, upcoming_repeat_arrivals_30d: 5, completed_without_future: 40, profiles_without_reservations: 3 },
    pickup_readiness: { prior_snapshot_available: false, latest_prior_snapshot_date: null, status: "INSUFFICIENT_HISTORY" },
    truth: {},
  }),
  "/api/v1/admin/intelligence/pickup": () => ({ status: "INSUFFICIENT_HISTORY", local_date: today, snapshot_count: 0, days: [], truth: "" }),
  "/api/v1/admin/growth/summary": () => ({ queue: { active: 6, overdue: 1, feedback_open: 2, return_open: 3 }, feedback: { scored: 18, average_score: 4.6, promoters: 12, passives: 4, detractors: 2, recovery_open: 1, nps: 55, nps_sample_size: 18 }, candidates: { post_stay_14d: 9, reactivation: 22, reactivation_min_days: 30 } }),
  "/api/v1/admin/reports/overview": (q) => ({ range: range(q.get("from_date") === "2026-11-01" ? 14 : 14), kpi: kpi(q.get("from_date") === "2026-11-01" ? 1 : 0.93), crm: { conversion_percent: 18.5, leads: 54, converted: 10 } }),
  "/api/v1/admin/finance/summary": (q) => ({ period_payments: { received_kgs: q.get("from_date") === "2026-11-01" ? 1600000 : 1450000, received_count: 64 }, receivables_snapshot: { outstanding_kgs: 340000, debtor_count: 7 } }),
  "/api/v1/admin/intelligence/operations-performance": () => ({
    property: { local_date: today, timezone: "Asia/Bishkek" }, range: range(14),
    guest_services: { ...task(), past_due_date_active: 0, by_service: [] },
    guest_service_sla: { status: "NOT_CONFIGURED", configured: false, target_minutes: null, breach_count: null, observed_avg_completion_minutes: null, due_date_overdue_active: 0 },
    housekeeping: task(), maintenance: task(), problem_rooms: [], recurring_faults: [], staff_performance: [],
  }),
};

export function startMockCore(port = 8000) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    const handler = routes[url.pathname];
    res.setHeader("content-type", "application/json");
    if (!handler) { res.statusCode = 404; res.end(JSON.stringify({ detail: "qa-mock: not implemented" })); return; }
    res.end(JSON.stringify(handler(url.searchParams)));
  });
  return new Promise((resolve) => server.listen(port, "127.0.0.1", () => resolve(server)));
}
if (import.meta.url === `file://${process.argv[1]}`) {
  await startMockCore(Number(process.env.PORT || 8000));
  console.log("qa mock core on", process.env.PORT || 8000);
}
