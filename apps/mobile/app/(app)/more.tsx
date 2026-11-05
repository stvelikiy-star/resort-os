import React from 'react';
import { Redirect, useRouter } from 'expo-router';
import { Text, View } from 'react-native';
import { ArrowUpRight, CircleUserRound, Grid2X2, BedDouble, CalendarDays, ClipboardCheck, MessageCircle, ConciergeBell, UtensilsCrossed, Wrench, ChartNoAxesCombined } from 'lucide-react-native';
import { FutureScreen, GlassCard, PremiumHeader } from '../../src/components/Future';
import { Empty, SectionLabel } from '../../src/components/ui';
import { mobileTabPlan } from '../../src/roles/navigation';
import { workspaceForSession, TabKey, homeForSession } from '../../src/roles/registry';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

const ICONS = {
  overview: ChartNoAxesCombined, reception: ConciergeBell, pms: CalendarDays, inbox: MessageCircle,
  dining: UtensilsCrossed, tasks: ClipboardCheck, rooms: BedDouble, requests: Wrench,
  admin: Grid2X2, profile: CircleUserRound,
} as const;
export default function MoreScreen() {
  const { user, hotel, api, serverAuthMode } = useSession();
  const router = useRouter();
  const copy = useMobileCopy();
  const { c } = useTheme();
  if (!user) return <Redirect href="/connect" />;
  const ws = workspaceForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', serverAuthMode);
  const { overflow } = mobileTabPlan(ws.tabs);
  if (!overflow.length) return <Redirect href={homeForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', serverAuthMode)} />;
  return <FutureScreen>
    <PremiumHeader title={copy.moreMenu} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    <SectionLabel>{copy.available}</SectionLabel>
    <View style={{ gap: space.md }}>
      {overflow.map((key: TabKey) => {
        const Icon = ICONS[key];
        return <GlassCard key={key} testID={'more-' + key} onPress={() => router.push('/' + key as never)}
          style={{ minHeight: 76, flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <View style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: c.primarySoft, justifyContent: 'center', alignItems: 'center' }}>
            <Icon size={24} color={c.primary}/>
          </View>
          <Text style={[font.h2, { color: c.text, flex: 1 }]}>{copy[key]}</Text>
          <ArrowUpRight size={20} color={c.textMuted}/>
        </GlassCard>;
      })}
    </View>
    {!overflow.length ? <Empty text={copy.empty}/> : null}
  </FutureScreen>;
}
