// C1: compare the new grouped navigation to the actual pre-C1 Legacy gates.
// Source equivalence is not a substitute for browser or server authorization checks.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { execFileSync } from 'node:child_process';
const baseline = execFileSync('git', ['show', 'eb7384c9bdeb8471b1dc3a11c6d8e27aa6a1f807:apps/admin/components/AdminShell.tsx'], { encoding: 'utf8' });
const source = fs.readFileSync('apps/admin/components/AdminShell.tsx', 'utf8');
const legacy = s => s.slice(s.indexOf('<nav className="admin-tabs"'), s.indexOf('</nav>', s.indexOf('<nav className="admin-tabs"')) + 6);
assert.equal(legacy(source), legacy(baseline), 'Legacy nav changed');
assert.equal(source.slice(source.indexOf('{user.module_permissions.length === 0'), source.indexOf('      {uiPreference === "legacy" && <MarinaAiAssistant')), baseline.slice(baseline.indexOf('{user.module_permissions.length === 0'), baseline.indexOf('      <MarinaAiAssistant screen={tab}')), 'Board rendering/RBAC gates changed');
const declaration = source.slice(source.indexOf('const FL2_NAV_GROUPS'), source.indexOf('function initialTab'));
const items = [...declaration.matchAll(/\{ tab: "([A-Z_]+)", label: "[^"]+", icon: \w+(?:, module: "([A-Z_]+)")? \}/g)].map(m => ({ tab: m[1], module: m[2] }));
const oldItems = [...legacy(baseline).matchAll(/\{([^{}]+?)&& <button className=\{tab === "([A-Z_]+)"/g)].map(m => ({ tab:m[2], module: m[1].match(/moduleEnabled\("([A-Z_]+)"\)/)?.[1] }));
assert.equal(items.length,26); assert.equal(new Set(items.map(i=>i.tab)).size,26); assert.equal(oldItems.length,26);
assert.equal([...declaration.matchAll(/title: "/g)].length,6);
assert.deepEqual(items.toSorted((a,b)=>a.tab.localeCompare(b.tab)),oldItems.toSorted((a,b)=>a.tab.localeCompare(b.tab)));
const roles = JSON.parse(execFileSync('python3',['-c', 'import runpy,json; print(json.dumps(runpy.run_path("services/api/app/section_permissions.py")["DEFAULT_ROLE_MODULES"]))'],{encoding:'utf8'}));
const modules=items.filter(i=>i.module).map(i=>i.module);
const grants=[...Object.values(roles),[],...items.map(i=>[i.tab]),items.map(i=>i.tab)];
let cases=0;
for(let mask=0;mask<2**modules.length;mask++) {
 const enabled=new Set(modules.filter((_,i)=>mask&(1<<i)));
 for(const permissions of grants) {
  const show = list => list.filter(i=>permissions.includes(i.tab)&&(!i.module||enabled.has(i.module))).map(i=>i.tab).sort();
  assert.deepEqual(show(items),show(oldItems)); cases++;
 }
}
console.log(`C1 navigation contract PASS: 26 tabs, 6 groups, ${cases} permission/module combinations; Legacy nav and board gates byte-identical`);
