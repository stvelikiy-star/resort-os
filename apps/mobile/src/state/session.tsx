import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { getLocales } from 'expo-localization';
import { AppState } from 'react-native';
import { apiFor, dropApi } from '../api/factory';
import { DEMO_HOTELS, HotelConnection, hotelConnectionId, parseHotelAddress } from '../api/hotels';
import { ApiError } from '../api/types';
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
  const sessionRevision = useRef(0);
  initI18n(locale);

  useEffect(() => {
    if (initialLocale) return;
    void getItem('marina.locale').then((v) => { if (v && ['ru', 'kg', 'en', 'kz'].includes(v)) setLocaleState(v as Locale); });
    void getItem('marina.hotels').then((v) => {
      if (!v) return;
      try {
        const saved: unknown = JSON.parse(v);
        if (!Array.isArray(saved)) return;
        // Saved connections are preferences, not trusted configuration.
        // Re-validate every origin before a network client can be constructed.
        const known = new Set(DEMO_HOTELS.map((h) => h.id));
        const extra: HotelConnection[] = [];
        for (const item of saved.slice(0, 50)) {
          if (!item || typeof item !== 'object') continue;
          const h = item as Partial<HotelConnection>;
          if (h.demo !== false || typeof h.baseUrl !== 'string') continue;
          const parsed = parseHotelAddress(h.baseUrl);
          if (!parsed.ok) continue;
          const id = hotelConnectionId(parsed.baseUrl);
          if (known.has(id) || extra.length >= 20) continue;
          known.add(id);
          extra.push({ id, baseUrl: parsed.baseUrl, name: id.slice(5), city: '', demo: false, accent: '#245E9A' });
        }
        setHotels([...DEMO_HOTELS, ...extra]);
      } catch { /* ignore corrupt preferences */ }
    });
  }, [initialLocale]);

  const hotel = hotels.find((h) => h.id === hotelId) ?? null;
  const user = hotel ? sessions[hotel.id] ?? null : null;
  const api = hotel ? apiFor(hotel) : null;

  useEffect(() => {
    if (!hotel || !api || !user || api.mode !== 'LIVE') return;
    const revision = sessionRevision.current;
    let checking = false;
    const verifySession = async () => {
      if (checking) return;
      checking = true;
      try {
        const verified = await api.me();
        if (sessionRevision.current !== revision) return;
        if (!verified || verified.id !== user.id || verified.property_code !== user.property_code) {
          sessionRevision.current++;
          dropApi(hotel.id);
          setSessions((current) => { const next = { ...current }; delete next[hotel.id]; return next; });
          return;
        }
        // Permission or role changes on the PMS become visible when the app resumes.
        setSessions((current) => current[hotel.id]
          ? { ...current, [hotel.id]: verified }
          : current);
      } catch (e) {
        if (sessionRevision.current !== revision) return;
        if (e instanceof ApiError && (e.code === 'UNAUTHORIZED' || e.code === 'FORBIDDEN')) {
          sessionRevision.current++;
          dropApi(hotel.id);
          setSessions((current) => { const next = { ...current }; delete next[hotel.id]; return next; });
        }
        // Do not mistake a temporary network outage for an explicit revocation.
      } finally {
        checking = false;
      }
    };
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') void verifySession();
    });
    return () => sub.remove();
  }, [hotel, api, user?.id, user?.property_code]);

  const setLocale = useCallback((l: Locale) => { setLocaleState(l); void setItem('marina.locale', l); }, []);
  const selectHotel = useCallback((id: string | null) => {
    // A hotel switch is a security boundary: do not reuse an earlier user
    // session merely because the device previously opened that property.
    if (id === hotelId) return;
    sessionRevision.current++;
    if (hotelId) dropApi(hotelId);
    setSessions({});
    setHotelId(id);
  }, [hotelId]);
  const addHotel = useCallback((h: HotelConnection) => {
    setHotels((cur) => {
      const next = cur.some((x) => x.id === h.id) ? cur : [...cur, h];
      void setItem('marina.hotels', JSON.stringify(next.filter((x) => !x.demo)));
      return next;
    });
    selectHotel(h.id);
  }, [selectHotel]);
  const signIn = useCallback(async (username: string, password: string) => {
    if (!hotel || !api) throw new Error('no hotel');
    const revision = sessionRevision.current;
    const signedIn = await api.login(username, password);
    // A native cookie may not persist after a successful login response.
    // Confirm that subsequent authenticated requests resolve to the SAME user.
    const verified = api.mode === 'LIVE' ? await api.me() : signedIn;
    if (!verified || typeof verified.id !== 'string' || !verified.id ||
        typeof verified.property_code !== 'string' || !verified.property_code ||
        typeof verified.role !== 'string' || !verified.role ||
        verified.id !== signedIn.id || verified.property_code !== signedIn.property_code) {
      throw new ApiError('UNAUTHORIZED', 'Session or hotel identity changed during login');
    }
    if (sessionRevision.current !== revision) throw new ApiError('UNAUTHORIZED', 'Hotel changed during login');
    setSessions((s) => ({ ...s, [hotel.id]: verified }));
    return verified;
  }, [hotel, api]);
  const signOut = useCallback(async () => {
    if (!hotel || !api) return;
    sessionRevision.current++;
    try {
      await api.logout();
    } catch {
      // A failed network logout must not leave employee data visible locally.
      // The server session may remain valid until it expires/revocation.
    } finally {
      dropApi(hotel.id);
      setSessions((s) => { const n = { ...s }; delete n[hotel.id]; return n; });
    }
  }, [hotel, api]);

  const value = useMemo<SessionCtx>(() => ({
    hotels, hotel, user, api, locale, setLocale, addHotel, selectHotel, signIn, signOut, leaveHotel: () => selectHotel(null),
  }), [hotels, hotel, user, api, locale, setLocale, addHotel, selectHotel, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('SessionProvider missing');
  return v;
}
