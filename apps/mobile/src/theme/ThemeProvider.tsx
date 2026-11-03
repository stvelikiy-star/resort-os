import React, { createContext, useContext, useMemo, useState } from 'react';
import { useColorScheme } from 'react-native';
import { colors, Colors, ThemeName } from './tokens';

export type ThemePref = 'system' | ThemeName;
interface Ctx { name: ThemeName; c: Colors; pref: ThemePref; setPref: (p: ThemePref) => void }
const ThemeCtx = createContext<Ctx | null>(null);

export function ThemeProvider({ children, initial = 'system' }: { children: React.ReactNode; initial?: ThemePref }) {
  const system = useColorScheme();
  const [pref, setPref] = useState<ThemePref>(initial);
  const name: ThemeName = pref === 'system' ? (system === 'dark' ? 'dark' : 'light') : pref;
  const value = useMemo(() => ({ name, c: colors[name], pref, setPref }), [name, pref]);
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme(): Ctx {
  const v = useContext(ThemeCtx);
  if (!v) throw new Error('ThemeProvider missing');
  return v;
}
