import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { resolve } from 'node:path';

/**
 * Static source contract — fails closed on changed/missing pinned server code,
 * proves ROUTE EXISTENCE only. DTO and runtime auth require dedicated E2E.
 * Reference snapshot: unified Core release candidate #428 at
 * 73725dc2fd11ad45a5d9bc23a2c21dd732bd61d7.
 */
const src = resolve(process.cwd(), '../../services/api/app');
const pinned = {
  'auth.py': '59bed47d5f1de5ec98457e6849ea541356cc1929',
  'operations.py': '888be1aad873765a49eb0c902c99dfbb38e3d8e2',
  'operations_assignment.py': '6571408a94257d803ddc75b4a66c1b55d792a3fe',
  'staff_task_reports.py': 'd63e9096abcd64115145d99de8f66b8c6bb775ef',
  'staff_control.py': '281926a30c97f8037804b468531f0ea527b75fde',
  'main.py': '2a01b9898fc3e6e4d2a680f31691ba7e00a768ed',
  'manager_dashboard.py': '135c6ec05c8cb16060936f57c218e213a1fa2eb2',
  'reception_reservations.py': 'a86688a3dc69cf639cb79bea8d7e243569f57e41',
  'pms_reservation_create.py': 'c5d7fb9fd6b5a36e6c7c9c0b46d8d83155fe306b',
  'inbox.py': 'e860f157adfb7ec9e846a79f9fc8a6e64b1e6e7f',
  'kitchen_menu_management.py': '6247836cc8fa39a8699383e712b42843e987adaf',
  'kitchen.py': 'af86e40323b16226f6f969e209bc03d64a85a285',
  'dining_production_snapshots.py': '717f2070a0924ab73456e364a5d4a8cf03c0c47e',
  'dining_control.py': '80c4defa448f0e82671f743215a307705f5dd002',
  'guest_services.py': 'b9dadd9e7dcaa2ab1958853e77b9699b61207c71',
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
  ['kitchen_menu_management.py','router','/api/v1/kitchen',['post /menu']],
  ['kitchen.py','admin_router','/api/v1/kitchen',['get /menu','post /tables','get /orders','post /orders','patch /orders/{order_id}/status']],
  ['dining_production_snapshots.py','router','/api/v1/dining',['get /production-snapshots','post /production-snapshots']],
  ['dining_control.py','router','/api/v1/dining',['get /floor','patch /orders/{order_id}/waiter']],
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
  if (prefix && !code.includes(router + ' = APIRouter(prefix="' + prefix + '"')) throw new Error('API prefix mismatch: ' + filename);
  for (const entry of endpoints) {
    const [method, ...rest] = entry.split(' ');
    const path = rest.join(' ');
    if (!code.includes('@' + router + '.' + method + '("' + path + '"')) throw new Error('Missing ' + method.toUpperCase() + ' ' + prefix + path + ' in ' + filename);
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
process.stdout.write('MARINA MOBILE PINNED_CORE_SHA: 73725dc2fd11ad45a5d9bc23a2c21dd732bd61d7\n');
