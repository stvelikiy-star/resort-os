import { useEffect, useState } from 'react';
import { AccessibilityInfo, AppState, Easing } from 'react-native';
import { motion } from './tokens';

export const motionPresets = {
  entrance: { duration: motion.card, easing: Easing.out(Easing.cubic) },
  modal: { duration: motion.modal, easing: Easing.out(Easing.cubic) },
  press: { duration: motion.press, easing: Easing.out(Easing.cubic) },
  tab: { duration: motion.tab, easing: Easing.out(Easing.cubic) },
  chart: { duration: motion.chart, easing: Easing.out(Easing.cubic) },
} as const;
/** Resolves the OS preference before an entrance animation makes content visible.
 * Never run motion while backgrounded; Reduced Motion always takes priority.
 */
export function useMotionPreference(): { allowed: boolean; ready: boolean } {
  const [state, setState] = useState({ allowed: false, ready: false });
  useEffect(() => {
    let live = true;
    const read = async () => {
      try {
        const reduce = await AccessibilityInfo.isReduceMotionEnabled();
        if (live) setState({ allowed: !reduce && AppState.currentState === 'active', ready: true });
      } catch {
        if (live) setState({ allowed: false, ready: true });
      }
    };
    void read();
    const motionSub = AccessibilityInfo.addEventListener('reduceMotionChanged', () => { void read(); });
    const stateSub = AppState.addEventListener('change', () => { void read(); });
    return () => { live = false; motionSub.remove(); stateSub.remove(); };
  }, []);
  return state;
}
export function useMotionAllowed(): boolean {
  return useMotionPreference().allowed;
}
export function cappedStagger(index: number): number {
  return Math.min(Math.max(index, 0), motion.maxStaggerCards) * motion.cardStagger;
}
