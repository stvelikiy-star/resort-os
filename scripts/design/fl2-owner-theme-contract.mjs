// C2 permits theme/legibility changes, not API, financial calculations or actions.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
const base='542c67a6bd6b3b415784164dc45e80ec68e14834';
const read=p=>fs.readFileSync(p,'utf8');
const original=p=>execFileSync('git',['show',`${base}:${p}`],{encoding:'utf8'});
for(const name of ['OwnerExecutivePack','OwnerOperationsPerformance','OwnerOccupancyMatrix'])assert.equal(read(`apps/admin/components/${name}.tsx`),original(`apps/admin/components/${name}.tsx`),`${name}: unexpected source change`);
// C2 source-immutability is maintained; the later approved FL2 shell integration
// adds precisely one presentation import. No auth, RBAC or navigation code may drift.
const shellPath='apps/admin/components/AdminShell.tsx';
const shell=read(shellPath);
const appearanceImport='import FutureLuxuryAppearance from "./FutureLuxuryAppearance";\n';
assert.ok(shell.includes(appearanceImport),'FL2 appearance integration import must be present');
// A single reviewed Profile menu replaces visible floating preference controls.
 // Pin the exact presentation-only action block. Changes to auth, RBAC, tabs,
 // navigation and business handlers still fail byte-for-byte source comparison.
const previousShell=execFileSync('git',['show','4f2548b827d282d9eae6988336a8a033be1682af:'+shellPath],{encoding:'utf8'});
const actionBlock=source=>{
  const start=source.indexOf('        <div className="admin-shell-actions">');
  const marker='\n      </div>\n      {user.module_permissions.length';
  const end=source.indexOf(marker,start);
  assert.ok(start>=0 && end>start,'Admin profile action boundaries must be present');
  return source.slice(start,end).trimEnd();
};
const currentActions=actionBlock(shell);
assert.equal(createHash('sha256').update(currentActions).digest('hex'),
  '635ebeac55f15d3d65001aa838291d48717623a13a2bb4e56c9980f34b7a798f',
  'Admin account settings must match reviewed presentation-only markup');
const oldActions=actionBlock(previousShell);
const normalizedShell=shell
  .replace('SlidersHorizontal, Moon, Sun, Sparkles','SlidersHorizontal, Sparkles')
  .replace('>Классика</button>','>Legacy</button>')
  .replace('<Moon size={16} aria-hidden="true" /><span>Тёмная</span>','☾ Dark')
  .replace('<Sun size={16} aria-hidden="true" /><span>Светлая</span>','☀ Light')
  .replace(currentActions,oldActions);
assert.equal(normalizedShell,previousShell,'AdminShell: auth, RBAC and navigation source must remain unchanged');
assert.equal(previousShell.replace(appearanceImport,''),original(shellPath),
  'Previously approved AdminShell must still match the immutable C2 source baseline');
const control='apps/admin/components/OwnerControlV2.tsx';
assert.equal(read(control).replace(' tabIndex={0} role="region" aria-label="Загрузка по дням"',''),original(control));
const center='apps/admin/components/fl2/OwnerCommandCenter.tsx';
assert.equal(read(center).replace('<h1>Добро пожаловать в MARINA SMART!</h1>','<h1>Command Center</h1>'),original(center));
assert.equal(read('apps/admin/components/fl2/Fl2.tsx'),original('apps/admin/components/fl2/Fl2.tsx'),'Fl2 component logic changed');
// Foundation color declarations may change only through the separate reference foundation contract.
const stripTokens=s=>s.replace(/  --mx-surface:[^;]+;\n/g,'').replace(/--mx-[a-z-]+:\s*[^;]+;/g,'').trim();
assert.equal(stripTokens(read('apps/admin/app/fl2-foundation.css').split('/* REFERENCE_BRIDGE')[0]),stripTokens(original('apps/admin/app/fl2-foundation.css')),'Foundation component/motion rules changed');
const css=read('apps/admin/app/fl2-owner-composition.css').split('/* C2 —')[1];
assert.ok(css);assert.ok(!/#[\da-f]{3,8}\b/i.test(css),'C2 must use shared tokens, no new palette');
assert.ok(!/display:\s*none|visibility:\s*hidden/.test(css),'Do not hide analytics to pass layout checks');
assert.equal(createHash('sha256').update(fs.readFileSync('apps/admin/public/marina-smart-approved.png')).digest('hex'),'24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356');
console.log('C2 source contract PASS: API/calculations/actions and Legacy component sources preserved; shared tokens; approved logo');
