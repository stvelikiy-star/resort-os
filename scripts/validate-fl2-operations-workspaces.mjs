#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const base=path.resolve(import.meta.dirname,'..');
const read=p=>fs.readFileSync(path.join(base,p),'utf8');
const requireText=(text,needle,name)=>{if(!text.includes(needle))throw Error('FL2 visual parity: '+name+' missing '+needle);};
const layout=read('apps/admin/app/layout.tsx');
const ops=read('apps/admin/components/OperationsBoard.tsx');
const rules=read('apps/admin/components/HotelRulesBoard.tsx');
const growth=read('apps/admin/components/GrowthControlBoard.tsx');
const media=read('apps/admin/components/SiteMediaBoard.tsx');
const css=read('apps/admin/app/fl2-operations-knowledge-growth.css');
const mediaCss=read('apps/admin/components/SiteMediaBoard.module.css');
requireText(layout,'import "./fl2-operations-knowledge-growth.css";','layout CSS');
for(const [name,source,markers] of [
  ['operations',ops,['work-shell fl2-ops','/core/api/v1/ops/tasks?limit=250','/core/api/v1/ops/tasks/${task.id}/status','/core/api/v1/ops/tasks/${task.id}/assignee','className="task-create"','className="task-history"','onSubmit={createTask}','updateStatus(task, "IN_INSPECTION")']],
  ['MARINA AI hotel rules',rules,['work-shell management-shell fl2-hotel-rules','/core/api/v1/admin/hotel-rules','onSubmit={save}','window.confirm','aria-pressed={activeTopic===index}','hotel-knowledge-payment']],
  ['CRM growth',growth,['growth-shell','Outbound authority: NONE_AUTOMATIC','growth-policy','growth-modal','onSubmit={submitFeedback}','createFromCandidate(candidate','patchStatus(item']],
  ['site media',media,['styles.shell','styles.library','styles.previewGrid','styles.upload','styles.slot','saveDraft(slot)','publish(slot)','type="file"']]
])for(const marker of markers)requireText(source,marker,name);
for(const marker of ['.fl2-ops .task-card','.fl2-ops .task-history','.fl2-ops .task-create','.fl2-hotel-rules .hotel-knowledge-tabs','.fl2-hotel-rules .hotel-knowledge-topic','.growth-policy','.growth-modal','data-fl2-theme="light"','prefers-reduced-motion'])requireText(css,marker,'operations visuals');
for(const marker of [':global(html[data-marina-ui="future-luxury"]) .shell',':global(html[data-marina-ui="future-luxury"][data-fl2-theme="light"]) .shell','.upload','.previewGrid','.library','.slot','.actions .primary'])requireText(mediaCss,marker,'media visual');
if(css.includes('display:none!important')||css.includes('pointer-events:none!important'))throw Error('operations CSS hides controls');
console.log('FL2 operations parity PASS: original task actions, MARINA AI rules/save, CRM no-outbound policy and site media uploads/publish retained.');
