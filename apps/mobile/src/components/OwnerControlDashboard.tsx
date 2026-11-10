import React, { useLayoutEffect, useRef, useState } from 'react';
import { Animated, Text, View, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { ArrowUpRight, BedDouble, CalendarCheck2, CalendarClock, ClipboardCheck, DoorOpen, MessageSquareText, ShieldAlert, UsersRound, Wallet, Wrench, ChefHat } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import type { Dashboard } from '../api/liveModules';
import { canReadFinance } from '../api/financeAccess';
import type { AuthUser } from '../api/types';
import { useMobileCopy } from '../i18n/mobileCopy';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space } from '../theme/tokens';
import { motionPresets, useMotionPreference } from '../theme/motion';
import { Empty, SectionLabel } from './ui';
import { GlassCard, StaggerItem } from './Future';

type Copy = ReturnType<typeof useMobileCopy>;
type OwnerTab = 'overview' | 'pms' | 'tasks' | 'inbox' | 'admin' | 'kitchen';
interface Props {
  data: Dashboard;
  user: AuthUser;
  copy: Copy;
  canOpen: (tab: OwnerTab) => boolean;
  canOpenInbox: boolean;
  showroom: boolean;
}

export function occupancyProgress(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
}

function OccupancyProgress({ value, label, color, trackColor }: {
  value: number; label: string; color: string; trackColor: string;
}) {
  const safe = occupancyProgress(value);
  const { allowed, ready } = useMotionPreference();
  const [progress] = useState(() => new Animated.Value(1));
  const appeared = useRef(false);
  useLayoutEffect(() => {
    progress.stopAnimation();
    if (!ready || appeared.current || !allowed) {
      if (ready) appeared.current = true;
      progress.setValue(1);
      return;
    }
    appeared.current = true;
    progress.setValue(0);
    const animation = Animated.timing(progress, {
      toValue: 1,
      duration: motionPresets.chart.duration,
      easing: motionPresets.chart.easing,
      useNativeDriver: false,
    });
    animation.start();
    return () => animation.stop();
  }, [allowed, ready, progress, safe]);
  const width = progress.interpolate({ inputRange: [0, 1], outputRange: ['0%', `${safe}%`] });
  return <View accessible accessibilityRole="progressbar" accessibilityLabel={label}
    accessibilityValue={{ min: 0, max: 100, now: Math.round(safe) }}
    style={{ height: 9, backgroundColor: trackColor, borderRadius: radius.pill, overflow: 'hidden' }}>
    <Animated.View style={{ height: 9, width, backgroundColor: color, borderRadius: radius.pill }}/>
  </View>;
}

/** Stable two-column executive grid. Only verified dashboard fields are displayed;
 * absent financial permissions never turn into fake zero-value financial tiles. */
