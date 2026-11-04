import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { BedDouble, MessageCircle, ShieldAlert, Wallet, CalendarDays } from 'lucide-react-native';
import { Hero } from '../../src/components/Brand';
import { DemoBanner, Empty, SectionLabel } from '../../src/components/ui';
import { AIOrb, ErrorState, FutureScreen, GlassCard, LoadingShimmer, MetricCard, OccupancyRing, PremiumHeader, QuickAction, StaggerItem } from '../../src/components/Future';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useLiveModules, Dashboard } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function Overview() {
  const { user, hotel, serverAuthMode } = useSession();
  const shared = serverAuthMode === 'shared_auth_preview';
  const canOpenInbox = !shared && (user?.module_permissions?.includes('WHATSAPP') || user?.module_permissions?.includes('INBOX'));
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const { data, loading, error, reload } = useAsync<Dashboard | null>(() => live ? live.dashboard() : Promise.resolve(null), [live, user?.id, user?.module_permissions?.join(',')]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const money = (value: number) => Number(value).toLocaleString('ru-RU') + ' KGS';
  return <FutureScreen>
    <PremiumHeader title={copy.overview} subtitle={hotel?.name} eyebrow={user?.display_name || 'MARINA SMART'}
      right={!shared && live && user && ['OWNER','MANAGER'].includes(user.role) ? <AIOrb label="MARINA AI" size={46} onPress={() => router.push('/ai')}/> : null}/>
    {hotel?.demo ? <DemoBanner/> : null}
    {!live ? <Empty text={copy.unavailable}/> : null}
    {loading && live ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <StaggerItem index={0}><Hero>
        <View style={{ flexDirection:'row', alignItems:'center', justifyContent:'space-between' }}>
          <Text style={[font.label, { color:'#C8E8F5' }]}>{data.property.name.toUpperCase()} · {data.property.local_date}</Text>
          <Text style={[font.label, { color:'#E7C480' }]}>LIVE PMS</Text>
        </View>
        <View style={{ flexDirection:'row', alignItems:'center', gap:12, marginTop:8 }}>
          <View style={{ flex:1 }}>
            <Text style={[font.display, { color:'#FFFFFF', fontSize:43 }]}>{data.stays.occupancy_percent}%</Text>
            <Text style={[font.body, { color:'#D6E9F7' }]}>{copy.occupancy} · {data.stays.occupied_rooms}/{data.rooms.total}</Text>
          </View>
          <OccupancyRing percent={data.stays.occupancy_percent} label={copy.occupancy}/>
        </View>
        <View style={{ height:1, backgroundColor:'rgba(255,255,255,0.16)', marginTop:20, marginBottom:14 }}/>
        <View style={{ flexDirection:'row', gap:space.lg }}>
          <View style={{ flex:1 }}><Text style={[font.h2,{color:'#FFFFFF'}]}>{data.stays.arrivals_today}</Text><Text style={[font.small,{color:'#D6E9F7'}]}>{copy.arrivals}</Text></View>
          <View style={{ flex:1 }}><Text style={[font.h2,{color:'#FFFFFF'}]}>{data.stays.departures_today}</Text><Text style={[font.small,{color:'#D6E9F7'}]}>{copy.departures}</Text></View>
        </View>
      </Hero></StaggerItem>
      <SectionLabel>{copy.today}</SectionLabel>
      <View style={{ flexDirection:'row', flexWrap:'wrap', gap:space.md }}>
        <MetricCard icon={Wallet} label={copy.revenue} detail={copy.paymentsNotProfit} value={money(data.finance.confirmed_payments_today_kgs)}/>
        <MetricCard icon={ShieldAlert} label={copy.debt} value={money(data.finance.active_reservations_remaining_kgs)}/>
        <MetricCard icon={MessageCircle} label={copy.needsReply} value={String(data.communications.needs_reply)} onPress={canOpenInbox ? () => router.push('/inbox') : undefined}/>
        <MetricCard icon={BedDouble} label={copy.dirty} value={String(data.rooms.dirty)} onPress={user?.module_permissions?.includes('PMS') ? () => router.push('/pms') : undefined}/>
      </View>
      <SectionLabel>{copy.available}</SectionLabel>
      {user?.module_permissions?.includes('PMS') ? <QuickAction icon={CalendarDays} label={copy.pms} onPress={() => router.push('/pms')}/> : null}
      {canOpenInbox ? <QuickAction icon={MessageCircle} label={copy.inbox} onPress={() => router.push('/inbox')}/> : null}
      <SectionLabel>{copy.urgent} · {data.tasks.urgent_active}</SectionLabel>
      {data.attention_tasks.length === 0 ? <Empty text={copy.empty}/> : data.attention_tasks.slice(0,8).map((t, i) => <StaggerItem index={i+1} key={t.id}>
        <GlassCard onPress={() => router.push({pathname:'/task/[id]',params:{id:t.id}})} style={{ flexDirection:'row',alignItems:'center',gap:12 }}>
          <View style={{width:42,height:42,borderRadius:14,backgroundColor:c.warningSoft,alignItems:'center',justifyContent:'center'}}><ShieldAlert size={22} color={c.warning}/></View>
          <View style={{flex:1}}><Text style={[font.h2,{color:c.text}]}>{t.title}</Text><Text style={[font.small,{color:c.textMuted}]}>{t.room_code||'—'} · {t.priority}</Text></View>
        </GlassCard>
      </StaggerItem>)}
    </> : null}
  </FutureScreen>;
}
