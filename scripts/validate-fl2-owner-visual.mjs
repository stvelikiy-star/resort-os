#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname,'..');
const read = f=>fs.readFileSync(path.join(root,f),'utf8');
const fail = m=>{throw new Error('FL2 OWNER visual parity: '+m);};
const view = read('apps/admin/components/DashboardBoard.tsx');
const skin = read('apps/admin/app/fl2-owner-dashboard.css');
const layout = read('apps/admin/app/layout.tsx');
const baselineSections = ['<OwnerExecutivePack />','<OwnerControlV2 />','<OwnerOperationsPerformance />','<section className="command-kpis">','<section className="command-grid">'];
for(const section of baselineSections) if(!view.includes(section))fail('OWNER functional section removed: '+section);
for(const text of ['data-fl2-owner={isOwner ? "true" : undefined}','fetch("/core/api/v1/admin/dashboard"','onClick={load}','data.stays.occupancy_percent','data.finance.confirmed_payments_today_kgs']){
 if(!view.includes(text)) fail('source route/action/metric removed: '+text);
}
if(!layout.includes('import "./fl2-owner-dashboard.css";')) fail('OWNER opt-in skin not loaded');
const raw = skin.match(/(^|\n)[^@\n{]+\{/g)||[];
for(const selector of raw) {
 if(selector.includes('.dashboard-shell')&&!selector.includes('[data-fl2-owner="true"]'))fail('unscoped dashboard CSS: '+selector);
}
if(!skin.includes('prefers-reduced-motion'))fail('Reduced Motion override missing');
if(!skin.includes('html[data-marina-ui="future-luxury"]'))fail('Future Luxury opt-in guard missing');
console.log('FL2 OWNER visual PASS: existing source metrics, actions, three owner modules, opt-in CSS, reduced-motion policy.');