export function OwnerControlDashboard({ data, user, copy, canOpen, canOpenInbox, showroom }: Props) {
  const { c, name } = useTheme();
  const router = useRouter();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 350 || fontScale > 1.3;
  const count = (n: number) => Number.isFinite(n) && n >= 0 ? String(Math.round(n)) : '—';
  const currency = (n: number) => Number.isFinite(n) && n >= 0
    ? Math.round(n).toLocaleString('ru-RU') + ' KGS' : '—';
  const open = (route: '/pms' | '/inbox' | '/tasks' | '/admin' | '/finance' | '/kitchen') => () => router.push(route);
  const metric = (icon: LucideIcon, title: string, value: string, tint: string, action?: () => void) => {
    const Icon = icon;
    return <GlassCard key={title} onPress={action} style={{
      flex: 1, flexBasis: compact ? '100%' : '46%', minWidth: 0, minHeight: compact ? 112 : 136, padding: compact ? 12 : 14,
      gap: 8, justifyContent: 'space-between', borderTopWidth: 2, borderTopColor: tint,
    }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <View style={{ width: 36, height: 36, borderRadius: 11, backgroundColor: c.surfaceAlt,
          alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={20} color={tint} strokeWidth={2}/>
        </View>
        {action ? <ArrowUpRight color={tint} size={17}/> : null}
      </View>
      <Text adjustsFontSizeToFit minimumFontScale={0.55} numberOfLines={1}
        style={[font.metric, { fontSize: compact ? 23 : 27, color: c.text, minWidth: 0 }]}>{value}</Text>
      <Text numberOfLines={2} style={[font.small, { color: c.textMuted, fontWeight: '600', lineHeight: 17 }]}>{title}</Text>
    </GlassCard>;
  };
  const row = (index: number, ...items: React.ReactNode[]) => <StaggerItem index={index}>
    <View style={{ flexDirection: 'row', flexWrap: compact ? 'wrap' : 'nowrap', alignItems: 'stretch', gap: space.sm }}>{items}</View>
  </StaggerItem>;
  const canFinance = !showroom && canReadFinance(user);
  const nav = [
    { title: copy.pms, icon: CalendarCheck2, route: '/pms' as const, show: canOpen('pms') },
    { title: copy.inbox, icon: MessageSquareText, route: '/inbox' as const, show: canOpenInbox },
    { title: copy.tasks, icon: ClipboardCheck, route: '/tasks' as const, show: canOpen('tasks') },
    { title: copy.staffOverview, icon: UsersRound, route: '/admin' as const, show: canOpen('admin') },
    { title: copy.kitchen, icon: ChefHat, route: '/kitchen' as const, show: !showroom && canOpen('kitchen') },
  ].filter(item => item.show);
  // An empty inventory is not 0% occupancy: it means the property has no verified denominator.
  const occupancyKnown = Number.isInteger(data.rooms.total) && data.rooms.total > 0 &&
    Number.isFinite(data.stays.occupancy_percent) && data.stays.occupancy_percent >= 0 && data.stays.occupancy_percent <= 100;
  const occupancy = occupancyKnown ? data.stays.occupancy_percent : 0;
  return <View testID="owner-control-dashboard" style={{ gap: space.lg }}>
    <GlassCard style={{ padding: compact ? 17 : 20, backgroundColor: c.surface, gap: space.md }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text numberOfLines={1} style={[font.label, { color: c.cyan }]}>{data.property.name.toUpperCase()}</Text>
          <Text style={[font.small, { color: c.textMuted, marginTop: 4 }]}>{data.property.local_date}</Text>
        </View>
        <Text style={[font.label, { color: name === 'light' ? c.warning : c.gold }]}>{showroom ? copy.demoLabel : copy.livePmsLabel}</Text>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <Text style={[font.display, { color: c.text, fontSize: compact ? 38 : 44 }]}>{occupancyKnown ? count(occupancy) + "%" : "—"}</Text>
        <Text style={[font.small, { color: c.textMuted, flexShrink: 1, textAlign: 'right' }]}>
          {copy.occupancy} · {count(data.stays.occupied_rooms)}/{count(data.rooms.total)}
        </Text>
      </View>
      {occupancyKnown ? <OccupancyProgress value={occupancy} label={copy.occupancy}
        color={c.cyan} trackColor={c.surfaceAlt}/> : null}
    </GlassCard>

    <View style={{ gap: space.sm }}>
      <SectionLabel>{copy.today} · {data.property.local_date}</SectionLabel>
      {row(0,
        metric(DoorOpen, copy.arrivals, count(data.stays.arrivals_today), c.cyan, canOpen('pms') ? open('/pms') : undefined),
        metric(CalendarClock, copy.departures, count(data.stays.departures_today), c.gold, canOpen('pms') ? open('/pms') : undefined),
      )}
      {row(1,
        metric(MessageSquareText, copy.needsReply, count(data.communications.needs_reply), c.cyan, canOpenInbox ? open('/inbox') : undefined),
        metric(BedDouble, copy.dirty, count(data.rooms.dirty), c.warning, canOpen('pms') ? open('/pms') : undefined),
      )}
      {row(2,
        metric(ClipboardCheck, copy.housekeepingOverview, count(data.tasks.housekeeping_active), c.success, canOpen('tasks') ? open('/tasks') : undefined),
        metric(Wrench, copy.maintenanceOverview, count(data.tasks.maintenance_active), c.warning, canOpen('tasks') ? open('/tasks') : undefined),
      )}
      {canFinance ? row(3,
        metric(Wallet, copy.revenue, currency(data.finance.confirmed_payments_today_kgs), c.gold, open('/finance')),
        metric(ShieldAlert, copy.debt, currency(data.finance.active_reservations_remaining_kgs), c.warning, open('/finance')),
      ) : null}
      {canFinance ? <Text style={[font.small, { color: c.textMuted }]}>{copy.paymentsNotProfit}</Text> : null}
    </View>

    <View style={{ gap: space.sm }}>
      <SectionLabel>{copy.available}</SectionLabel>
      {nav.length ? <View style={{ gap: space.sm }}>{Array.from({length: Math.ceil(nav.length/2)},(_,i) =>
        <View key={i} style={{ flexDirection: 'row', gap: space.sm }}>
          {nav.slice(i*2,i*2+2).map(item => <GlassCard key={item.route} onPress={open(item.route)} style={{
            flex: 1, minWidth: 0, minHeight: 94, padding: 13, gap: 8,
          }}>
            <item.icon size={24} color={c.primary}/>
            <Text numberOfLines={2} style={[font.small, { color: c.text, fontWeight: '700' }]}>{item.title}</Text>
          </GlassCard>)}
          {nav.length % 2 === 1 && i === Math.floor(nav.length/2) ? <View style={{ flex: 1 }}/> : null}
        </View>)}</View> : <Empty text={copy.empty}/>}
    </View>
    <View style={{ gap: space.sm }}>
      <SectionLabel>{copy.roomCondition}</SectionLabel>
      {row(4,
        metric(BedDouble, copy.clean, count(data.rooms.clean), c.success),
        metric(ShieldAlert, copy.tech, count(data.rooms.tech_block), c.danger),
      )}
    </View>
    {data.attention_tasks.length > 0 ? <View style={{ gap: space.sm }}>
      <SectionLabel>{copy.urgent} · {count(data.tasks.urgent_active)}</SectionLabel>
      {data.attention_tasks.slice(0,3).map(task =>
        <GlassCard key={task.id} onPress={user.module_permissions?.includes('OPS')
          ? () => router.push({ pathname: '/task/[id]', params: { id: task.id } }) : undefined}
          style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <ShieldAlert color={c.warning} size={22}/>
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text numberOfLines={2} style={[font.body, { color: c.text, fontWeight: '700' }]}>{task.title}</Text>
            <Text style={[font.small, { color: c.textMuted }]}>{task.room_code ?? '—'}</Text>
          </View>
          <ArrowUpRight color={c.primary} size={18}/>
        </GlassCard>)}
    </View> : null}
  </View>;
}
