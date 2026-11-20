import React, { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Button, DemoBanner, FadeIn, Field, PressScale, SectionLabel } from '../../src/components/ui';
import { BrandLockup, Hero } from '../../src/components/Brand';
import { FutureScreen, GlassCard } from '../../src/components/Future';
import { DEMO_ROLE_LOGINS } from '../../src/api/demoApi';
import { useSession } from '../../src/state/session';
import { homeForSession } from '../../src/roles/registry';
import { ApiError } from '../../src/api/types';
import type { AuthMode, StaffApi } from '../../src/api/types';
import { isTrustedHotelOrigin } from '../../src/api/hotels';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

export default function Login() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { hotel, api, signIn } = useSession();
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [modeResult, setModeResult] = useState<{ api: StaffApi; attempt: number; value: AuthMode } | null>(null);
  const [modeError, setModeError] = useState<{ api: StaffApi; attempt: number } | null>(null);
  const [modeRetry, setModeRetry] = useState(0);
  const authMode: AuthMode | null = hotel?.demo ? 'demo' :
    modeResult?.api === api && modeResult?.attempt === modeRetry ? modeResult.value : null;
  const cannotDiscoverMode = modeError?.api === api && modeError?.attempt === modeRetry;

  useEffect(() => {
    if (!hotel || !api || hotel.demo) return;
    let active = true;
    // Mode requests are public. Never send credentials when the mode is
    // unknown, unsupported or unavailable. Async callbacks avoid render loops.
    const check = api.authMode ? api.authMode() : Promise.reject(new Error('Auth mode unavailable'));
    void check.then(value => {
      if (active) setModeResult({ api, attempt: modeRetry, value });
    }).catch(() => {
      if (active) setModeError({ api, attempt: modeRetry });
    });
    return () => { active = false; };
  }, [hotel, api, modeRetry]);

  const go = async (user: string, pass: string) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true); setErr(null);
    try {
      if (!authMode) throw new ApiError('UNKNOWN', 'Unverified hotel authentication mode');
      // Customer login is always bound to its installed single-property origin.
      // A shared-preview server must not silently expose a hotel selector.
      if (authMode === 'shared_auth_preview') throw new ApiError('FORBIDDEN', 'Shared hotel login is unavailable in customer app');
      const me = await signIn(user, pass);
      router.replace(homeForSession(me.role, me.module_permissions, api?.mode ?? 'LIVE', authMode));
    } catch (e) { const code = e instanceof ApiError ? e.code : 'UNKNOWN'; setErr(code === 'UNAUTHORIZED' || code === 'BAD_REQUEST' ? t('login.wrong') : code === 'OFFLINE' ? t('errors.offline') : code === 'PENDING_LOGOUT' ? t('login.logoutPending') : code === 'FORBIDDEN' ? t('errors.forbidden') : t('errors.generic')); } finally { busyRef.current = false; setBusy(false); }
  };

  if (hotel && !hotel.demo && !isTrustedHotelOrigin(hotel.baseUrl)) return <Redirect href="/connect"/>;
  return (
    <FutureScreen>
      <FadeIn style={{ gap: space.sm }}>
        <Hero height={170}>
          <BrandLockup size={56}/>
          <Text style={[font.title,{color:'#FFFFFF',marginTop:14}]}>{t('login.title')}</Text>
        </Hero>
        <Text style={[font.body, { color: c.textMuted }]}>{t('login.hotel')}: {hotel?.name}</Text>
        {hotel?.demo ? <DemoBanner /> : null}
      </FadeIn>
      <GlassCard style={{ gap: space.md }}>
        {authMode === 'shared_auth_preview' ? <Text testID="login-shared-disabled" style={[font.small, { color: c.danger }]}>{t('errors.forbidden')}</Text> : null}
        {authMode === null ? <Button testID="login-mode-retry" label={t('login.checkMode')} variant="secondary" onPress={() => setModeRetry(x => x + 1)} /> : null}
        <Field label={t('login.username')} value={u} onChangeText={setU} autoCapitalize="none" autoCorrect={false} testID="login-username" />
        <Field label={t('login.password')} value={p} onChangeText={setP} secureTextEntry testID="login-password" />
        {err ? <Text testID="login-error" style={[font.small, { color: c.danger }]}>{err}</Text> : null}
        {cannotDiscoverMode && authMode === null ? <Text testID="login-mode-error" style={[font.small, { color: c.danger }]}>{t('login.modeUnavailable')}</Text> : null}
        <Button testID="login-submit" label={t('login.signIn')} onPress={() => go(u, p)} disabled={busy || !authMode || authMode === 'shared_auth_preview' || !u || !p} />
      </GlassCard>
      {hotel?.demo ? (
        <>
          <SectionLabel>{t('login.demoRole')}</SectionLabel>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {DEMO_ROLE_LOGINS.map((d) => (
              <PressScale key={d.username} testID={`demo-${d.username}`} onPress={() => go(d.username, 'demo')} disabled={busy} style={{ paddingHorizontal: 16, minHeight: 48, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: c.primarySoft }}>
                <Text style={[font.small, { color: c.primary, fontWeight: '700' }]}>{t(`roles.${d.role}`)}</Text>
              </PressScale>
            ))}
          </View>
        </>
      ) : null}
    </FutureScreen>
  );
}
