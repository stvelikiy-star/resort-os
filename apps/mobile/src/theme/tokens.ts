export type ThemeName = 'light' | 'dark';

/** MARINA SMART premium mobile system: midnight ink, champagne gold, restrained sea-glass accents. */
export const palette = {
  teal: '#087F86',
  tealDeep: '#07555C',
  navy: '#101D30',
  sand: '#D4AE70',
  coral: '#CB685E',
  green: '#2D9977',
  amber: '#CA9445',
  blue: '#4D7FAB',
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
    bg: '#F5F5F2', surface: '#FFFFFF', surfaceAlt: '#EDF1F1', border: '#E1E7E6',
    text: '#142337', textMuted: '#667788', primary: '#087F86', primaryText: '#FFFFFF',
    primarySoft: '#E4F2F1', accent: '#B88A45', success: '#227B61', successSoft: '#E2F3EA',
    warning: '#9B6C27', warningSoft: '#FCF1DD', danger: '#B9453F', dangerSoft: '#FCE9E6',
    info: '#3569A2', infoSoft: '#EAF1FA', heroFrom: '#101D30', heroTo: '#17525D', shadow: '#122439',
  },
  dark: {
    bg: '#0A1423', surface: '#132238', surfaceAlt: '#1C3046', border: '#294054',
    text: '#F5F5F0', textMuted: '#A5B5C2', primary: '#69D7CF', primaryText: '#071923',
    primarySoft: '#173E45', accent: '#E5BF7B', success: '#61CEA5', successSoft: '#183C34',
    warning: '#F0C276', warningSoft: '#473820', danger: '#FF938C', dangerSoft: '#482B2D',
    info: '#98C0F4', infoSoft: '#213C5D', heroFrom: '#172C46', heroTo: '#0B535A', shadow: '#000000',
  },
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 12, md: 18, lg: 24, pill: 999 };
export const font = {
  title: { fontSize: 28, fontWeight: '800' as const, letterSpacing: -0.7 },
  h2: { fontSize: 19, fontWeight: '700' as const, letterSpacing: -0.35 },
  body: { fontSize: 16, fontWeight: '500' as const },
  small: { fontSize: 13, fontWeight: '500' as const },
  label: { fontSize: 11, fontWeight: '800' as const, letterSpacing: 1.1 },
};
/** Comfortable touch target, including one-handed operational use. */
export const TOUCH = 56;
