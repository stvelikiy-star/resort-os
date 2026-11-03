import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Static contract gate only. Confirms mobile routes still exist in the same
 * repository tree; it is NOT a network E2E or runtime authentication test.
 * Server modules are intentionally read-only.
 */
const src = resolve(process.cwd(), '../../services/api/app');
const contracts = [
  ['auth.py', '/api/v1/auth', ['post /login', 'post /logout', 'get /me']],
  ['operations.py', '/api/v1/ops', ['get /tasks', 'post /tasks', 'post /tasks/{task_id}/claim', 'patch /tasks/{task_id}/status', 'patch /rooms/{room_id}/state']],
  ['staff_task_reports.py', '/api/v1/ops', ['post /tasks/{task_id}/complete-report']],
  ['operations_assignment.py', '/api/v1/ops', ['patch /tasks/{task_id}/assignee']],
  ['staff_control.py', '/api/v1/admin/staff', ['get /overview']],
];
let count = 0;
for (const [filename, prefix, endpoints] of contracts) {
  const code = readFileSync(resolve(src, filename), 'utf8');
  if (!code.includes(`APIRouter(prefix="${prefix}"`)) {
    throw new Error(`API prefix changed in ${filename}: expected ${prefix}`);
  }
  for (const entry of endpoints) {
    const [method, ...rest] = entry.split(' ');
    const path = rest.join(' ');
    if (!code.includes(`@router.${method}("${path}"`)) {
      throw new Error(`Missing route ${method.toUpperCase()} ${prefix}${path} in ${filename}`);
    }
    count++;
  }
}
process.stdout.write(`MARINA STAFF static backend route contract: ${count}/${count} PASS\\n`);
