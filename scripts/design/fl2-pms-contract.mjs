// C3 presentation-only contract; source checks do not certify live server behavior.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
const ts=createRequire(new URL('../../apps/admin/package.json',import.meta.url))('typescript');
const base='9f13104bddeffdd2c236dfacb0086e4eaa5d6bfc';
const read=p=>fs.readFileSync(p,'utf8');
const original=p=>execFileSync('git',['show',`${base}:${p}`],{encoding:'utf8'});
for(const name of ['PMSNewReservationModal','ReservationScheduleBuilder','RoomDetailModal','PMSGridV9','AdminShell','PMSControlSnapshotV9']) {
 const p=`apps/admin/components/${name}.tsx`;assert.equal(read(p),original(p),`${name}: protected source changed`);
}
const path='apps/admin/components/PMSOwnerGrid.tsx';
function functions(s){const ast=ts.createSourceFile(path,s,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const found={};function visit(n){if(ts.isFunctionDeclaration(n)&&n.name&&n.name.text!=='PMSOwnerGrid')found[n.name.text]=n.getText(ast);if(ts.isVariableDeclaration(n)&&n.initializer&&ts.isCallExpression(n.initializer)&&['useCallback','useMemo'].includes(n.initializer.expression.getText(ast)))found[n.name.getText(ast)]=n.getText(ast);ts.forEachChild(n,visit);}visit(ast);return found;}
assert.deepEqual(functions(read(path)),functions(original(path)),'Booking operations, filtering, prices or callbacks changed');
const api=s=>[...s.matchAll(/(?:fetch\([^;]+?\);|useEffect\(\(\) => \{[\s\S]*?\}, \[[^\]]*\]\);)/g)].map(m=>m[0]);
assert.deepEqual(api(read(path)),api(original(path)),'Requests or lifecycle changed');
assert.ok(!/fetch\(|XMLHttpRequest|WebSocket/.test(read('apps/admin/components/PmsBookingPreviewButton.tsx')));
const css=read('apps/admin/app/fl2-pms-composition.css').split('/* C3 —')[1];assert.ok(css);assert.ok(!/#[\da-f]{3,8}\b/i.test(css),'No new palette');
console.log('C3 contract PASS: protected modal sources, API/lifecycle, filters, selection/HOLD/open callbacks unchanged; read-only tooltip; shared tokens');
