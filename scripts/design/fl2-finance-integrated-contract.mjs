// Integration-preservation audit for the combined FL2 + OWNER finance Draft candidate.
// This is a source contract, not a substitute for browser, device or live-API E2E.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
const read=p=>fs.readFileSync(p,'utf8');
const has=(path,needles)=>{const source=read(path);for(const needle of needles)assert.ok(source.includes(needle),`${path}: missing ${needle}`);return source;};
has('apps/staff/app/manifest.ts',['/icon-192.png','/icon-512.png','/icon-maskable-512.png','#0B1F2A']);
assert.ok(!read('apps/staff/app/manifest.ts').includes('/icon.svg'),'Staff PWA must not install the old III logo');
// Retain the original approved product logo and require the exact brand-derived
// PNG blobs reviewed in #552, including safe-zone maskable and Android foreground.
const approvedBlobs = {
  'apps/staff/public/marina-smart-approved.png': '284cda0b7294a3626ada0d598f820faf4eb1500f',
  'apps/staff/public/icon-192.png': '0a4896f78b47bdc4df79e13c2f13980fb239d91d',
  'apps/staff/public/icon-512.png': '08e0fc96c2995a54ad6eb04ed5416b5ae87a4d65',
  'apps/staff/public/icon-maskable-512.png': '65a4c7968000cc60d87c45a921e7006db69c8a68',
  'apps/mobile/assets/marina-smart-adaptive-foreground.png': '322bb875f45fcc1491fafb63c90e666e533bd2ca',
};
for(const [path,expected] of Object.entries(approvedBlobs)) {
  const contents=fs.readFileSync(path);
  const sha=createHash('sha1').update(Buffer.from(`blob ${contents.length}\\0`)).update(contents).digest('hex');
  assert.equal(sha,expected,`Brand asset changed unexpectedly: ${path}`);
}
has('apps/mobile/src/theme/moduleIcons.ts',['store: Package','overview: LayoutDashboard','reception: ConciergeBell']);
has('apps/mobile/src/roles/registry.ts',["STORE_STAFF: ['store', 'profile']","store: 'DINING'"]);
has('apps/mobile/src/components/OwnerExpenses.tsx',['postOwnerExpense','settleOwnerExpense','onCommitted?.()',"cancel:'Жокко чыгаруу'","cancel:'Cancel'"]);
has('apps/mobile/app/finance.tsx',['ownerKitchenManagement','ownerRecordedCashMovements','onCommitted={refreshFinancialSnapshots}','reloadKitchen()','reloadCash()']);
has('apps/mobile/src/api/liveModules.ts',['ownerKitchenManagement','ownerRecordedCashMovements','postOwnerExpense','settleOwnerExpense']);
has('apps/admin/components/HotelFinanceBoard.tsx',['owner_supplier_stock_snapshot','recognized_profit_kgs','is_recognized_profit_complete']);
const adminRuntime=has('apps/admin/components/AdminExperienceRuntime.tsx',['OWNER · склад и себестоимость','ИЕСІ · қойма және өзіндік құн','ЭЭСИ · кампа жана өздүк нарк','Inventory carrying value']);
assert.ok(adminRuntime.includes('KZ_EXACT') && adminRuntime.includes('const exact:'),'KZ fallback and full locale dictionary both required');
has('services/api/app/owner_kitchen_reconciliation.py',['recognized_profit_kgs']);
has('apps/admin/components/AdminShell.tsx',['FutureLuxuryAppearance','data-fl2-theme']);
has('apps/mobile/src/components/Motion.tsx',['useMotionPreference','motionPresets','stopAnimation']);
has('apps/mobile/src/theme/motion.ts',['isReduceMotionEnabled','reduceMotionChanged','AppState.currentState']);
for(const p of ['packages/database/prisma/migrations/zz120_marina_owner_expenses_20261115/migration.sql','packages/database/prisma/migrations/zz121_marina_supplier_documents_20261116/migration.sql','packages/database/prisma/migrations/zz122_marina_supplier_returns_20261116/migration.sql'])assert.ok(fs.statSync(p).size>0,p);
console.log('FL2_FINANCE_INTEGRATION_PRESERVATION_PASS: brand, role, finance API, refresh, supplier valuation, i18n, owner profit gate, and migrations');
