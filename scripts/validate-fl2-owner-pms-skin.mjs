#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = rel => fs.readFileSync(path.join(root,rel),'utf8');
const assert = (condition, message) => { if(!condition) throw new Error('FL2 OWNER/PMS: '+message); };
const shell=read('apps/admin/components/AdminShell.tsx');
const css=read('apps/admin/app/fl2-owner-pms-finish.css');
const pref=read('apps/admin/lib/fl2-appearance.ts');
const layout=read('apps/admin/app/layout.tsx');
const dashboard=read('apps/admin/components/DashboardBoard.tsx');
const pms=read('apps/admin/components/PMSOwnerGrid.tsx');
assert(shell.includes('readFl2Theme()') && shell.includes('writeFl2Theme(nextTheme)'), 'appearance toggle not connected');
assert(shell.includes('document.documentElement.dataset.fl2Theme = fl2Theme'), 'theme not reflected in CSS root');
assert(shell.includes('chooseUiPreference("legacy")') && shell.includes('chooseUiPreference("future-luxury")'),'legacy/Future preference removed');
assert(shell.includes('aria-pressed={fl2Theme === "light"}') && shell.includes('aria-pressed={fl2Theme === "dark"}'),'theme accessible toggle removed');
assert(!/fetch\(|Prisma|API|password|token|property_code/.test(pref),'browser appearance helper handles business state');
assert(pref.includes('return "dark"') && pref.includes('"light"'),'appearance fallback absent');
assert(layout.includes('import "./fl2-owner-pms-finish.css"'),'CSS import missing');
for(const marker of [
  'html[data-marina-ui="future-luxury"] .owner-booking-modal',
  'html[data-marina-ui="future-luxury"][data-fl2-theme="light"]',
  'html[data-marina-ui="future-luxury"] .fl2-theme-switch',
  '.owner-pms-stack .owner-booking-bar',
  '.dashboard-shell[data-fl2-owner="true"] .attention-row',
  '@media(prefers-reduced-motion:reduce)'
]) assert(css.includes(marker),'CSS visual state missing: '+marker);
assert(dashboard.includes('fetch("/core/api/v1/admin/dashboard"'),'server-backed KPI removed');
for(const name of ['OwnerExecutivePack','OwnerControlV2','OwnerOperationsPerformance']) assert(dashboard.includes('<'+name+' />'),'owner dashboard section removed: '+name);
assert(pms.includes('PMSNewReservationModal') && pms.includes('ReservationScheduleBuilder') && pms.includes('RoomDetailModal'),'PMS operations changed');
assert(pms.includes('fetch(`/core/api/v1/pms/grid?'),'server-backed PMS missing');
console.log('FL2 OWNER/PMS visual PASS: legacy preserved, Dark/Light appearance only, real server data and booking components retained.');
