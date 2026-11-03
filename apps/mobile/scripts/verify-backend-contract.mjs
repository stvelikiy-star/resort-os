import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { resolve } from 'node:path';

/**
 * Static source contract — fails closed on changed/missing pinned server code,
 * proves ROUTE EXISTENCE only. DTO and runtime auth require dedicated E2E.
 * Reference snapshot: current mobile-base/backend tree at
 * 8476b0f4d10e6b33fc45b192d2323c9ca595b2e0.
 */
const src = resolve(process.cwd(), '../../services/api/app');
const pinned = {
  'auth.py': '36e78d6924876f25a7a0e44ecdb4a7f9fb77f7d9',
  'operations.py': 'e0559b741ccb1980329f089df080626790ecac8e',
  'operations_assignment.py': '81c563e5d1d357d648de8d7e9f8379d2a6d9d5c2',
  'staff_task_reports.py': '48e33a13fb43512bfd0018ea717fe711ddda42ce',
  'staff_control.py': '9e9f8d0d969254cd7691be79ca3b155530719afd',
  'main.py': '54595a5afee0ccf05157db294ee7f799b1883cb4',
  'manager_dashboard.py': '135c6ec05c8cb16060936f57c218e213a1fa2eb2',
  'reception_reservations.py': '3942d865cad4ae5905c3031468d65bff25a85d98',
  'pms_reservation_create.py': 'bc18267d90d4e0e60a97464d29a53bd01c81c1b8',
  'inbox.py': 'e860f157adfb7ec9e846a79f9fc8a6e64b1e6e7f',
  'kitchen.py': 'f6d7e79160457c5518e1e40f36e25f34bd49f359',
  'dining_control.py': '80c4defa448f0e82671f743215a307705f5dd002',
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
  ['kitchen.py','admin_router','/api/v1/kitchen',['get /orders','patch /orders/{order_id}/status']],
  ['dining_control.py','router','/api/v1/dining',['get /floor','patch /orders/{order_id}/waiter']],
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
// These endpoints are present only on the separate platform candidate,
// not the pinned mobile-base backend. Do not label them LIVE.
const gaps = [
  'GET /api/v1/admin/pms/holds',
  'POST /api/v1/admin/pms/holds',
  'DELETE /api/v1/admin/pms/holds/{hold_id}',
];
const holdsPresent = existsSync(resolve(src,'pms_holds.py'));
process.stdout.write('MARINA MOBILE PINNED_BACKEND_ROUTES: ' + routeCount + '/' + routeCount + ' VERIFIED\n');
if (!holdsPresent) {
  process.stdout.write('MARINA MOBILE BLOCKED_BACKEND_ROUTES: ' + gaps.length + '\n' + gaps.map(s=>'  '+s).join('\n') + '\n');
  if (process.env.MARINA_MOBILE_RELEASE_GATE === 'strict') throw new Error('Mobile release blocked: PMS HOLD router absent from pinned backend');
}
