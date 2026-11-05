import type { TabKey } from './registry';

/** Keep at most four task-oriented routes plus one More tab on narrow phones.
 * Inputs must already come from workspaceForSession; this function NEVER grants access.
 */
export function mobileTabPlan(allowed: readonly TabKey[]) {
  const unique = Array.from(new Set(allowed));
  if (unique.length <= 4) return { primary: unique, overflow: [] as TabKey[], showMore: false };
  return { primary: unique.slice(0, 4), overflow: unique.slice(4), showMore: true };
}
