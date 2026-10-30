/**
 * Hard boundary: this application runs only in demo mode until a reviewed
 * mobile-auth contract and isolated staging endpoint are implemented.
 */
export const APP_MODE = 'DEMO' as const;
export const API_ENABLED = false as const;
export function assertNoLiveMutation(): never {
 throw new Error('Live PMS mutations are disabled in the MARINA STAFF prototype.');
}
