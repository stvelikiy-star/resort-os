import React, { useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Text, View, useWindowDimensions } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { BedDouble, MessageCircle, ShieldAlert, Wallet, CalendarDays, ClipboardCheck, Users, Wrench, Sparkles } from 'lucide-react-native';
import { Hero } from '../../src/components/Brand';
import { DemoBanner, Empty, SectionLabel } from '../../src/components/ui';
import { AIOrb, AnimatedKpi, ErrorState, FutureScreen, GlassCard, LoadingShimmer, MetricCard, OccupancyRing, PremiumHeader, QuickAction, StaggerItem } from '../../src/components/Future';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { hasTabForSession } from '../../src/roles/registry';
import { useLiveModules, Dashboard } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { demoDashboard } from '../../src/api/demoPresentation';
import { InventorySpectrum } from '../../src/components/InventorySpectrum';
import { contactInitials } from '../../src/i18n/statusLabels';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

export default function Overview() {
  const { user, hotel, api, serverAuthMode, locale } = useSession();
  const showroom = api?.mode === 'DEMO';
  const shared = serverAuthMode === 'shared_auth_preview';
  const canOpen = (tab: 'inbox' | 'pms' | 'tasks' | 'admin') => !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', tab, serverAuthMode);
  const canOpenInbox = !shared && canOpen('inbox');
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const { width } = useWindowDimensions();
  const { t: tr } = useTranslation();
  const priorityLabel = (priority: string) => ['URGENT', 'HIGH', 'NORMAL', 'LOW'].includes(priority) ? tr('tasks.' + priority.toLowerCase()) : priority;
  const router = useRouter();
  const { data, loading, error, reload } = useAsync<Dashboard | null>(async () => showroom && api ? demoDashboard(hotel?.name ?? 'DEMO', await api.listRooms(), await api.listTasks(), locale) : live ? live.dashboard() : null, [live, api, showroom, hotel?.id, user?.id, locale, user?.module_permissions?.join(',')]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const money = (value: number) => Number.isFinite(value) ? Number(value).toLocaleString('ru-RU') + ' KGS' : '—';
  const count = (value: number) => Number.isFinite(value) && value >= 0 ? String(value) : '—';
  return <FutureScreen>
    <PremiumHeader title={copy.overview} subtitle={hotel?.name} eyebrow={user ? copy.welcome + ', ' + user.display_name : 'MARINA SMART'}
      right={user ? <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <View accessibilityLabel={copy.profile + ': ' + user.display_name}
          style={{ width: 48, height: 48, borderRadius: 24, borderWidth: 1, borderColor: c.border, backgroundColor: c.primarySoft, justifyContent: 'center', alignItems: 'center' }}>
          <Text style={[font.h2, { color: c.primary }]}>{contactInitials(user.display_name) || '•'}</Text>
        </View>
        {!shared && live && ['OWNER','MANAGER'].includes(user.role) ? <AIOrb label="MARINA AI" size={38} onPress={() => router.push('/ai')}/> : null}
      </View> : null}/>
    {hotel?.demo ? <DemoBanner/> : null}
    {!live && !showroom ? <Empty text={copy.unavailable}/> : null}
    {loading && (live || showroom) ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <StaggerItem index={0}><Hero>
        <View style={{ flexDirection:'row', alignItems:'center', justifyContent:'space-between' }}>
          <Text numberOfLines={2} style={[font.label, { color:'#C8E8F5', flex: 1, minWidth: 0 }]}>{data.property.name.toUpperCase()} · {data.property.local_date}</Text>
          <Text style={[font.label, { color:'#E7C480' }]}>{hotel?.demo ? copy.demoLabel : 'LIVE PMS'}</Text>
        </View>
        <View style={{ flexDirection:'row', alignItems:'center', gap:width < 350 ? 6 : 12, marginTop:8 }}>
          <View style={{ flex:1 }}>
            <AnimatedKpi value={data.stays.occupancy_percent} suffix="%" style={[font.display, { color:'#FFFFFF', fontSize:width < 350 ? 34 : 43 }]}/>
            <Text style={[font.body, { color:'#D6E9F7' }]}>{copy.occupancy} · {data.stays.occupied_rooms}/{data.rooms.total}</Text>
          </View>
          <OccupancyRing percent={data.stays.occupancy_percent} label={copy.occupancy} size={width < 350 ? 82 : 112}/>
        </View>
        <View style={{ height:1, backgroundColor:'rgba(255,255,255,0.16)', marginTop:20, marginBottom:14 }}/>
        <View style={{ flexDirection:'row', gap:space.lg }}>
          <View style={{ flex:1 }}><AnimatedKpi value={data.stays.arrivals_today} style={[font.h2,{color:'#FFFFFF'}]}/><Text style={[font.small,{color:'#D6E9F7'}]}>{copy.arrivals}</Text></View>
          <View style={{ flex:1 }}><AnimatedKpi value={data.stays.departures_today} style={[font.h2,{color:'#FFFFFF'}]}/><Text style={[font.small,{color:'#D6E9F7'}]}>{copy.departures}</Text></View>
        </View>
      </Hero></StaggerItem>
      {user?.role === 'MANAGER' ? <GlassCard style={{ gap: 8, borderLeftWidth: 4, borderLeftColor: c.warning }}>
        <Text style={[font.h2, { color: c.text }]}>{copy.shiftBriefing}</Text>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
          <Text style={[font.body, { color: c.textMuted }]}>{copy.urgent}: <Text style={{ color: c.warning, fontWeight: '800' }}>{count(data.tasks.urgent_active)}</Text></Text>
          <Text style={[font.body, { color: c.textMuted }]}>{copy.needsReply}: <Text style={{ color: c.text, fontWeight: '800' }}>{count(data.communications.needs_reply)}</Text></Text>
        </View>
      </GlassCard> : null}
      <SectionLabel>{copy.today} · {data.property.local_date}</SectionLabel>
      <View style={{ flexDirection:'row', flexWrap:'wrap', gap:space.md }}>
        <MetricCard icon={Wallet} label={copy.revenue} detail={copy.paymentsNotProfit} value={money(data.finance.confirmed_payments_today_kgs)}/>
        <MetricCard icon={ShieldAlert} label={copy.debt} value={money(data.finance.active_reservations_remaining_kgs)}/>
        <MetricCard icon={MessageCircle} label={copy.needsReply} value={count(data.communications.needs_reply)} onPress={canOpenInbox ? () => router.push('/inbox') : undefined}/>
        <MetricCard icon={BedDouble} label={copy.dirty} value={count(data.rooms.dirty)} onPress={canOpen('pms') ? () => router.push('/pms') : undefined}/>
      </View>
      <SectionLabel>{copy.available}</SectionLabel>
      {canOpen('pms') ? <QuickAction icon={CalendarDays} label={copy.pms} onPress={() => router.push('/pms')}/> : null}
      {canOpenInbox ? <QuickAction icon={MessageCircle} label={copy.inbox} onPress={() => router.push('/inbox')}/> : null}
      {canOpen('tasks') ? <QuickAction icon={ClipboardCheck} label={copy.tasks} onPress={() => router.push('/tasks')}/> : null}
      {canOpen('admin') ? <QuickAction icon={Users} label={copy.staffOverview} onPress={() => router.push('/admin')}/> : null}
      <SectionLabel>{copy.roomCondition}</SectionLabel>
      <InventorySpectrum totals={data.rooms} total={data.rooms.total} labels={{clean:copy.clean,dirty:copy.dirty,inspection:copy.checking,blocked:copy.tech}}/>
      <GlassCard style={{ gap: space.md }}>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
          {([
            { label: copy.clean, value: data.rooms.clean, color: c.success },
            { label: copy.dirty, value: data.rooms.dirty, color: c.warning },
            { label: copy.checking, value: data.rooms.in_inspection, color: c.info },
            { label: copy.tech, value: data.rooms.tech_block, color: c.danger },
          ]).map(item => <View key={item.label} style={{ width: width < 350 ? '100%' : '46%', flexGrow: 1, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <View style={{ width: 8, height: 8, borderRadius: radius.pill, backgroundColor: item.color }}/>
            <Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{item.label}</Text>
            <Text style={[font.h2, { color: c.text }]}>{count(item.value)}</Text>
          </View>)}
        </View>
      </GlassCard>
      <SectionLabel>{copy.tasks}</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        <MetricCard icon={Sparkles} label={copy.housekeepingOverview} value={count(data.tasks.housekeeping_active)} onPress={canOpen('tasks') ? () => router.push('/tasks') : undefined}/>
        <MetricCard icon={Wrench} label={copy.maintenanceOverview} value={count(data.tasks.maintenance_active)} onPress={canOpen('tasks') ? () => router.push('/tasks') : undefined}/>
      </View>
      {data.today.arrivals.length ? <SectionLabel>{copy.arrivalList} · {data.today.arrivals.length}</SectionLabel> : null}
      {data.today.arrivals.slice(0, 3).map((x, i) => <StaggerItem key={x.id} index={i}>
        <GlassCard onPress={!showroom && canOpen('pms') ? () => router.push({ pathname: '/reservation/[id]', params: { id: x.id } }) : undefined}>
          <Text style={[font.h2, { color: c.text }]}>{x.guest_name || x.booking_number}</Text>
          <Text style={[font.small, { color: c.textMuted }]}>{x.booking_number} · {x.room_code || '—'}</Text>
        </GlassCard>
      </StaggerItem>)}
      {data.today.departures.length ? <SectionLabel>{copy.departureList} · {data.today.departures.length}</SectionLabel> : null}
      {data.today.departures.slice(0, 3).map((x, i) => <StaggerItem key={x.id} index={i}>
        <GlassCard onPress={!showroom && canOpen('pms') ? () => router.push({ pathname: '/reservation/[id]', params: { id: x.id } }) : undefined}>
          <Text style={[font.h2, { color: c.text }]}>{x.guest_name || x.booking_number}</Text>
          <Text style={[font.small, { color: c.textMuted }]}>{x.booking_number} · {x.room_code || '—'}</Text>
        </GlassCard>
      </StaggerItem>)}
      <SectionLabel>{copy.urgent} · {data.tasks.urgent_active}</SectionLabel>
      {data.attention_tasks.length === 0 ? <Empty text={copy.empty}/> : data.attention_tasks.slice(0,8).map((task, i) => <StaggerItem index={i+1} key={task.id}>
        <GlassCard onPress={user?.module_permissions?.includes('OPS') ? () => router.push({pathname:'/task/[id]',params:{id:task.id}}) : undefined} style={{ flexDirection:'row',alignItems:'center',gap:12 }}>
          <View style={{width:42,height:42,borderRadius:14,backgroundColor:c.warningSoft,alignItems:'center',justifyContent:'center'}}><ShieldAlert size={22} color={c.warning}/></View>
          <View style={{flex:1}}><Text style={[font.h2,{color:c.text}]}>{task.title}</Text><Text style={[font.small,{color:c.textMuted}]}>{task.room_code||'—'} · {priorityLabel(task.priority)}</Text></View>
        </GlassCard>
      </StaggerItem>)}
    </> : null}
  </FutureScreen>;
}
