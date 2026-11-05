import React from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { LogOut, Repeat, Languages, Palette, ArrowLeftRight } from 'lucide-react-native';
import Constants from 'expo-constants';
import { Button, DemoBanner, Segmented } from '../../src/components/ui';
import { FutureScreen, GlassCard, PremiumHeader } from '../../src/components/Future';
import { useSession } from '../../src/state/session';
import { Hero } from '../../src/components/Brand';
import { contactInitials } from '../../src/i18n/statusLabels';
import { useTheme, ThemePref } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import { workspaceForSession } from '../../src/roles/registry';
import { LOCALE_LABEL, LOCALES, Locale } from '../../src/i18n';

export default function Profile() {
  const { t } = useTranslation();
  const { c, pref, setPref } = useTheme();
  const router = useRouter();
  const { user, hotel, api, serverAuthMode, locale, setLocale, signOut, leaveHotel } = useSession();
  if (!user || !hotel || !api) return <Redirect href="/connect" />;
  const row = (k: string, v: string) => (
    <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: space.md, paddingVertical: 8 }}>
      <Text style={[font.body, { color: c.textMuted, flex: 1 }]}>{k}</Text>
      <Text style={[font.body, { color: c.text, fontWeight: '700', flex: 1, textAlign: 'right' }]}>{v}</Text>
    </View>
  );
  return (
    <FutureScreen>
      <PremiumHeader title={t('profile.title')} subtitle={hotel.name} eyebrow="MARINA SMART"/>
      <Hero height={154}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.lg }}>
          <View style={{ width: 66, height: 66, borderRadius: 33, borderWidth: 1, borderColor: '#E6BD70', backgroundColor: 'rgba(255,255,255,0.12)', alignItems: 'center', justifyContent: 'center' }}>
            <Text style={[font.title, { color: '#FFFFFF' }]}>{contactInitials(user.display_name) || '•'}</Text>
          </View>
          <View style={{ flex: 1, minWidth: 0, gap: 5 }}>
            <Text numberOfLines={2} style={[font.h2, { color: '#FFFFFF' }]}>{user.display_name}</Text>
            <Text style={[font.small, { color: '#D6E9F7' }]}>{t('roles.' + user.role)}</Text>
            <Text numberOfLines={1} style={[font.label, { color: '#E6BD70' }]}>{user.username}</Text>
          </View>
        </View>
      </Hero>
      {hotel?.demo ? <DemoBanner /> : null}
      <GlassCard>
        {row(t('profile.hotel'), hotel?.name ?? '')}
        {row(t('profile.role'), user ? t(`roles.${user.role}`) : '')}
        {row(t('profile.mode'), hotel?.demo ? t('profile.modeDemo') : t('profile.modeLive'))}
        {row(t('profile.version'), String(Constants.expoConfig?.version ?? '0.2.0'))}
      </GlassCard>
      {user && !workspaceForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', serverAuthMode).mobileReady ? <GlassCard testID="role-soon"><Text style={[font.body, { color: c.textMuted }]}>{t('profile.roleSoon')}</Text></GlassCard> : null}
      <GlassCard style={{ gap: space.lg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <Languages size={23} color={c.cyan}/>
          <Text style={[font.h2, { color: c.text }]}>{t('profile.language')}</Text>
        </View>
        <Segmented<Locale> value={locale} onChange={setLocale} options={LOCALES.map((l) => ({ key: l, label: LOCALE_LABEL[l] }))} />
      </GlassCard>
      <GlassCard style={{ gap: space.lg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <Palette size={23} color={c.gold}/>
          <Text style={[font.h2, { color: c.text }]}>{t('profile.theme')}</Text>
        </View>
        <Segmented<ThemePref> value={pref} onChange={setPref} options={[{ key: 'system', label: t('profile.system') }, { key: 'light', label: t('profile.light') }, { key: 'dark', label: t('profile.dark') }]} />
      </GlassCard>
      <View style={{ gap: space.sm, marginTop: space.md }}>
        {api.mode === 'DEMO' ? <Button testID="switch-demo-role" label={t('profile.switchDemoRole')} icon={ArrowLeftRight} variant="secondary" onPress={async () => { await signOut(); router.replace('/login'); }}/> : null}
        <Button label={t('profile.switchHotel')} icon={Repeat} variant="secondary" onPress={async () => { await signOut(); leaveHotel(); router.replace('/connect'); }} />
        <Button testID="sign-out" label={t('profile.signOut')} icon={LogOut} variant="danger" onPress={async () => { await signOut(); router.replace('/login'); }} />
      </View>
    </FutureScreen>
  );
}
