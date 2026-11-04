import React, { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { Button, DemoBanner, FadeIn, Field, PressScale, SectionLabel } from '../../src/components/ui';
import { Hero, Logo, Wordmark } from '../../src/components/Brand';
import { FutureScreen, GlassCard } from '../../src/components/Future';
import { DEMO_ROLE_LOGINS } from '../../src/api/demoApi';
import { useSession } from '../../src/state/session';
import { homeForSession } from '../../src/roles/registry';
import { ApiError } from '../../src/api/types';
import type { AuthMode } from '../../src/api/types';
import { checkedHotelSelector } from '../../src/api/sharedHotelAuth';
import { isTrustedHotelOrigin } from '../../src/api/hotels';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

export default function Login() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { hotel, api, signIn, leaveHotel } = useSession();
  const [u, setU] = useState('');
  const [p, setP] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [authMode, setAuthMode] = useState<AuthMode | null>(null);
  const [modeRetry, setModeRetry] = useState(0);
  const [tenantCode, setTenantCode] = useState('');
  const [propertyCode, setPropertyCode] = useState('');

  useEffect(() => {
    let active = true;
    setErr(null);
    setAuthMode(null);
    if (!hotel || !api) return;
    if (hotel.demo) { setAuthMode('demo'); return; }
    void api.authMode().then(mode => {
      if (active) setAuthMode(mode);
    }).catch(() => {
      if (active) setErr(t('login.modeUnavailable'));
    });
    return () => { active = false; };
  }, [hotel?.id, api, modeRetry]);

  const go = async (user: string, pass: string) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true); setErr(null);
    try {
      if (!authMode) throw new ApiError('UNKNOWN', 'Unverified hotel authentication mode');
      const selector = authMode === 'shared_auth_preview' ? checkedHotelSelector({
        tenant_code: tenantCode.trim(), property_code: propertyCode.trim(),
      }) : undefined;
      const me = await signIn(user, pass, selector);
      router.replace(homeForSession(me.role, me.module_permissions, api?.mode ?? 'LIVE'));
    } catch (e) { const code = e instanceof ApiError ? e.code : 'UNKNOWN'; setErr(code === 'UNAUTHORIZED' || code === 'BAD_REQUEST' ? t('login.wrong') : code === 'OFFLINE' ? t('errors.offline') : code === 'PENDING_LOGOUT' ? t('login.logoutPending') : code === 'FORBIDDEN' ? t('errors.forbidden') : t('errors.generic')); } finally { busyRef.current = false; setBusy(false); }
  };

  if (hotel && !hotel.demo && !isTrustedHotelOrigin(hotel.baseUrl)) return <Redirect href="/connect"/>;
  return (
    <FutureScreen>
      <PressScale onPress={() => { leaveHotel(); router.replace('/connect'); }} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} accessibilityLabel={t('login.change')}>
        <ChevronLeft size={22} color={c.primary} /><Text style={[font.body, { color: c.primary }]}>{t('login.change')}</Text>
      </PressScale>
      <FadeIn style={{ gap: space.sm }}>
        <Hero height={170}>
          <View style={{ flexDirection:'row',alignItems:'center',gap:12 }}><Logo size={56}/><Wordmark color="#FFFFFF"/></View>
          <Text style={[font.title,{color:'#FFFFFF',marginTop:14}]}>{t('login.title')}</Text>
        </Hero>
        <Text style={[font.body, { color: c.textMuted }]}>{t('login.hotel')}: {hotel?.name}</Text>
        {hotel?.demo ? <DemoBanner /> : null}
      </FadeIn>
      <GlassCard style={{ gap: space.md }}>
        {authMode === 'shared_auth_preview' ? <>
          <Text style={[font.small, { color: c.textMuted }]}>{t('login.sharedHint')}</Text>
          <Field label={t('login.tenantCode')} value={tenantCode} onChangeText={setTenantCode} autoCapitalize="none" autoCorrect={false} testID="login-tenant-code" />
          <Field label={t('login.propertyCode')} value={propertyCode} onChangeText={setPropertyCode} autoCapitalize="none" autoCorrect={false} testID="login-property-code" />
        </> : null}
        {authMode === null ? <Button testID="login-mode-retry" label={t('login.checkMode')} variant="secondary" onPress={() => setModeRetry(x => x + 1)} /> : null}
        <Field label={t('login.username')} value={u} onChangeText={setU} autoCapitalize="none" autoCorrect={false} testID="login-username" />
        <Field label={t('login.password')} value={p} onChangeText={setP} secureTextEntry testID="login-password" />
        {err ? <Text testID="login-error" style={[font.small, { color: c.danger }]}>{err}</Text> : null}
        <Button testID="login-submit" label={t('login.signIn')} onPress={() => go(u, p)} disabled={busy || !authMode || !u || !p || (authMode === 'shared_auth_preview' && (!tenantCode.trim() || !propertyCode.trim()))} />
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
