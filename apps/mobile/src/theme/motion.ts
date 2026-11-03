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
/** False = no animation work in screen readers' Reduced Motion state. */
export function useMotionAllowed(): boolean {
  const [allowed, setAllowed] = useState(false); // safe first render avoids a flash
  useEffect(() => {
    let live = true;
    const read = async () => {
      try { const reduce = await AccessibilityInfo.isReduceMotionEnabled(); if (live) setAllowed(!reduce && AppState.currentState === 'active'); }
      catch { if (live) setAllowed(false); }
    };
    void read();
    const motionSub = AccessibilityInfo.addEventListener('reduceMotionChanged', () => { void read(); });
    const stateSub = AppState.addEventListener('change', () => { void read(); });
    return () => { live = false; motionSub.remove(); stateSub.remove(); };
  }, []);
  return allowed;
}
export function cappedStagger(index: number): number {
  return Math.min(Math.max(index, 0), motion.maxStaggerCards) * motion.cardStagger;
}
