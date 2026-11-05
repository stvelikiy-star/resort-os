import React, { useState } from 'react';
import { Platform, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Building2, Link2, QrCode, ShieldCheck } from 'lucide-react-native';
import { Button, Card, FadeIn, Field, SectionLabel, Segmented } from '../../src/components/ui';
import { Hero, Logo, Wordmark } from '../../src/components/Brand';
import { FutureScreen, GlassCard } from '../../src/components/Future';
import { useSession } from '../../src/state/session';
import { homeForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import { hotelConnectionId, isTrustedHotelOrigin, parseHotelAddress } from '../../src/api/hotels';
import { LOCALE_LABEL, LOCALES, Locale } from '../../src/i18n';

export default function Connect() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { hotelAddress } = useLocalSearchParams<{ hotelAddress?: string }>();
  const { hotels, addHotel, selectHotel, startDemo, locale, setLocale } = useSession();
  const installed = hotels.find(h => !h.demo);
  const [addr, setAddr] = useState(typeof hotelAddress === 'string' ? hotelAddress : '');
  const [err, setErr] = useState<string | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);

  const add = () => {
    const r = parseHotelAddress(addr);
    if (!r.ok) { setErr(t(`connect.${r.reason}`)); return; }
    if (!isTrustedHotelOrigin(r.baseUrl)) { setErr(t('connect.untrusted')); return; }
    const host = new URL(r.baseUrl).hostname;
    try {
      addHotel({ id: hotelConnectionId(r.baseUrl), name: host, city: '', baseUrl: r.baseUrl, demo: false, accent: c.primary });
      setErr(null); router.push('/login');
    } catch { setErr(t('connect.untrusted')); }
  };

  return (
    <FutureScreen>
      <FadeIn style={{ gap: space.md }}>
        <Hero height={196}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><Logo size={68}/><Wordmark color="#FFFFFF"/></View>
          <Text style={[font.title, { color: '#FFFFFF', marginTop: 16 }]}>{t('connect.title')}</Text>
          <Text style={[font.small, { color: '#D7E9F5', marginTop: 5 }]}>{t('connect.subtitle')}</Text>
        </Hero>
        <Segmented<Locale> value={locale} onChange={setLocale} options={LOCALES.map((l) => ({ key: l, label: LOCALE_LABEL[l].slice(0, 3).toUpperCase() }))} />
      </FadeIn>

      {
        <GlassCard testID="web-demo-launcher" style={{ gap: space.md, backgroundColor: c.primarySoft }}>
          <Text style={[font.h2, { color: c.text }]}>{t('connect.tryDemoTitle')}</Text>
          <Text style={[font.body, { color: c.textMuted }]}>{t('connect.tryDemoHint')}</Text>
          <Button testID="web-demo-start" label={t('connect.tryDemoButton')} disabled={demoBusy}
            onPress={async () => {
              if (demoBusy) return;
              setDemoBusy(true); setErr(null);
              try {
                const visitor = await startDemo('owner');
                router.replace(homeForSession(visitor.role, visitor.module_permissions, 'DEMO'));
              } catch {
                setErr(t('errors.generic'));
              } finally { setDemoBusy(false); }
            }} />
        </GlassCard>
      }
      {installed ? (
        <GlassCard style={{ gap: space.md }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
            <Building2 size={26} color={c.primary} />
            <View style={{ flex: 1 }}>
              <Text style={[font.h2, { color: c.text }]}>{installed.name}</Text>
              <Text style={[font.small, { color: c.textMuted }]}>{t('connect.noSecrets')}</Text>
            </View>
          </View>
          <Button testID="connect-bound-hotel" label={t('login.signIn')} onPress={() => {
            if (!isTrustedHotelOrigin(installed.baseUrl)) { setErr(t('connect.untrusted')); return; }
            selectHotel(installed.id); router.replace('/login');
          }} />
        </GlassCard>
      ) : (
        <>
          <SectionLabel>{t('connect.addHotel')}</SectionLabel>
          <GlassCard style={{ gap: space.md }}>
            <Field label={t('connect.code')} placeholder={t('connect.codePh')} value={addr} onChangeText={setAddr} autoCapitalize="none" autoCorrect={false} keyboardType="url" testID="hotel-address" />
            {err ? <Text testID="connect-error" style={[font.small, { color: c.danger }]}>{err}</Text> : null}
            <Button testID="connect-add" label={t('connect.addHotel')} icon={Link2} onPress={add} />
            <Button testID="connect-scan" label={t('connect.scan')} icon={QrCode} variant="secondary" onPress={() => router.push('/scan')} />
          </GlassCard>
        </>
      )}
      {Platform.OS === 'web' ? (
        <Card testID="web-live-cookie-notice" style={{ backgroundColor: c.warningSoft, gap: space.sm }}>
          <Text style={[font.small, { color: c.text }]}>{t('connect.browserLiveNotice')}</Text>
        </Card>
      ) : null}
      <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
        <ShieldCheck size={18} color={c.success} /><Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{t('connect.noSecrets')}</Text>
      </View>
    </FutureScreen>
  );
}
