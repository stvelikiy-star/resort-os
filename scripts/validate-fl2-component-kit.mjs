#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = f => fs.readFileSync(path.join(root,f),'utf8');
const fail = m => { throw new Error('FL2 component kit: '+m); };
const ui = read('apps/mobile/src/components/ui.tsx');
const required = {
 primary: 'CircleDot',
 success: 'CheckCircle2',
 warning: 'AlertTriangle',
 danger: 'XCircle',
 info: 'Info'
};
for(const [tone,Icon] of Object.entries(required)){
 if(!ui.includes(`${tone}: ${Icon}`)) fail('missing accessible Mobile status icon: '+tone);
}
if(!ui.includes('icon: Icon') || !ui.includes('Icon ??') || !ui.includes('{label}</Text>')){
 fail('Mobile Badge changed its existing icon/label API');
}
for(const pathName of ['apps/mobile/src/components/Future.tsx','apps/mobile/src/components/domain.tsx']){
 const source=read(pathName);
 if(!source.includes('Badge')) fail('Existing badge consumer removed: '+pathName);
}
const css = read('apps/admin/app/fl2-ui-kit.css');
for(const selector of ['.fl2-card','.fl2-badge','.fl2-button',':focus-visible','prefers-reduced-motion']){
 if(!css.includes(selector))fail('web kit missing '+selector);
}
if(/(^|\n)\s*body\s*\{|(^|\n)\s*\.dashboard-shell\s*\{/.test(css))fail('web kit uses forbidden global override');
const layout=read('apps/admin/app/layout.tsx');
if(!layout.includes('"./fl2-ui-kit.css"'))fail('Admin kit CSS not imported');
console.log('FL2 component kit PASS: existing Mobile Badge text/callback API, five semantic Lucide tones, scoped Admin UI classes, reduced motion.');
