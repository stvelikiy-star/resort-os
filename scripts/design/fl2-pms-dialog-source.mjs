// Compare all operational statements and JSX handlers, while permitting dialog presentation changes.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const ts=createRequire(new URL('../../apps/admin/package.json',import.meta.url))('typescript');
export const dialogNames=['PMSNewReservationModal','ReservationScheduleBuilder','RoomDetailModal'];
export function assertDialogBehavior(source,baseline,name){
 const parse=s=>{const ast=ts.createSourceFile(name+'.tsx',s,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);const root=ast.statements.find(n=>ts.isFunctionDeclaration(n)&&n.name?.text===name);assert.ok(root,name+' export missing');
  const body=root.body.statements.filter(n=>!ts.isReturnStatement(n)&&!n.getText(ast).startsWith('const dialogRef = usePmsDialog(')).map(n=>n.getText(ast));
  const events=[];function visit(n){if(ts.isJsxAttribute(n)&&n.name.getText(ast).startsWith('on'))events.push(n.getText(ast));ts.forEachChild(n,visit);}visit(root);
  return {parameters:root.parameters.map(n=>n.getText(ast)),body,events,top:ast.statements.filter(n=>n!==root&&!ts.isImportDeclaration(n)).map(n=>n.getText(ast))};
 };
 assert.deepEqual(parse(source),parse(baseline),name+': API, effects, calculations, state or JSX event handlers changed');
 assert.equal((source.match(/const dialogRef = usePmsDialog\(onClose, (?:busy|busyState !== null)\);/g)||[]).length,1,name+': explicit focus hook expected');
 assert.ok(source.includes('ref={dialogRef} tabIndex={-1}'),name+': focus root missing');
}
