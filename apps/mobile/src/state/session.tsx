import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getLocales } from 'expo-localization';
import { apiFor, dropApi } from '../api/factory';
import { DEMO_HOTELS, HotelConnection } from '../api/hotels';
import type { AuthUser, StaffApi } from '../api/types';
import { initI18n, Locale, localeFromDevice } from '../i18n';
import { getItem, setItem } from '../lib/storage';

interface SessionCtx {
  hotels: HotelConnection[];
  hotel: HotelConnection | null;
  user: AuthUser | null;
  api: StaffApi | null;
  locale: Locale;
  setLocale: (l: Locale) => void;
  addHotel: (h: HotelConnection) => void;
  selectHotel: (id: string) => void;
  signIn: (username: string, password: string) => Promise<AuthUser>;
  signOut: () => Promise<void>;
  leaveHotel: () => void;
}
const Ctx = createContext<SessionCtx | null>(null);

export function SessionProvider({ children, initialLocale, initialHotelId, initialUser }: { children: React.ReactNode; initialLocale?: Locale; initialHotelId?: string; initialUser?: AuthUser }) {
  const [locale, setLocaleState] = useState<Locale>(initialLocale ?? localeFromDevice(getLocales()[0]?.languageCode));
  const [hotels, setHotels] = useState<HotelConnection[]>(DEMO_HOTELS);
  const [hotelId, setHotelId] = useState<string | null>(initialHotelId ?? null);
  // Sessions are keyed by hotel id: signing in to hotel A never exposes data of hotel B.
  const [sessions, setSessions] = useState<Record<string, AuthUser>>(initialHotelId && initialUser ? { [initialHotelId]: initialUser } : {});
  initI18n(locale);

  useEffect(() => {
    if (initialLocale) return;
    void getItem('marina.locale').then((v) => { if (v && ['ru', 'kg', 'en', 'kz'].includes(v)) setLocaleState(v as Locale); });
    void getItem('marina.hotels').then((v) => {
      if (!v) return;
      try { const extra = (JSON.parse(v) as HotelConnection[]).filter((h) => !h.demo && h.baseUrl.startsWith('https://')); setHotels([...DEMO_HOTELS, ...extra]); } catch { /* ignore corrupt */ }
    });
  }, [initialLocale]);

  const hotel = hotels.find((h) => h.id === hotelId) ?? null;
  const user = hotel ? sessions[hotel.id] ?? null : null;
  const api = hotel ? apiFor(hotel) : null;

  const setLocale = useCallback((l: Locale) => { setLocaleState(l); void setItem('marina.locale', l); }, []);
  const addHotel = useCallback((h: HotelConnection) => {
    setHotels((cur) => {
      const next = cur.some((x) => x.id === h.id) ? cur : [...cur, h];
      void setItem('marina.hotels', JSON.stringify(next.filter((x) => !x.demo)));
      return next;
    });
    setHotelId(h.id);
  }, []);
  const signIn = useCallback(async (username: string, password: string) => {
    if (!hotel || !api) throw new Error('no hotel');
    const u = await api.login(username, password);
    setSessions((s) => ({ ...s, [hotel.id]: u }));
    return u;
  }, [hotel, api]);
  const signOut = useCallback(async () => {
    if (!hotel || !api) return;
    try { await api.logout(); } finally {
      dropApi(hotel.id);
      setSessions((s) => { const n = { ...s }; delete n[hotel.id]; return n; });
    }
  }, [hotel, api]);

  const value = useMemo<SessionCtx>(() => ({
    hotels, hotel, user, api, locale, setLocale, addHotel, selectHotel: setHotelId, signIn, signOut, leaveHotel: () => setHotelId(null),
  }), [hotels, hotel, user, api, locale, setLocale, addHotel, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('SessionProvider missing');
  return v;
}
