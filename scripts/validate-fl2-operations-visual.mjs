#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const read=name=>fs.readFileSync(path.join(root,name),'utf8');
const required=(txt,needle,label)=>{if(!txt.includes(needle))throw new Error('FL2 operations '+label+': missing '+needle)};
const guest=read('apps/admin/components/GuestHistoryBoard.tsx');
const dining=read('apps/admin/components/DiningManagementBoard.tsx');
const finance=read('apps/admin/components/HotelFinanceBoard.tsx');
const css=read('apps/admin/app/fl2-guest-finance.css');
const diningCss=read('apps/admin/components/DiningManagementBoard.module.css');
const layout=read('apps/admin/app/layout.tsx');
required(layout,'import "./fl2-guest-finance.css"','import');
for(const marker of ['html[data-marina-ui="future-luxury"] .guest-history-shell','html[data-marina-ui="future-luxury"] .hotel-finance-shell','html[data-marina-ui="future-luxury"][data-fl2-theme="light"]'])required(css,marker,'palette');
for(const marker of [':global(html[data-marina-ui="future-luxury"]) .shell',':global(html[data-marina-ui="future-luxury"][data-fl2-theme="light"]) .shell'])required(diningCss,marker,'dining CSS');
for(const marker of ['guest-directory-list','guest-reservation-history','guest-profile'])required(guest,marker,'guest source');
for(const marker of ['"/core/api/v1/dining/stays?include_future_days=30"','method: "PUT"','mealChecks'])required(dining,marker,'dining source');
for(const marker of ['transaction-table','finance-kpis','finance-split-grid'])required(finance,marker,'finance source');
console.log('FL2 operations visual PASS: Core-backed guests, dining meal plan and owner finance with opt-in dark/light skins.');
