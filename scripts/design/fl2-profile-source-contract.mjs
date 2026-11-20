// Shared read-only guard for the approved Profile menu presentation delta.
 // Auth, RBAC, navigation, and business handlers must stay byte-identical.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";

export function assertApprovedProfileShell(shell) {
  const shellPath = "apps/admin/components/AdminShell.tsx";
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
  return previousShell;
}
