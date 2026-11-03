import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Building2, Link2, QrCode, ShieldCheck } from 'lucide-react-native';
import { Badge, Button, Card, DemoBanner, FadeIn, Field, Screen, SectionLabel, Segmented } from '../../src/components/ui';
import { Logo } from '../../src/components/Brand';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import { hotelConnectionId, parseHotelAddress } from '../../src/api/hotels';
import { LOCALE_LABEL, LOCALES, Locale } from '../../src/i18n';

export default function Connect() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { hotelAddress } = useLocalSearchParams<{ hotelAddress?: string }>();
  const { hotels, addHotel, selectHotel, locale, setLocale } = useSession();
  const [addr, setAddr] = useState(typeof hotelAddress === 'string' ? hotelAddress : '');
  const [err, setErr] = useState<string | null>(null);

  const open = (id: string) => { selectHotel(id); router.push('/login'); };
  const add = () => {
    const r = parseHotelAddress(addr);
    if (!r.ok) { setErr(t(`connect.${r.reason}`)); return; }
    const host = new URL(r.baseUrl).hostname;
    addHotel({ id: hotelConnectionId(r.baseUrl), name: host, city: '', baseUrl: r.baseUrl, demo: false, accent: c.primary });
    setErr(null); router.push('/login');
  };

  return (
    <Screen>
      <FadeIn style={{ gap: space.md }}>
        <Logo size={64} />
        <Text style={[font.title, { color: c.text }]}>{t('connect.title')}</Text>
        <Text style={[font.body, { color: c.textMuted }]}>{t('connect.subtitle')}</Text>
        <Segmented<Locale> value={locale} onChange={setLocale} options={LOCALES.map((l) => ({ key: l, label: LOCALE_LABEL[l].slice(0, 3).toUpperCase() }))} />
      </FadeIn>

      <SectionLabel>{t('connect.demoHotels')}</SectionLabel>
      <DemoBanner />
      {hotels.map((h, i) => (
        <FadeIn key={h.id} delay={80 * (i + 1)}>
          <Card testID={`hotel-${h.id}`} onPress={() => open(h.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
            <View style={{ width: 52, height: 52, borderRadius: 16, backgroundColor: h.accent + '33', alignItems: 'center', justifyContent: 'center' }}><Building2 size={26} color={h.accent} /></View>
            <View style={{ flex: 1 }}>
              <Text style={[font.h2, { color: c.text }]}>{h.name}</Text>
              <Text style={[font.small, { color: c.textMuted }]}>{h.city || h.baseUrl}</Text>
            </View>
            <Badge label={h.demo ? 'DEMO' : 'LIVE'} tone={h.demo ? 'warning' : 'success'} />
          </Card>
        </FadeIn>
      ))}

      <SectionLabel>{t('connect.addHotel')}</SectionLabel>
      <Card style={{ gap: space.md }}>
        <Field label={t('connect.code')} placeholder={t('connect.codePh')} value={addr} onChangeText={setAddr} autoCapitalize="none" autoCorrect={false} keyboardType="url" testID="hotel-address" />
        {err ? <Text testID="connect-error" style={[font.small, { color: c.danger }]}>{err}</Text> : null}
        <Button testID="connect-add" label={t('connect.addHotel')} icon={Link2} onPress={add} />
        <Button label={t('connect.scan')} icon={QrCode} variant="secondary" onPress={() => router.push('/scan')} />
      </Card>
      <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
        <ShieldCheck size={18} color={c.success} /><Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{t('connect.noSecrets')}</Text>
      </View>
    </Screen>
  );
}
