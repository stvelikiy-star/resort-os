// Separate foundation change: allow palette values/bridges, preserve product behavior and motion.
import assert from 'node:assert/strict';
import {assertDialogBehavior,dialogNames} from './fl2-pms-dialog-source.mjs';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {assertApprovedProfileShell} from './fl2-profile-source-contract.mjs';
const base='71ca55669838b063775325825258b7fe2c14e387';
const read=p=>fs.readFileSync(p,'utf8');
const original=p=>execFileSync('git',['show',`${base}:${p}`],{encoding:'utf8'});
const css=read('apps/admin/app/fl2-foundation.css');
const spec=JSON.parse(read('docs/design/FL2_WEB_REFERENCE_PALETTE.json'));
assert.deepEqual(spec.base,{navy:'#0B1F2A',teal:'#14B8A6',sky:'#0EA5E9',surface:'#1E293B',text:'#F8FAFC'});
const blocks=[...css.matchAll(/html\[data-marina-ui="future-luxury"\](?:\[data-fl2-theme="light"\])? \{([^}]+)\}/g)].slice(0,2).map(m=>m[1]);
for(const [i,theme] of ['dark','light'].entries())for(const [key,value] of Object.entries(spec[theme]))assert.equal(blocks[i].match(new RegExp(`--mx-${key}:\\s*([^;]+);`))?.[1],value,`${theme}/${key}`);
for(const name of ['DashboardBoard','OwnerControlV2','PMSOwnerGrid','PMSNewReservationModal','ReservationScheduleBuilder','RoomDetailModal','fl2/Fl2','fl2/OwnerCommandCenter']){const p=`apps/admin/components/${name}.tsx`;if(dialogNames.includes(name))assertDialogBehavior(read(p),original(p),name);else assert.equal(read(p),original(p),`${name} product logic changed`);}
const shellPath='apps/admin/components/AdminShell.tsx';
const appearanceImport='import FutureLuxuryAppearance from "./FutureLuxuryAppearance";\n';
const shell=read(shellPath);
assert.ok(shell.includes(appearanceImport),'Reference: approved appearance import absent');
const previousShell=assertApprovedProfileShell(shell);
assert.equal(previousShell.replace(appearanceImport,''),original(shellPath),'Reference: protected behavior changed');
const unchangedRules=s=>s.split('/* REFERENCE_BRIDGE')[0].replace(/  --mx-surface:[^;]+;\n/g,'').replace(/--mx-[a-z-]+:\s*[^;]+;/g,'').trim();
assert.equal(unchangedRules(css),unchangedRules(original('apps/admin/app/fl2-foundation.css')),'Original component sizing/motion changed');
assert.ok(!/!important|display:\s*none|visibility:\s*hidden/.test(css.split('/* REFERENCE_BRIDGE')[1]),'Do not hide or force components');
const lum=rgb=>rgb.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
const color=s=>s.startsWith('#')?[1,3,5].map(i=>parseInt(s.slice(i,i+2),16)).concat(1):s.match(/[\d.]+/g).map(Number);
const over=(a,b)=>a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1)));
const ratios=[];
for(let i=0;i<2;i++){const values=Object.fromEntries([...blocks[i].matchAll(/--mx-([a-z-]+):\s*([^;]+);/g)].map(m=>[m[1],m[2]]));const bg=color(values.bg);for(const surface of ['bg','surface','glass','glass-strong']){const b=over(color(values[surface]),bg);for(const fg of ['ink','muted','accent','info','success','warning','danger']){const ls=[lum(color(values[fg])),lum(b)].sort((a,b)=>a-b);const ratio=(ls[1]+.05)/(ls[0]+.05);assert.ok(ratio>=4.5,`${i}/${fg}/${surface}: ${ratio}`);ratios.push(ratio);}}
 const pair=[lum(color(values['accent-ink'])),lum(color(values.accent))].sort((a,b)=>a-b);assert.ok((pair[1]+.05)/(pair[0]+.05)>=4.5);}
console.log(`REFERENCE_FOUNDATION_PASS: approved 5 base swatches; ${ratios.length+2} text/surface pairs >=4.5; component behavior/API/motion preserved; minimum ${Math.min(...ratios).toFixed(2)}`);
