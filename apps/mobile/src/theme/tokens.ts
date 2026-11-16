export type ThemeName = 'light' | 'dark';

/**
 * MARINA FUTURE LUXURY — design targets from the 03.11.2026 brief.
 * Keep the existing compass-and-ship image as the ONLY mobile logo pending a
 * pixel-level sign-off against original source artwork. Accent is not body text.
 */
export const palette = {
  teal: '#087F96', tealDeep: '#073B70', navy: '#073B70',
  sand: '#D5A64B', coral: '#C64E55', green: '#17745F',
  amber: '#AE7022', blue: '#1665A2',
  champagne: '#D5A64B', cyan: '#00CFE8', iris: '#9C6BFF',
} as const;

export interface Colors {
  bg: string; surface: string; surfaceAlt: string; border: string;
  text: string; textMuted: string; primary: string; primaryText: string;
  primarySoft: string; accent: string; success: string; successSoft: string;
  warning: string; warningSoft: string; danger: string; dangerSoft: string;
  info: string; infoSoft: string; heroFrom: string; heroTo: string; shadow: string;
  glass: string; glassBorder: string; gold: string; cyan: string; iris: string;
  glow: string; navActive: string; navInactive: string;
}
export const colors: Record<ThemeName, Colors> = {
  light: {
    bg: '#F1F7F8', surface: '#FFFFFF', surfaceAlt: '#EEF7FC', border: '#DCE8F3',
    text: '#0B1F2A', textMuted: '#586D80', primary: '#0F766E', primaryText: '#FFFFFF',
    primarySoft: '#DDF3EF', accent: '#0F766E', success: '#176A54', successSoft: '#E2F5EC',
    warning: '#8D590E', warningSoft: '#FFF2D9', danger: '#AA303A', dangerSoft: '#FBE6EA',
    info: '#14659A', infoSoft: '#E0F2FC', heroFrom: '#061B38', heroTo: '#155A87',
    shadow: '#0C3455', glass: '#FFFFFF', glassBorder: '#DFEBF4', gold: '#8A5A00',
    cyan: '#007E9B', iris: '#6743B4', glow: '#E2F7FF', navActive: '#0F766E',
    navInactive: '#586D80',
  },
  dark: {
    bg: '#0B1F2A', surface: '#1E293B', surfaceAlt: '#203440', border: '#2C4260',
    text: '#F8FAFC', textMuted: '#B3C6DC', primary: '#14B8A6', primaryText: '#0B1F2A',
    primarySoft: '#103B36', accent: '#14B8A6', success: '#61DFB7', successSoft: '#103C37',
    warning: '#F4CC7B', warningSoft: '#44351F', danger: '#FF9CA4', dangerSoft: '#48252D',
    info: '#91D6FF', infoSoft: '#163656', heroFrom: '#06151E', heroTo: '#0E3540',
    shadow: '#000000', glass: '#142C36', glassBorder: '#36505C', gold: '#E6BD70',
    cyan: '#14B8A6', iris: '#A987FF', glow: '#103B36', navActive: '#14B8A6',
    navInactive: '#B3C6DC',
  },
};
export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32, huge: 40 } as const;
export const radius = { sm: 12, md: 18, lg: 24, xl: 30, pill: 999 } as const;
export const font = {
  display: { fontSize: 34, fontWeight: '800' as const, letterSpacing: -1.1 },
  title: { fontSize: 27, fontWeight: '800' as const, letterSpacing: -0.6 },
  h2: { fontSize: 19, fontWeight: '700' as const, letterSpacing: -0.3 },
  body: { fontSize: 16, fontWeight: '500' as const, lineHeight: 24 },
  small: { fontSize: 13, fontWeight: '500' as const, lineHeight: 19 },
  label: { fontSize: 12, fontWeight: '700' as const, letterSpacing: 0.6 },
  metric: { fontSize: 30, fontWeight: '800' as const, letterSpacing: -0.6 },
} as const;
export const elevation = { card: { shadowOpacity: 0.08, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 3 }, floating: { shadowOpacity: 0.18, shadowRadius: 26, shadowOffset: { width: 0, height: 12 }, elevation: 9 } } as const;
export const TOUCH = 56;
export const motion = {
  press: 125, tab: 220, card: 320, modal: 340, chart: 700,
  /** Bottom sheet: enter is slightly slower than exit so dismissal never feels sluggish. */
  sheetIn: 320, sheetOut: 220,
  /** Server-confirmed status swap and tab-icon focus. */
  status: 240, tabIcon: 200,
  /** Bounded "work in progress" loops: pulses/rotations before settling static. */
  maxShimmerPulses: 3, maxOrbTurns: 8,
  cardStagger: 55, maxStaggerCards: 6,
  spring: { speed: 30, bounciness: 5 },
} as const;
export const iconography = { nav: 23, action: 22, metric: 24, stroke: 1.9, strokeActive: 2.5 } as const;
