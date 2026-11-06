import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Text, TextInput, View, useWindowDimensions } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronRight, LogIn, LogOut, MessageCircle, Search, Users, X } from 'lucide-react-native';
import { Badge, Empty, SectionLabel, Segmented, PressScale, DemoBanner } from '../../src/components/ui';
import { AIOrb, ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, QuickAction, StaggerItem } from '../../src/components/Future';
import { useLiveModules, ReceptionList, ReceptionReservation } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { contactInitials } from '../../src/i18n/statusLabels';
import { demoReception } from '../../src/api/demoPresentation';
import { useSession } from '../../src/state/session';
import { hasTabForSession } from '../../src/roles/registry';
import { useAsync } from '../../src/lib/useAsync';
import { useTheme } from '../../src/theme/ThemeProvider';
import { Hero } from '../../src/components/Brand';
import { font, radius, space } from '../../src/theme/tokens';

export default function Reception() {
  const { user, hotel, api, serverAuthMode, locale } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'reception', serverAuthMode);
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const compactMetrics = width < 375 || fontScale > 1.25;
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [view, setView] = useState<'all' | 'arrivals' | 'departures' | 'staying'>('all');
  const { data, loading, error, reload } = useAsync<ReceptionList | null>(async () => !allowed ? null : showroom && api ? demoReception(locale, await api.listRooms()) : live ? live.reception() : null, [live, api, showroom, user?.id, locale, allowed]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const canInbox = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'inbox', serverAuthMode);
  const visible = useMemo(() => (data?.items ?? []).filter(x => {
    const q = search.trim().toLocaleLowerCase();
    return !q || [x.firstName, x.bookingNumber, x.room_code, x.phone].some(v => (v ?? '').toLocaleLowerCase().includes(q));
  }), [data, search]);
  const arrivals = visible.filter(x => x.checkIn === data?.local_date && x.status === 'GUARANTEED');
  const departures = visible.filter(x => x.checkOut === data?.local_date && x.status === 'CHECKED_IN');
  const pending = visible.filter(x => ['PENDING', 'REQUESTED'].includes(x.status));
  const staying = visible.filter(x => x.status === 'CHECKED_IN' && !departures.includes(x));
  const rest = visible.filter(x => !arrivals.includes(x) && !departures.includes(x) && !pending.includes(x) && !staying.includes(x));

  const bookingState = (x: ReceptionReservation) => {
    if (x.status === 'CHECKED_OUT') return { label: copy.checkedOut, tone: 'neutral' as const };
    if (x.status === 'CANCELLED') return { label: copy.cancelled, tone: 'danger' as const };
    if (x.status === 'CHECKED_IN') return { label: x.checkOut <= (data?.local_date ?? '') ? copy.awaitingDeparture : copy.checkedIn, tone: 'success' as const };
    if (x.status === 'GUARANTEED') return { label: copy.awaitingArrival, tone: 'info' as const };
    if (['PENDING', 'REQUESTED'].includes(x.status)) return { label: copy.pendingConfirmation, tone: 'warning' as const };
    return { label: x.status, tone: 'neutral' as const };
  };
  const card = (x: ReceptionReservation, index: number) => {
    const state = bookingState(x);
    return <StaggerItem index={index} key={x.id}><GlassCard testID={'reservation-' + x.id}
      onPress={!showroom ? () => router.push({ pathname: '/reservation/[id]', params: { id: x.id } }) : undefined}
      style={{ gap: space.sm }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
        <View style={{ width: 44, height: 44, borderRadius: radius.md, backgroundColor: c.primarySoft, alignItems: 'center', justifyContent: 'center' }}>
          {x.firstName ? <Text style={[font.h2, { color: c.primary }]}>{contactInitials(x.firstName)}</Text> : <Users size={22} color={c.primary}/>} 
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{x.firstName || x.bookingNumber}</Text>
          <Text style={[font.small, { color: c.textMuted }]}>{x.bookingNumber} · {x.room_code || '—'}</Text>
        </View>
        <ChevronRight color={c.primary} size={22}/>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Badge label={state.label} tone={state.tone}/>
        {x.room_state === 'DIRTY' ? <Badge label={copy.dirty} tone="warning"/> : null}
        {x.room_state === 'TECH_BLOCK' ? <Badge label={copy.tech} tone="danger"/> : null}
        <Text style={[font.small, { color: c.textMuted }]}>{x.checkIn} → {x.checkOut}</Text>
      </View>
    </GlassCard></StaggerItem>;
  };
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.reception} subtitle={hotel?.name} eyebrow="MARINA SMART"
      right={(live || showroom) && serverAuthMode !== 'shared_auth_preview' ? <AIOrb state={showroom ? 'offline' : 'idle'} label="MARINA AI" size={44} onPress={() => router.push('/ai')}/> : null}/>
    {canInbox ? <QuickAction icon={MessageCircle} label={copy.inbox} onPress={() => router.push('/inbox')}/> : null}
    {live && !showroom && serverAuthMode !== 'shared_auth_preview' &&
      <QuickAction icon={CalendarDays} label={copy.mealPlansTitle} onPress={() => router.push('/meal-plans')}/>}

    {showroom ? <DemoBanner/> : null}
    {!live && !showroom ? <Empty text={copy.unavailable}/> : null}
    {loading && (live || showroom) ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <Hero height={178}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}>
          <CalendarDays color="#E6BD70" size={21}/>
          <Text style={[font.small, { color: '#C8E8F5', letterSpacing: 0.8 }]}>{copy.today} · {data.local_date}</Text>
        </View>
        <View style={{ flexDirection: 'row', gap: compactMetrics ? space.sm : space.lg, marginTop: space.lg }}>
          <View style={{ flex: 1, minWidth: 0, flexDirection: compactMetrics ? 'column' : 'row', alignItems: compactMetrics ? 'flex-start' : 'center', gap: compactMetrics ? 6 : 10 }}>
            <View style={{ width: 44, height: 44, borderRadius: 15, backgroundColor: 'rgba(73,220,183,0.18)', alignItems: 'center', justifyContent: 'center' }}>
              <LogIn size={24} color="#73EBC9"/>
            </View>
            <View style={{ width: '100%', minWidth: 0, gap: 2 }}>
              <Text style={[font.metric, { color: '#FFFFFF' }]}>{arrivals.length}</Text>
              <Text style={[font.small, { color: '#D9EAF6', flexShrink: 1 }]}>{copy.arrivals}</Text>
            </View>
          </View>
          <View style={{ width: 1, backgroundColor: 'rgba(255,255,255,0.2)' }}/>
          <View style={{ flex: 1, minWidth: 0, flexDirection: compactMetrics ? 'column' : 'row', alignItems: compactMetrics ? 'flex-start' : 'center', gap: compactMetrics ? 6 : 10 }}>
            <View style={{ width: 44, height: 44, borderRadius: 15, backgroundColor: 'rgba(230,189,112,0.17)', alignItems: 'center', justifyContent: 'center' }}>
              <LogOut size={24} color="#E6BD70"/>
            </View>
            <View style={{ width: '100%', minWidth: 0, gap: 2 }}>
              <Text style={[font.metric, { color: '#FFFFFF' }]}>{departures.length}</Text>
              <Text style={[font.small, { color: '#D9EAF6', flexShrink: 1 }]}>{copy.departures}</Text>
            </View>
          </View>
        </View>
      </Hero>
      <View style={{ flexDirection: 'row', alignItems: 'center', minHeight: 56, gap: 8, paddingHorizontal: 14, backgroundColor: c.surface, borderWidth: 1, borderRadius: radius.md, borderColor: c.border }}>
        <Search size={20} color={c.textMuted}/>
        <TextInput testID="reception-search" accessibilityLabel={copy.searchReservation} placeholder={copy.searchReservation}
          placeholderTextColor={c.textMuted} autoCorrect={false} returnKeyType="search" value={search} onChangeText={setSearch}
          style={[font.body, { color: c.text, flex: 1, paddingVertical: 10 }]}/>
        {search ? <PressScale accessibilityLabel={copy.clearSearch} onPress={() => setSearch('')} style={{ minWidth: 44, minHeight: 44, alignItems: 'center', justifyContent: 'center' }}><X size={20} color={c.textMuted}/></PressScale> : null}
      </View>
      <Segmented value={view} onChange={setView} options={[{key:'all',label:copy.all},{key:'arrivals',label:copy.arrivals},{key:'departures',label:copy.departures},{key:'staying',label:copy.checkedIn}]}/>
      {(view === 'all' || view === 'arrivals') ? <>
        <SectionLabel>{copy.arrivalList} · {arrivals.length}</SectionLabel>
        {arrivals.length ? arrivals.map(card) : <Empty text={copy.empty}/>}
      </> : null}
      {(view === 'all' || view === 'departures') ? <>
        <SectionLabel>{copy.departureList} · {departures.length}</SectionLabel>
        {departures.length ? departures.map(card) : <Empty text={copy.empty}/>}
      </> : null}
      {view === 'all' && pending.length ? <SectionLabel>{copy.pendingConfirmation} · {pending.length}</SectionLabel> : null}
      {view === 'all' ? pending.map(card) : null}
      {(view === 'all' || view === 'staying') && staying.length ? <SectionLabel>{copy.checkedIn} · {staying.length}</SectionLabel> : null}
      {(view === 'all' || view === 'staying') ? staying.map(card) : null}
      {view === 'all' && rest.length ? <SectionLabel>{copy.bookings} · {rest.length}</SectionLabel> : null}
      {view === 'all' ? rest.map(card) : null}
      {visible.length === 0 || (view === 'staying' && staying.length === 0) ? <Empty text={copy.empty}/> : null}
    </> : null}
  </FutureScreen>;
}
