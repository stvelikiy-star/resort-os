export type ThemeName = 'light' | 'dark';

export const palette = {
  teal: '#0A9996',
  tealDeep: '#0B5F66',
  navy: '#0F2F3A',
  sand: '#E9B872',
  coral: '#E5654F',
  green: '#2FA36B',
  amber: '#E0A21B',
  blue: '#3D7BD9',
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
    bg: '#F3F7F8', surface: '#FFFFFF', surfaceAlt: '#E8F0F2', border: '#D9E4E7',
    text: '#0F2F3A', textMuted: '#5B7480', primary: palette.teal, primaryText: '#FFFFFF',
    primarySoft: '#DDF3F2', accent: palette.sand, success: '#1F8A58', successSoft: '#DFF4E9',
    warning: '#9A6A00', warningSoft: '#FBF0D2', danger: '#C8442F', dangerSoft: '#FBE4DF',
    info: '#2F66BE', infoSoft: '#E1ECFB', heroFrom: palette.tealDeep, heroTo: palette.teal, shadow: '#0F2F3A',
  },
  dark: {
    bg: '#0A1A20', surface: '#12262E', surfaceAlt: '#1A3540', border: '#24424E',
    text: '#EAF4F6', textMuted: '#8FAAB5', primary: '#2BC4BF', primaryText: '#062226',
    primarySoft: '#10393D', accent: palette.sand, success: '#4CCB8D', successSoft: '#12372A',
    warning: '#F0BF52', warningSoft: '#3A2F10', danger: '#FF8A74', dangerSoft: '#42201A',
    info: '#7CAEF2', infoSoft: '#172F52', heroFrom: '#0B3F46', heroTo: '#0A7F7D', shadow: '#000000',
  },
};

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 10, md: 16, lg: 22, pill: 999 };
export const font = {
  title: { fontSize: 26, fontWeight: '800' as const, letterSpacing: -0.4 },
  h2: { fontSize: 19, fontWeight: '700' as const },
  body: { fontSize: 16, fontWeight: '500' as const },
  small: { fontSize: 13, fontWeight: '500' as const },
  label: { fontSize: 12, fontWeight: '700' as const, letterSpacing: 0.6 },
};
/** Minimum touch target for gloved/one-hand use. */
export const TOUCH = 56;
