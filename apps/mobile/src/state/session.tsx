import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { getLocales } from 'expo-localization';
import { AppState } from 'react-native';
import { apiFor, dropApi } from '../api/factory';
import { createRealApi } from '../api/realApi';
import { flushPendingCookieLogouts, hasUnrevokedCookieForHost, queueCookieLogout } from '../lib/pendingLogout';
import { DEMO_HOTELS, HotelConnection, hotelConnectionId, isTrustedHotelOrigin, parseHotelAddress } from '../api/hotels';
import { ApiError } from '../api/types';
import { activateClientSession, bindVerifiedHost } from '../api/unauthorizedSession';
import { checkedHotelSelector, matchesSelectedHotel, sameSessionIdentity } from '../api/sharedHotelAuth';
import type { SharedHotelSelector } from '../api/sharedHotelAuth';
import type { AuthMode, AuthUser, StaffApi } from '../api/types';
import { initI18n, Locale, localeFromDevice } from '../i18n';
import { getItem, setItem } from '../lib/storage';

interface SessionCtx {
  hotels: HotelConnection[];
  hotel: HotelConnection | null;
  user: AuthUser | null;
  api: StaffApi | null;
  /** Canonical /api/v1/auth/mode, verified during LIVE login. */
  serverAuthMode: AuthMode | null;
  locale: Locale;
  setLocale: (l: Locale) => void;
  addHotel: (h: HotelConnection) => void;
  selectHotel: (id: string) => void;
  /** Retain verified per-origin in-memory sessions; never reuse shared-host cookies. */
  switchHotel: (id: string) => Promise<boolean>;
  signIn: (username: string, password: string, selector?: SharedHotelSelector) => Promise<AuthUser>;
  /** Isolated synthetic preview: does not touch hotel APIs. */
  startDemo: (username?: string) => Promise<AuthUser>;
  signOut: () => Promise<void>;
  leaveHotel: () => void;
}
const Ctx = createContext<SessionCtx | null>(null);

