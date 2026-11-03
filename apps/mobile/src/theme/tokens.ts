export type ThemeName = 'light' | 'dark';

/** MARINA SMART: midnight navy, deep ocean blue and silver, derived from the approved compass/ship brand artwork. */
export const palette = {
  teal: '#245E9A', // compatibility alias for existing components
  tealDeep: '#071D3C',
  navy: '#081B35',
  sand: '#DDE6F1', // silver, not the old gold
  coral: '#DA655B',
  green: '#21815D',
  amber: '#BD851F',
  blue: '#3275C1',
};

export interface Colors {
  bg: string; surface: string; surfaceAlt: string; border: string;
  text: string; textMuted: string; primary: string; primaryText: string;
  primarySoft: string; accent: string; success: string; successSoft: string;
  warning: string; warningSoft: string; danger: string; dangerSoft: string;
  info: string; infoSoft: string; heroFrom: string; heroTo: string; shadow: string;
}

export const colors: Record<ThemeName, Colors> = {
  light: {
    bg: '#F3F6FB', surface: '#FFFFFF', surfaceAlt: '#E8EFF7', border: '#D9E3EE',
    text: '#071D3C', textMuted: '#526981', primary: '#164B85', primaryText: '#FFFFFF',
    primarySoft: '#E1ECF8', accent: '#DDE6F1', success: '#1F805A', successSoft: '#DDF3E9',
    warning: '#976412', warningSoft: '#FFF1D3', danger: '#B73A35', dangerSoft: '#FBE5E4',
    info: '#2263AF', infoSoft: '#DFECFB', heroFrom: '#06172E', heroTo: '#174B85', shadow: '#071D3C',
  },
  dark: {
    bg: '#051327', surface: '#0B2140', surfaceAlt: '#112D53', border: '#244468',
    text: '#F5F8FD', textMuted: '#AEC1D8', primary: '#91BDEB', primaryText: '#06172E',
    primarySoft: '#17385F', accent: '#DDE6F1', success: '#67D3A4', successSoft: '#103E35',
    warning: '#EFC56D', warningSoft: '#433414', danger: '#FF9892', dangerSoft: '#4C2628',
    info: '#99C9FF', infoSoft: '#173557', heroFrom: '#020C1C', heroTo: '#143C71', shadow: '#000000',
  },
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 12, md: 18, lg: 24, pill: 999 };
export const font = {
  title: { fontSize: 27, fontWeight: '800' as const, letterSpacing: -0.5 },
  h2: { fontSize: 19, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '500' as const },
  small: { fontSize: 13, fontWeight: '500' as const },
  label: { fontSize: 12, fontWeight: '700' as const, letterSpacing: 0.6 },
};
/** Accessible minimum touch target, including one-handed use. */
export const TOUCH = 56;
