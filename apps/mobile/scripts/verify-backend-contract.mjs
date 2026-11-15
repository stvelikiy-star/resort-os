import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { resolve } from 'node:path';

/**
 * Static source contract — fails closed on changed/missing pinned server code,
 * proves ROUTE EXISTENCE only. DTO and runtime auth require dedicated E2E.
 * Reference snapshot: MARINA integration release 8217602953ba637114e1b403dfc8d2fe7b02ddd2.
 * Staff/store and kitchen/recipe additions reviewed against Core #428.
 * Cook draft authoring reviewed with test_kitchen_draft_authoring.py and kitchen-author-menu.test.ts.
 * Recipe extension is pinned separately and covered by recipe DTO and API tests.
 * Dining manager-only menu writes (#477) and assigned WAITER READY->SERVED (#483)
 * verified by PostgreSQL Kitchen Operations E2E on the stacked integration tree.
 */
const src = resolve(process.cwd(), '../../services/api/app');
const pinned = {
  'auth.py': '59bed47d5f1de5ec98457e6849ea541356cc1929',
  'operations.py': '888be1aad873765a49eb0c902c99dfbb38e3d8e2',
  'operations_assignment.py': '6571408a94257d803ddc75b4a66c1b55d792a3fe',
  'staff_task_reports.py': 'd63e9096abcd64115145d99de8f66b8c6bb775ef',
  'staff_control.py': '5f090f4a318458e3a67f2ee59dd302cbc31b43bc',
  'main.py': '2a01b9898fc3e6e4d2a680f31691ba7e00a768ed',
  'manager_dashboard.py': '135c6ec05c8cb16060936f57c218e213a1fa2eb2',
  'reception_reservations.py': 'a86688a3dc69cf639cb79bea8d7e243569f57e41',
  'pms_reservation_create.py': 'c5d7fb9fd6b5a36e6c7c9c0b46d8d83155fe306b',
  'inbox.py': 'e860f157adfb7ec9e846a79f9fc8a6e64b1e6e7f',
  'owner_cash_reconciliation.py': 'f8600874c4dbbc5f95d6a7affe139bdd4dfbe23c',
  'owner_expenses.py': 'aa05bd01d52ca93701768e07894ead88d48a037b',
  'owner_kitchen_management.py': 'ebe1f276ea64f19ad696f6643afa3ead4fb30571',
  'kitchen_procurement.py': '35024849f3697e6b1da928e4428f8e8f54c89453',
  'kitchen_stock.py': 'ea6f5e8013a967fc9a98c46b992e2d7cd3c0834d',
  'kitchen_menu_management.py': '3d8f8947e3a26cd40f77f718887c5f674fb4038c',
  'kitchen_recipes.py': 'd6a920886721a3a9bf8fc6d5c681f42b7f22eca5',
  'kitchen.py': '22c2faa257e4119d3d716acbfa8d499cb1b71bb5',
  'dining_production_snapshots.py': '717f2070a0924ab73456e364a5d4a8cf03c0c47e',
  'dining_control.py': '196e847403dc9b45fd4fa8ac94c28556320478db',
  'dining_stays.py': '6978f0f430e82616d05ebbab08a135119304d828',
  'dining_seating.py': '1dd098289a5ba5d45fa14512547f7ea1f1681122',
  'dining_folio.py': '1ee6b2c2893473bab2af7ce434045dd54bf0366e',
  'staff_guest_requests.py': 'a7497404b57972fda32e64f83aa4e3662cfc1d2e',
  'guest_services.py': '463f57606140afda07b5cd98014e3e229fa53d25',
  'marina_assistant.py': '7b4e50bd9bd853cfeed438ac8fccb5e310a0f773',
  'stays.py': '7412700ee2801199ed518976039abe23c351c150',
};
const contracts = [
  ['auth.py','router','/api/v1/auth',['post /login','post /logout','get /me']],
  ['operations.py','router','/api/v1/ops',['get /tasks','post /tasks','post /tasks/{task_id}/claim','patch /tasks/{task_id}/status','patch /rooms/{room_id}/state']],
  ['operations_assignment.py','router','/api/v1/ops',['patch /tasks/{task_id}/assignee']],
  ['staff_task_reports.py','router','/api/v1/ops',['post /tasks/{task_id}/complete-report']],
  ['staff_control.py','router','/api/v1/admin/staff',['get /overview']],
  ['manager_dashboard.py','router','/api/v1/admin/dashboard',['get ']],
  ['reception_reservations.py','router','/api/v1/admin/reception',['get /reservations','get /reservations/{reservation_id}']],
  ['main.py','app','',['get /api/v1/pms/grid']],
  ['pms_reservation_create.py','router','/api/v1/admin/pms/reservations',['post /new/preview','post /new/commit']],
  ['inbox.py','router','/api/v1/admin/inbox',['get /conversations','get /conversations/{conversation_id}','post /conversations/{conversation_id}/claim','patch /conversations/{conversation_id}/status','post /conversations/{conversation_id}/notes']],
  ['owner_cash_reconciliation.py','router','/api/v1/admin/finance/owner',['get /recorded-cash-movements']],
  ['owner_expenses.py','router','/api/v1/admin/finance/owner/expenses',
    ['get ', 'post ', 'post /{expense_id}/settlements', 'post /{expense_id}/void']],
  ['owner_kitchen_management.py','router','/api/v1/admin/finance/owner',['get /kitchen-operations']],
  ['kitchen_procurement.py','router','/api/v1/kitchen/procurement',
    ['get /needs','get /requests','post /requests','post /requests/{request_id}/approve','post /requests/{request_id}/receive']],
  ['kitchen_stock.py','router','/api/v1/kitchen/stock',['get ','get /losses','post /losses']],
  ['kitchen_menu_management.py','router','/api/v1/kitchen',['get /menu/availability','put /menu/{item_id}/availability','post /menu','patch /menu/{item_id}','get /production-menu','get /production-targets','put /production-targets','get /menu/{item_id}/recipe','put /menu/{item_id}/recipe']],
  ['kitchen.py','admin_router','/api/v1/kitchen',['get /menu','post /tables','get /orders','post /orders','patch /orders/{order_id}/status']],
  ['dining_production_snapshots.py','router','/api/v1/dining',['get /production-snapshots','post /production-snapshots']],
  ['dining_control.py','router','/api/v1/dining',['get /floor','patch /orders/{order_id}/waiter']],
  ['dining_stays.py','router','/api/v1/dining',['get /stays']],
  ['dining_seating.py','router','/api/v1/dining',['get /sessions','post /sessions','patch /sessions/{session_id}/status','post /sessions/{session_id}/move']],
  ['dining_folio.py','router','/api/v1/dining',['get /folio-orders','post /orders/{order_id}/folio']],
  ['staff_guest_requests.py','router','/api/v1/ops/guest-requests',['get ','post /{task_id}/claim','post /{task_id}/complete']],
  ['guest_services.py','router','/api/v1/admin/guest-services',['post ']],
  ['marina_assistant.py','router','/api/v1/assistant',['get /capabilities','post /chat']],
  ['stays.py','router','/api/v1/admin/stays',['post /reservations/{reservation_id}/check-in','post /reservations/{reservation_id}/check-out']],
];
function fileSha(buffer) {
  return createHash('sha1').update(Buffer.from('blob ' + buffer.byteLength + '\0')).update(buffer).digest('hex');
}
let routeCount = 0;
for (const [filename, sha] of Object.entries(pinned)) {
  const path = resolve(src, filename);
  if (!existsSync(path)) throw new Error('Pinned backend module missing: ' + filename);
  const bytes = readFileSync(path);
  if (fileSha(bytes) !== sha) throw new Error('BACKEND DRIFT: ' + filename + ' changed; review/update pinned snapshot and response schema before release');
}
for (const [filename, router, prefix, endpoints] of contracts) {
  const code = readFileSync(resolve(src, filename), 'utf8');
  // Python uses both quotation styles. Keep exact route/method assertions.
  const doublePrefix = router + ' = APIRouter(prefix="' + prefix + '"';
  const singlePrefix = router + " = APIRouter(prefix='" + prefix + "'";
  if (prefix && !code.includes(doublePrefix) && !code.includes(singlePrefix))
    throw new Error('API prefix mismatch: ' + filename);
  for (const entry of endpoints) {
    const [method, ...rest] = entry.split(' ');
    const path = rest.join(' ');
    // Decorators may include status_code, response_model, etc. after the path.
    const doubleRoute = '@' + router + '.' + method + '("' + path + '"';
    const singleRoute = '@' + router + '.' + method + "('" + path + "'";
    if (!code.includes(doubleRoute) && !code.includes(singleRoute))
      throw new Error('Missing ' + method.toUpperCase() + ' ' + prefix + path + ' in ' + filename);
    routeCount++;
  }
}
// HOLD routes are present in unified Core #428. Verify route decorators too,
// rather than inferring capability merely from a filename.
const holdsFile = resolve(src,'pms_holds.py');
if (!existsSync(holdsFile)) throw new Error('Mobile release blocked: PMS HOLD router missing');
const holdsCode = readFileSync(holdsFile,'utf8');
const holdsPrefix = '/api/v1/admin/pms/holds';
if (!holdsCode.includes('router = APIRouter(prefix="' + holdsPrefix + '"')) {
  throw new Error('Mobile release blocked: PMS HOLD prefix drift');
}
for (const [method, path] of [['get',''],['post',''],['delete','/{hold_id}']]) {
  if (!holdsCode.includes('@router.' + method + '("' + path + '"')) {
    throw new Error('Mobile release blocked: missing HOLD ' + method + ' ' + holdsPrefix + path);
  }
  routeCount++;
}
process.stdout.write('MARINA MOBILE PINNED_BACKEND_ROUTES: ' + routeCount + '/' + routeCount + ' VERIFIED\n');
process.stdout.write('MARINA MOBILE PINNED_CORE_BASE_SHA: 8217602953ba637114e1b403dfc8d2fe7b02ddd2\n');