export function SessionProvider({ children, initialLocale, initialHotelId, initialUser }: { children: React.ReactNode; initialLocale?: Locale; initialHotelId?: string; initialUser?: AuthUser }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const selected = initialLocale ?? localeFromDevice(getLocales()[0]?.languageCode);
    initI18n(selected);
    return selected;
  });
  const [hotels, setHotels] = useState<HotelConnection[]>(DEMO_HOTELS);
  const [hotelId, setHotelId] = useState<string | null>(initialHotelId ?? null);
  // Sessions are keyed by hotel id: signing in to hotel A never exposes data of hotel B.
  const [sessions, setSessions] = useState<Record<string, AuthUser>>(initialHotelId && initialUser ? { [initialHotelId]: initialUser } : {});
  const [serverAuthMode, setServerAuthMode] = useState<AuthMode | null>(null);
  const authModesByHotel = useRef<Record<string, AuthMode>>({});
  const sessionRevision = useRef(0);
  const loginAttempt = useRef(0);
  // One native cookie jar per host: keep all LIVE sign-in cookie writes ordered.
  // Promise tail intentionally remains successful after a rejected attempt.
  const liveSignInTail = useRef<Promise<void>>(Promise.resolve());
  useEffect(() => {
    if (initialLocale) return;
    void getItem('marina.locale').then((v) => { if (v && ['ru', 'kg', 'en', 'kz'].includes(v)) { initI18n(v as Locale); setLocaleState(v as Locale); } });
    void getItem('marina.hotels').then((v) => {
      if (!v) return;
      try {
        const saved: unknown = JSON.parse(v);
        if (!Array.isArray(saved)) return;
        // Saved connections are preferences, not trusted configuration.
        // Re-validate every origin before a network client can be constructed.
        const known = new Set(DEMO_HOTELS.map((h) => h.id));
        const hosts = new Set<string>();
        const extra: HotelConnection[] = [];
        for (const item of saved.slice(0, 50)) {
          if (!item || typeof item !== 'object') continue;
          const h = item as Partial<HotelConnection>;
          if (h.demo !== false || typeof h.baseUrl !== 'string') continue;
          const parsed = parseHotelAddress(h.baseUrl);
          if (!parsed.ok || !isTrustedHotelOrigin(parsed.baseUrl)) continue;
          const id = hotelConnectionId(parsed.baseUrl);
          const host = new URL(parsed.baseUrl).hostname;
          if (known.has(id) || hosts.has(host) || extra.length >= 20) continue;
          hosts.add(host);
          known.add(id);
          extra.push({ id, baseUrl: parsed.baseUrl, name: id.slice(5), city: '', demo: false, accent: '#245E9A' });
        }
        // Legacy devices could have saved multiple unrelated hotel origins.
        // Never silently pick one: clear ambiguous preferences and require
        // an explicit, trusted single-property setup again.
        if (extra.length > 1) {
          setHotels(DEMO_HOTELS);
          void setItem('marina.hotels', '[]');
          return;
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
        if (!verified || !sameSessionIdentity(user, verified)) {
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
  }, [hotel, api, user]);

  // Retry an unfinished logout on startup / foreground; no user data is
  // exposed while the OS cookie may still exist. A signed app trust anchor
  // must approve the target origin before any automatic request.
  useEffect(() => {
    const tryRevoke = () => {
      void flushPendingCookieLogouts(async origin => createRealApi(origin).logout());
    };
    tryRevoke();
    const sub = AppState.addEventListener('change', state => {
      if (state === 'active') tryRevoke();
    });
    return () => sub.remove();
  }, []);

  const setLocale = useCallback((l: Locale) => { initI18n(l); setLocaleState(l); void setItem('marina.locale', l); }, []);
  const selectHotel = useCallback((id: string | null) => {
    // A hotel switch is a security boundary: do not reuse an earlier user
    // session merely because the device previously opened that property.
    if (id === hotelId) return;
    const candidate = hotels.find(h => h.id === id);
    // A provisioned customer app cannot enter the synthetic showroom even
    // through a deep link or a future caller bypassing the connection screen.
    if (candidate?.demo && hotels.some(h => !h.demo)) return;
    if (candidate && !candidate.demo && !isTrustedHotelOrigin(candidate.baseUrl)) return;
    const leaving = hotelId ? hotels.find(h => h.id === hotelId) : null;
    sessionRevision.current++;
    loginAttempt.current++;
    if (hotelId) dropApi(hotelId);
    // Switching hotel is a local security boundary even when remote logout
    // is offline. Do not expose the old staff identity during any network I/O.
    setSessions({});
    setServerAuthMode(null);
    setHotelId(id);
    if (leaving && !leaving.demo && isTrustedHotelOrigin(leaving.baseUrl)) {
      const origin = leaving.baseUrl;
      const revoke = async () => {
        let queued = false;
        try { await queueCookieLogout(origin); queued = true; }
        catch { /* keep the UI signed out even if secure storage is unavailable */ }
        if (queued) {
          await flushPendingCookieLogouts(async url => createRealApi(url).logout());
        } else {
          // No durable retry guarantee if journal writing failed, but do not
          // leave a live cookie unchallenged when the trusted host is reachable.
          try { await createRealApi(origin).logout(); }
          catch { /* the next sign-in must still clear the host cookie */ }
        }
      };
      // A pending login can still install Set-Cookie after the hotel changed.
      // Serialize its completion BEFORE revoking the old hotel session; the
      // next selected hotel's sign-in waits for this same revocation tail.
      const previous = liveSignInTail.current;
      const current = previous.then(revoke, revoke);
      liveSignInTail.current = current.then(() => undefined, () => undefined);
    }
  }, [hotelId, hotels]);
  const switchHotel = useCallback(async (id: string): Promise<boolean> => {
    // Customer builds are single-property: never restore another hotel's login.
    if (hotelId && id !== hotelId) {
      throw new ApiError('FORBIDDEN', 'Hotel switching is not available in a customer session');
    }
    const target = hotels.find(h => h.id === id);
    if (target?.demo && hotels.some(h => !h.demo)) {
      throw new ApiError('FORBIDDEN', 'DEMO is unavailable on a provisioned customer device');
    }
    if (!target || (!target.demo && !isTrustedHotelOrigin(target.baseUrl))) {
      throw new ApiError('FORBIDDEN', 'Hotel origin is not approved in this app build');
    }
    if (id === hotelId) return !!sessions[id];
    const previous = hotelId ? hotels.find(h => h.id === hotelId) : null;
    // Native HttpOnly cookies are scoped to HOST, not to tenant/property code.
    // Two connections sharing a hostname can NEVER retain separate LIVE users.
    if (previous && !previous.demo && !target.demo &&
        new URL(previous.baseUrl).hostname === new URL(target.baseUrl).hostname) {
      selectHotel(id); // existing fail-closed logout/host revocation boundary
      return false;
    }
    const revision = ++sessionRevision.current;
    loginAttempt.current++;
    let remembered: AuthUser | null = sessions[id] ?? null;
    if (remembered && !target.demo) {
      try {
        // Revalidate before revealing any cached LIVE identity or hotel data.
        // A disconnected or revoked session requires login, not a stale preview.
        const actual = await apiFor(target).me();
        if (!sameSessionIdentity(remembered, actual)) throw new ApiError('UNAUTHORIZED');
        remembered = actual;
      } catch {
        remembered = null;
        dropApi(id);
        setSessions(current => { const next = { ...current }; delete next[id]; return next; });
        delete authModesByHotel.current[id];
      }
    }
    if (revision !== sessionRevision.current) throw new ApiError('STALE_SESSION');
    if (remembered && !target.demo) activateClientSession(apiFor(target));
    if (remembered) {
      const verified = remembered;
      setSessions(current => ({ ...current, [id]: verified }));
    }
    setServerAuthMode(remembered ? authModesByHotel.current[id] ?? null : null);
    setHotelId(id);
    return !!remembered;
  }, [hotelId, hotels, sessions, selectHotel]);

  const addHotel = useCallback((h: HotelConnection) => {
    if (h.demo || !isTrustedHotelOrigin(h.baseUrl)) {
      throw new ApiError('FORBIDDEN', 'Hotel origin is not approved in this app build');
    }
    // A customer device may be provisioned for ONE trusted hotel. Changing it
    // requires a dedicated administrator-controlled reset, not another login.
    const existing = hotels.find(item => !item.demo);
    if (existing && existing.id !== h.id) {
      const sameHost = new URL(existing.baseUrl).hostname === new URL(h.baseUrl).hostname;
      // /api/v1 -> /core on the SAME approved host is a technical URL
      // migration, not onboarding a second customer. Never swap an active user.
      if (!sameHost || sessions[existing.id]) {
        throw new ApiError('FORBIDDEN', 'Device is already bound to a hotel');
      }
      dropApi(existing.id);
    }
    setHotels([...DEMO_HOTELS, h]);
    void setItem('marina.hotels', JSON.stringify([h]));
    if (hotelId !== h.id) selectHotel(h.id);
  }, [hotels, hotelId, selectHotel, sessions]);
  const startDemo = useCallback(async (username = 'manager'): Promise<AuthUser> => {
    const demoHotel = DEMO_HOTELS[0];
    // Never bypass production auth. This method explicitly uses the isolated
    // in-memory demo API, which does not make network calls.
    // The LIVE device remains bound to its customer hotel even when signed out.
    if (hotels.some(h => !h.demo)) {
      throw new ApiError('FORBIDDEN', 'DEMO is unavailable on a provisioned customer device');
    }
    const revision = ++sessionRevision.current;
    loginAttempt.current++;
    if (hotelId) dropApi(hotelId);
    dropApi(demoHotel.id);
    setSessions({});
    setServerAuthMode(null);
    setHotelId(demoHotel.id);
    try {
      const demoApi = apiFor(demoHotel);
      const demoUser = await demoApi.login(username, 'demo');
      if (sessionRevision.current !== revision) throw new ApiError('UNAUTHORIZED', 'Demo selection changed');
      setSessions({ [demoHotel.id]: demoUser });
      return demoUser;
    } catch (error) {
      if (sessionRevision.current === revision) {
        setSessions({});
        setHotelId(null);
      }
      throw error;
    }
  }, [hotelId]);

  const signIn = useCallback((username: string, password: string, selector?: SharedHotelSelector): Promise<AuthUser> => {
    if (!hotel || !api) return Promise.reject(new Error('no hotel'));
    if (!hotel.demo && !isTrustedHotelOrigin(hotel.baseUrl)) {
      return Promise.reject(new ApiError('FORBIDDEN', 'Untrusted hotel address'));
    }
    // Invalidate the prior identity as soon as the user requests a new login,
    // not after waiting for an earlier native-cookie mutation to finish.
    const revision = ++sessionRevision.current;
    const attempt = ++loginAttempt.current;
    setSessions(current => { const next = { ...current }; delete next[hotel.id]; return next; });
    setServerAuthMode(null);

    if (!hotel.demo) dropApi(hotel.id);
    const loginApi = hotel.demo ? api : apiFor(hotel);

    const perform = async (): Promise<AuthUser> => {
      // A hotel switch or later login can supersede this queued request.
      // Never send stale credentials or mutate cookies for that request.
      if (sessionRevision.current !== revision || loginAttempt.current !== attempt) {
        throw new ApiError('UNAUTHORIZED', 'Session context changed before login');
      }
      let selected: SharedHotelSelector | undefined;
      let chosenMode: AuthMode | null = null;
    if (!hotel.demo) {
      // This canonical endpoint distinguishes shared tenant login from legacy
      // one-property login without guessing from a hostname or user input.
      if (!loginApi.authMode) throw new ApiError('UNKNOWN', 'Server authentication mode unavailable');
      const mode = await loginApi.authMode();
      chosenMode = mode;
      if (mode === 'shared_auth_preview') {
        if (!selector) throw new ApiError('BAD_REQUEST', 'Organization and hotel codes are required');
        selected = checkedHotelSelector(selector);
      } else if (mode === 'single_property') {
        if (selector) throw new ApiError('BAD_REQUEST', 'This hotel does not accept shared selectors');
      } else {
        throw new ApiError('UNKNOWN', 'Unverified authentication mode');
      }
      // A cookie from a previous offline sign-out could still be active.
      // Revoke it before sending fresh credentials to the same host.
      await flushPendingCookieLogouts(async origin => createRealApi(origin).logout());
      if (await hasUnrevokedCookieForHost(hotel.baseUrl)) {
        throw new ApiError('PENDING_LOGOUT', 'Previous server logout is still pending');
      }
      // An OS cookie can outlive a locally cleared or lost logout queue.
      // Explicitly revoke any stale cookie before sending NEW credentials.
      // The existing /auth/logout returns 204 even for an anonymous request.
      // Fail closed if the server cannot confirm this step.
      try {
        await loginApi.logout();
      } catch {
        throw new ApiError('PENDING_LOGOUT', 'Unable to clear previous hotel session');
      }
    }
    // Switching hotel or signing out while a pending logout is reconciled
    // must invalidate this in-flight login BEFORE submitting credentials.
    if (sessionRevision.current !== revision || loginAttempt.current !== attempt) throw new ApiError('UNAUTHORIZED', 'Session context changed');
    // A login response can set the OS cookie before /me fails. Treat every
    // unverified LIVE result as potentially authenticated and queue revocation.
    let loginStarted = false;
    try {
      loginStarted = true;
      const signedIn = await loginApi.login(username, password, selected);
      const verified = loginApi.mode === 'LIVE' ? await loginApi.me() : signedIn;
      if (!verified || !sameSessionIdentity(signedIn, verified) ||
          (selected && !matchesSelectedHotel(signedIn, verified, selected))) {
        throw new ApiError('UNAUTHORIZED', 'Session or selected hotel identity changed during login');
      }
      if (sessionRevision.current !== revision || loginAttempt.current !== attempt) {
        throw new ApiError('UNAUTHORIZED', 'Session context changed during login');
      }
      activateClientSession(loginApi);
      if (chosenMode) authModesByHotel.current[hotel.id] = chosenMode;
      setServerAuthMode(chosenMode);
      setSessions(current => ({ ...current, [hotel.id]: verified }));
      return verified;
    } catch (error) {
      if (loginStarted && !hotel.demo && isTrustedHotelOrigin(hotel.baseUrl)) {
        // The server may have issued a cookie even after a lost response.
        // Do not reuse it on a later attempt without confirmed revocation.
        await queueCookieLogout(hotel.baseUrl).catch(() => {});
        void flushPendingCookieLogouts(async origin => createRealApi(origin).logout());
      }
      throw error;
    }
    };
    // A single native cookie jar is shared by unrelated properties on one
    // API host. Complete logout/login/me/failed-login cleanup for one attempt
    // before permitting the next LIVE attempt to touch the same cookie.
    // Keep DEMO concurrent behavior unchanged (in-memory, no OS cookie).
    if (hotel.demo) return perform();
    const previous = liveSignInTail.current;
    const current = previous.then(perform, perform);
    liveSignInTail.current = current.then(() => undefined, () => undefined);
    return current;
  }, [hotel, api]);
  const signOut = useCallback(async () => {
    if (!hotel || !api) return;
    sessionRevision.current++;
    loginAttempt.current++;
    // A logout request invalidates visible identity synchronously. Never wait
    // for encrypted storage or a network call to remove the previous hotel.
    dropApi(hotel.id);
    setServerAuthMode(null);
    delete authModesByHotel.current[hotel.id];
    setSessions((s) => { const n = { ...s }; delete n[hotel.id]; return n; });

    if (hotel.demo) {
      try { await api.logout(); } catch { /* isolated demo only */ }
      return;
    }

    const origin = hotel.baseUrl;
    const revoke = async () => {
      // An in-flight /auth/login may still install a native HttpOnly cookie.
      // Wait for that request to settle BEFORE issuing the final logout;
      // otherwise a late login response could recreate a supposedly
      // revoked cross-property cookie after sign-out.
      let queued = false;
      try { await queueCookieLogout(origin); queued = true; }
      catch { /* no durable guarantee, but local identity is already gone */ }
      if (queued) {
        // Keep the journal entry if the server did not acknowledge revocation.
        await flushPendingCookieLogouts(async url => createRealApi(url).logout());
      } else if (isTrustedHotelOrigin(origin)) {
        // Best-effort remote cleanup when durable queueing is unavailable.
        try { await api.logout(); } catch { /* do not restore stale identity */ }
      }
    };
    // One cookie jar per native host: serialize both sign-ins AND sign-outs.
    // Later sign-ins must not overtake an earlier requested logout.
    const previous = liveSignInTail.current;
    const current = previous.then(revoke, revoke);
    liveSignInTail.current = current.then(() => undefined, () => undefined);
    await current;
  }, [hotel, api]);

  // Protected-data 401 invalidates ONLY the verified session whose request
  // began under this binding. Old A responses cannot sign out newly logged B.
  useEffect(() => {
    if (!hotel || !user || api?.mode !== 'LIVE' || !isTrustedHotelOrigin(hotel.baseUrl)) return;
    const revision = sessionRevision.current;
    return bindVerifiedHost(hotel.baseUrl, () => {
      if (sessionRevision.current !== revision) return;
      void signOut(); // clear locally now; serialize durable server revocation
    });
  }, [hotel, api, user, signOut]);

  const value = useMemo<SessionCtx>(() => ({
    hotels, hotel, user, api, serverAuthMode, locale, setLocale, addHotel, selectHotel, switchHotel, signIn, startDemo, signOut, leaveHotel: () => selectHotel(null),
  }), [hotels, hotel, user, api, serverAuthMode, locale, setLocale, addHotel, selectHotel, switchHotel, signIn, startDemo, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): SessionCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('SessionProvider missing');
  return v;
}
