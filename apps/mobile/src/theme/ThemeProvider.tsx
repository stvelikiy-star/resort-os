import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useColorScheme } from 'react-native';
import { colors, Colors, ThemeName } from './tokens';
import { getItem, setItem } from '../lib/storage';

export type ThemePref = 'system' | ThemeName;
interface Ctx { name: ThemeName; c: Colors; pref: ThemePref; setPref: (p: ThemePref) => void }
const ThemeCtx = createContext<Ctx | null>(null);
const KEY = 'marina.theme';
export function validTheme(value: unknown): value is ThemePref {
  return value === 'system' || value === 'light' || value === 'dark';
}
export function ThemeProvider({ children, initial = 'system' }: { children: React.ReactNode; initial?: ThemePref }) {
  const system = useColorScheme();
  const [pref, setPreference] = useState<ThemePref>(initial);
  const [changed, setChanged] = useState(false);
  useEffect(() => {
    if (initial !== 'system') return;
    let active = true;
    void getItem(KEY).then((value) => {
      if (active && !changed && validTheme(value)) setPreference(value);
    }).catch(() => {});
    return () => { active = false; };
  }, [initial, changed]);
  const setPref = useCallback((next: ThemePref) => {
    setChanged(true);
    setPreference(next);
    void setItem(KEY, next);
  }, []);
  const name: ThemeName = pref === 'system' ? (system === 'dark' ? 'dark' : 'light') : pref;
  const value = useMemo(() => ({ name, c: colors[name], pref, setPref }), [name, pref, setPref]);
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}
export function useTheme(): Ctx {
  const v = useContext(ThemeCtx);
  if (!v) throw new Error('ThemeProvider missing');
  return v;
}
