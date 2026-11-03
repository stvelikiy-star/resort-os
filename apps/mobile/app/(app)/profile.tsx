import React from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { LogOut, Repeat } from 'lucide-react-native';
import Constants from 'expo-constants';
import { Button, DemoBanner, SectionLabel, Segmented } from '../../src/components/ui';
import { FutureScreen, GlassCard, PremiumHeader } from '../../src/components/Future';
import { useSession } from '../../src/state/session';
import { useTheme, ThemePref } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import { workspaceForSession } from '../../src/roles/registry';
import { LOCALE_LABEL, LOCALES, Locale } from '../../src/i18n';

export default function Profile() {
  const { t } = useTranslation();
  const { c, pref, setPref } = useTheme();
  const router = useRouter();
  const { user, hotel, api, locale, setLocale, signOut, leaveHotel } = useSession();
  if (!user || !hotel || !api) return <Redirect href="/connect" />;
  const row = (k: string, v: string) => (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 }}>
      <Text style={[font.body, { color: c.textMuted }]}>{k}</Text><Text style={[font.body, { color: c.text, fontWeight: '700' }]}>{v}</Text>
    </View>
  );
  return (
    <FutureScreen>
      <PremiumHeader title={user.display_name} subtitle={user.username} eyebrow="MARINA SMART"/>
      {hotel?.demo ? <DemoBanner /> : null}
      <GlassCard>
        {row(t('profile.hotel'), hotel?.name ?? '')}
        {row(t('profile.role'), user ? t(`roles.${user.role}`) : '')}
        {row(t('profile.mode'), hotel?.demo ? t('profile.modeDemo') : t('profile.modeLive'))}
        {row(t('profile.version'), String(Constants.expoConfig?.version ?? '0.2.0'))}
      </GlassCard>
      {user && !workspaceForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE').mobileReady ? <GlassCard testID="role-soon"><Text style={[font.body, { color: c.textMuted }]}>{t('profile.roleSoon')}</Text></GlassCard> : null}
      <SectionLabel>{t('profile.language')}</SectionLabel>
      <Segmented<Locale> value={locale} onChange={setLocale} options={LOCALES.map((l) => ({ key: l, label: LOCALE_LABEL[l] }))} />
      <SectionLabel>{t('profile.theme')}</SectionLabel>
      <Segmented<ThemePref> value={pref} onChange={setPref} options={[{ key: 'system', label: t('profile.system') }, { key: 'light', label: t('profile.light') }, { key: 'dark', label: t('profile.dark') }]} />
      <View style={{ gap: space.sm, marginTop: space.md }}>
        <Button label={t('profile.switchHotel')} icon={Repeat} variant="secondary" onPress={() => { leaveHotel(); router.replace('/connect'); }} />
        <Button testID="sign-out" label={t('profile.signOut')} icon={LogOut} variant="danger" onPress={async () => { await signOut(); router.replace('/login'); }} />
      </View>
    </FutureScreen>
  );
}
