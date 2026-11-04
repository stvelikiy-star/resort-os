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
    bg: '#F5FAFF', surface: '#FFFFFF', surfaceAlt: '#EEF7FC', border: '#DCE8F3',
    text: '#10243D', textMuted: '#586D80', primary: '#073B70', primaryText: '#FFFFFF',
    primarySoft: '#DFF2FB', accent: '#D5A64B', success: '#176A54', successSoft: '#E2F5EC',
    warning: '#8D590E', warningSoft: '#FFF2D9', danger: '#AA303A', dangerSoft: '#FBE6EA',
    info: '#14659A', infoSoft: '#E0F2FC', heroFrom: '#061B38', heroTo: '#155A87',
    shadow: '#0C3455', glass: '#FFFFFF', glassBorder: '#DFEBF4', gold: '#D5A64B',
    cyan: '#007E9B', iris: '#6743B4', glow: '#E2F7FF', navActive: '#073B70',
    navInactive: '#63788D',
  },
  dark: {
    bg: '#061225', surface: '#10213D', surfaceAlt: '#172A49', border: '#2C4260',
    text: '#F4F8FF', textMuted: '#B3C6DC', primary: '#00D8FF', primaryText: '#061225',
    primarySoft: '#103B56', accent: '#E6BD70', success: '#61DFB7', successSoft: '#103C37',
    warning: '#F4CC7B', warningSoft: '#44351F', danger: '#FF9CA4', dangerSoft: '#48252D',
    info: '#91D6FF', infoSoft: '#163656', heroFrom: '#020C1D', heroTo: '#15385D',
    shadow: '#000000', glass: '#122A47', glassBorder: '#36506C', gold: '#E6BD70',
    cyan: '#00D8FF', iris: '#A987FF', glow: '#123951', navActive: '#00D8FF',
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
  cardStagger: 55, maxStaggerCards: 6,
  spring: { speed: 30, bounciness: 5 },
} as const;
export const iconography = { nav: 23, action: 22, metric: 24, stroke: 1.9, strokeActive: 2.5 } as const;
