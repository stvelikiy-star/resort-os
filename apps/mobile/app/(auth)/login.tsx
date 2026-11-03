import React, { useRef, useState } from 'react';
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

  const go = async (user: string, pass: string) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true); setErr(null);
    try { const me = await signIn(user, pass); router.replace(homeForSession(me.role, me.module_permissions, api?.mode ?? 'LIVE')); } catch (e) { const code = e instanceof ApiError ? e.code : 'UNKNOWN'; setErr(code === 'UNAUTHORIZED' || code === 'BAD_REQUEST' ? t('login.wrong') : code === 'OFFLINE' ? t('errors.offline') : code === 'FORBIDDEN' ? t('errors.forbidden') : t('errors.generic')); } finally { busyRef.current = false; setBusy(false); }
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
        <Field label={t('login.username')} value={u} onChangeText={setU} autoCapitalize="none" autoCorrect={false} testID="login-username" />
        <Field label={t('login.password')} value={p} onChangeText={setP} secureTextEntry testID="login-password" />
        {err ? <Text testID="login-error" style={[font.small, { color: c.danger }]}>{err}</Text> : null}
        <Button testID="login-submit" label={t('login.signIn')} onPress={() => go(u, p)} disabled={busy || !u || !p} />
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
