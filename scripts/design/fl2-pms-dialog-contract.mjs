import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {assertDialogBehavior,dialogNames} from './fl2-pms-dialog-source.mjs';
const base='8f252c0c01574dd6705ea104dd035634edea67e5';
for(const name of dialogNames){const p=`apps/admin/components/${name}.tsx`;assertDialogBehavior(fs.readFileSync(p,'utf8'),execFileSync('git',['show',`${base}:${p}`],{encoding:'utf8'}),name);}
const hook=fs.readFileSync('apps/admin/components/hooks/usePmsDialog.ts','utf8');assert.ok(!/fetch\(|WebSocket|XMLHttpRequest|localStorage/.test(hook));
for(const needle of ['future-luxury','event.key === "Escape"','event.key === "Tab"','!latest.current.busy','previous?.isConnected','removeEventListener','document.body.style.overflow = originalOverflow'])assert.ok(hook.includes(needle),needle);
assert.equal(fs.readFileSync('apps/admin/app/fl2-foundation.css','utf8'),execFileSync('git',['show',`${base}:apps/admin/app/fl2-foundation.css`],{encoding:'utf8'}));
console.log('PMS_DIALOG_CONTRACT_PASS: 3 dialog operational bodies, effects, API and all JSX handlers preserved; focus hook has no requests; palette unchanged');
