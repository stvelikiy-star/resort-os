/** Browser-local appearance choice only. Never store simulated data, session identity,
 * hotel context, payments, permissions, tokens or business state here. */
export type MarinaUiPreference = 'legacy' | 'future-luxury';
const KEY = 'marina-admin-ui';

export function readMarinaUiPreference(): MarinaUiPreference {
  if (typeof window === 'undefined') return 'legacy';
  try {
    // The approved Future Luxury design is the default for new users.
    // Preserve Legacy for anyone who explicitly selected it.
    return window.localStorage.getItem(KEY) === 'legacy' ? 'legacy' : 'future-luxury';
  } catch {
    return 'future-luxury';
  }
}

export function writeMarinaUiPreference(next: MarinaUiPreference): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(KEY, next);
  } catch {
    // Appearance still works in memory; no business data depends on browser storage.
  }
}
