#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root=path.resolve(import.meta.dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const requireMarker=(text,marker,file)=>{
 if(!text.includes(marker))throw new Error("FL2 Reception missing "+marker+" in "+file);
};
const css=read("apps/admin/app/fl2-reception-visual.css");
const reception=read("apps/admin/components/ReceptionBoard.tsx");
const readiness=read("apps/admin/components/ReceptionWorkspace.tsx");
const layout=read("apps/admin/app/layout.tsx");
for(const marker of [
 'html[data-marina-ui="future-luxury"] .reception-card',
 'html[data-marina-ui="future-luxury"] .reservation-detail',
 'html[data-marina-ui="future-luxury"][data-fl2-theme="light"]',
 'html[data-marina-ui="future-luxury"] .reception-controls',
 '@media(prefers-reduced-motion:reduce)'
])requireMarker(css,marker,"reception skin");
requireMarker(layout,'import "./fl2-reception-visual.css";',"layout");
for(const marker of [
 'fetch("/core/api/v1/admin/reception/reservations?limit=500"',
 'transition(item, "check-in")',
 'transition(item, "check-out")',
 'openDetail(item.id)',
 'setFilter(e.target.value as Filter)',
])requireMarker(reception,marker,"reception UI");
for(const marker of [
 '<ReceptionBoard />',
 '<RoomBlocksPanel />',
 'sendHousekeeping(item)',
 'onNavigate("OPS")'
])requireMarker(readiness,marker,"reception workspace");
console.log("FL2 reception visual PASS: original list, check-in/out, booking modal, filter, housekeeping and both themes preserved.");
