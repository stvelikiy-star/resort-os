import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { BedDouble, CalendarCheck, CalendarClock, MessageCircle, ShieldAlert, Wallet } from 'lucide-react-native';
import { Hero, Logo } from '../../src/components/Brand';
import { Card, Empty, FadeIn, Screen, SectionLabel, Title } from '../../src/components/ui';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useLiveModules, Dashboard } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function Overview() {
  const { user, hotel } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const { data, loading, error, reload } = useAsync<Dashboard | null>(() => live ? live.dashboard() : Promise.resolve(null), [live, user?.id, user?.module_permissions?.join(',')]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const currency = 'KGS';
  const money = (value: number) => Number(value || 0).toLocaleString('ru-RU') + ' ' + currency;
  return <Screen>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
      <Logo size={54} />
      <View style={{ flex: 1 }}><Title sub={hotel?.name}>{copy.overview}</Title><Text style={[font.small, { color: c.textMuted }]}>{user?.display_name} · {user?.role}</Text></View>
    </View>
    {!live ? <Empty text={copy.unavailable} /> : null}
    {loading && live ? <Empty text={copy.loading} /> : null}
    {error ? <Card onPress={reload}><Text accessibilityRole="alert" style={[font.body, { color: c.danger }]}>{error.message} · {copy.retry}</Text></Card> : null}
    {data ? <>
      <FadeIn><Hero>
        <Text style={[font.small, { color: '#D4E3F4' }]}>{data.property.name} · {data.property.local_date}</Text>
        <Text style={[font.title, { color: '#FFFFFF', fontSize: 38, marginTop: 8 }]}>{data.stays.occupancy_percent}%</Text>
        <Text style={[font.body, { color: '#D4E3F4' }]}>{copy.occupancy}: {data.stays.occupied_rooms} / {data.rooms.total}</Text>
        <View style={{ flexDirection: 'row', gap: space.md, marginTop: space.lg }}>
          <View style={{ flex: 1 }}><Text style={[font.h2, { color: '#fff' }]}>{data.stays.arrivals_today}</Text><Text style={[font.small, { color: '#D4E3F4' }]}>{copy.arrivals}</Text></View>
          <View style={{ flex: 1 }}><Text style={[font.h2, { color: '#fff' }]}>{data.stays.departures_today}</Text><Text style={[font.small, { color: '#D4E3F4' }]}>{copy.departures}</Text></View>
        </View>
      </Hero></FadeIn>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        {[
          { icon: Wallet, label: copy.revenue, value: money(data.finance.confirmed_payments_today_kgs) },
          { icon: ShieldAlert, label: copy.debt, value: money(data.finance.active_reservations_remaining_kgs) },
          { icon: MessageCircle, label: copy.needsReply, value: String(data.communications.needs_reply), go: '/inbox' },
          { icon: BedDouble, label: copy.dirty, value: String(data.rooms.dirty), go: '/pms' },
        ].map((x) => <Card key={x.label} onPress={x.go ? () => router.push(x.go as '/pms') : undefined} style={{ width: '47%', flexGrow: 1, gap: 8 }}>
          <x.icon size={22} color={c.primary} /><Text style={[font.h2, { color: c.text }]}>{x.value}</Text><Text style={[font.small, { color: c.textMuted }]}>{x.label}</Text>
        </Card>)}
      </View>
      <Text style={[font.small, { color: c.textMuted }]}>{copy.paymentsNotProfit}</Text>
      <SectionLabel>{copy.today}</SectionLabel>
      <View style={{ flexDirection: 'row', gap: space.md }}>
        <Card onPress={() => router.push('/pms')} style={{ flex: 1, gap: 6 }}><CalendarCheck color={c.primary} size={26}/><Text style={[font.body, { color: c.text }]}>{copy.arrivals}</Text><Text style={[font.h2, { color: c.text }]}>{data.today.arrivals.length}</Text></Card>
        <Card onPress={() => router.push('/reception')} style={{ flex: 1, gap: 6 }}><CalendarClock color={c.primary} size={26}/><Text style={[font.body, { color: c.text }]}>{copy.departures}</Text><Text style={[font.h2, { color: c.text }]}>{data.today.departures.length}</Text></Card>
      </View>
      <SectionLabel>{copy.urgent} · {data.tasks.urgent_active}</SectionLabel>
      {data.attention_tasks.length === 0 ? <Empty text={copy.empty} /> : data.attention_tasks.slice(0, 8).map(t =>
        <Card key={t.id} onPress={() => router.push({ pathname: '/task/[id]', params: { id: t.id } })}>
          <Text style={[font.body, { color: c.text }]}>{t.title}</Text><Text style={[font.small, { color: c.textMuted }]}>{t.room_code ?? '—'} · {t.priority}</Text>
        </Card>)}
    </> : null}
  </Screen>;
}
