import React, { useCallback, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, Plus, BedDouble, UtensilsCrossed } from 'lucide-react-native';
import { Badge, Button, Empty, PressScale, SectionLabel, Segmented, DemoBanner } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { Grid, GridRoom, localDate, useLiveModules } from '../../src/api/liveModules';
import { CONFIRMED_BACKEND_FEATURES } from '../../src/api/features';
import { pmsCellState } from '../../src/roles/pmsPresentation';
import { isPmsDateFree, shortPmsGuestLabel } from '../../src/roles/pmsSelection';
import { PmsBookingSheet, type PmsSelectedBlock } from '../../src/components/PmsBookingSheet';
import { useMobileCopy, pmsWeekdayLabels } from '../../src/i18n/mobileCopy';
import { demoGrid } from '../../src/api/demoPresentation';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { canCreateBooking, canStartBookingFromPms } from '../../src/roles/bookingAccess';
import { hasTabForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius } from '../../src/theme/tokens';

function dayAt(start: string, offset: number): string {
  const d = new Date(start + 'T12:00:00'); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
const DAYS = 7, CELL_WIDTH = 72, ROW_HEIGHT = 76, LABEL_WIDTH = 104;

export default function Pms() {
  const { hotel, user, locale, api, serverAuthMode } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'pms', serverAuthMode);
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const [start, setStart] = useState(() => localDate());
  const [filter, setFilter] = useState<'all' | 'attention'>('all');
  const [selectedBlock, setSelectedBlock] = useState<PmsSelectedBlock | null>(null);
  const { data, loading, error, reload } = useAsync<Grid | null>(async () => !allowed ? null : showroom && api ? demoGrid(locale, await api.listRooms(), hotel?.name ?? 'DEMO') : live ? live.pmsGrid(start, dayAt(start, DAYS)) : null, [live, api, showroom, user?.id, start, locale, hotel?.id, allowed]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const dates = Array.from({ length: DAYS }, (_, i) => dayAt(start, i));
  const shownRooms = (data?.rooms ?? []).filter(room => filter === 'all' || ['DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'].includes(room.operational_state));
  const occupancyFor = (room: GridRoom, day: string) => room.blocks.filter(b => b.start <= day && day < b.end);
  const cell = (room: GridRoom, day: string) => {
    const blocks = occupancyFor(room, day);
    const block = blocks[0];
    const state = pmsCellState(blocks, day);
    const tone = state === 'RESERVATION' ? c.primary : state === 'HOLD' ? c.warningSoft
      : state === 'BLOCKED' || state === 'CONFLICT' ? c.dangerSoft : c.surfaceAlt;
    const ink = state === 'RESERVATION' ? c.primaryText : state === 'HOLD' ? c.warning
      : state === 'BLOCKED' || state === 'CONFLICT' ? c.danger : c.textMuted;
    const label = state === 'RESERVATION' && block ? shortPmsGuestLabel(block)
      : state === 'HOLD' ? 'HOLD' : state === 'BLOCKED' ? '×'
      : state === 'CONFLICT' ? '!' : '+';
    const semantic = state === 'RESERVATION' ? copy.bookings : state === 'HOLD' ? copy.holds
      : state === 'BLOCKED' ? copy.blocked : state === 'CONFLICT' ? copy.conflict : copy.available;
    const free = isPmsDateFree(room, day, localDate()) && (!!showroom || canCreateBooking(user));
    const openBlock = !!block && (showroom || user?.role !== 'AGENT' || state !== 'RESERVATION');
    return <PressScale key={day} testID={'pms-' + room.id + '-' + day}
      accessibilityLabel={room.code + ' ' + day + ' · ' + semantic + (block?.guest_name ? ' · ' + block.guest_name : '')}
      disabled={!free && !openBlock} dimWhenDisabled={false}
      onPress={() => {
        if (state === 'FREE' && free) {
          setSelectedBlock(null);
          router.push({ pathname: '/new-booking', params: { room_id: room.id, check_in: day, check_out: dayAt(day, 1) } });
        } else if (block && openBlock) {
          setSelectedBlock({room, block, state});
        }
      }}
      style={{ width: CELL_WIDTH - 4, height: ROW_HEIGHT - 6, marginRight: 4, borderRadius: radius.sm,
        backgroundColor: tone, justifyContent: 'center', alignItems: 'center',
        paddingHorizontal: 3, borderWidth: 1,
        borderColor: state === 'RESERVATION' ? tone : c.border }}>
      <Text numberOfLines={2} adjustsFontSizeToFit minimumFontScale={0.7}
        style={[font.small, { color: ink, fontSize: state === 'RESERVATION' ? 11 : 17,
          fontWeight: '800', textAlign: 'center' }]}>{label}</Text>
    </PressScale>;
  };
  const roomState = (room: GridRoom) =>
    room.operational_state === 'CLEAN' ? copy.clean : room.operational_state === 'DIRTY' ? copy.dirty
      : room.operational_state === 'TECH_BLOCK' ? copy.tech : room.operational_state === 'IN_INSPECTION' ? copy.checking : room.operational_state;
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.pms} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    {live && serverAuthMode !== 'shared_auth_preview' && user &&
      ['OWNER','MANAGER','RECEPTION'].includes(user.role) ?
      <Button testID="pms-meal-plans" variant="secondary" label={copy.mealPlansTitle} icon={UtensilsCrossed}
        onPress={() => router.push('/meal-plans')}/> : null}
    {live && user && canStartBookingFromPms(user.role) ? <Button testID="pms-new-booking" label={copy.newBooking} icon={Plus} onPress={() => router.push('/new-booking')}/> : null}
    {live && CONFIRMED_BACKEND_FEATURES.pmsHolds && user && ['OWNER','MANAGER'].includes(user.role) ? <Button testID="pms-holds" variant="secondary" label={copy.holds} icon={Clock3} onPress={() => router.push('/holds')}/> : null}
    <GlassCard style={{ gap: 10 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <PressScale testID="pms-prev" accessibilityLabel={copy.previous} onPress={() => setStart(dayAt(start, -7))}
          style={{ width: 48, minHeight: 48, borderRadius: radius.md, backgroundColor: c.primarySoft, justifyContent: 'center', alignItems: 'center' }}><ChevronLeft color={c.primary} size={24}/></PressScale>
        <View style={{ flex: 1, alignItems: 'center', gap: 3 }}><CalendarDays size={20} color={c.cyan}/>
          <Text style={[font.small, { color: c.text, textAlign: 'center' }]}>{start.slice(5)} — {dayAt(start, 6).slice(5)}</Text></View>
        <PressScale testID="pms-next" accessibilityLabel={copy.next} onPress={() => setStart(dayAt(start, 7))}
          style={{ width: 48, minHeight: 48, borderRadius: radius.md, backgroundColor: c.primarySoft, justifyContent: 'center', alignItems: 'center' }}><ChevronRight color={c.primary} size={24}/></PressScale>
        <PressScale testID="pms-today" accessibilityLabel={copy.today} onPress={() => setStart(localDate())}
          style={{ width: 48, minHeight: 48, borderRadius: radius.md, backgroundColor: c.surfaceAlt, justifyContent: 'center', alignItems: 'center' }}><CalendarDays color={c.primary} size={22}/></PressScale>
      </View>
    </GlassCard>
    {showroom ? <DemoBanner/> : null}
    {!live && !showroom ? <Empty text={copy.unavailable}/> : null}
    {loading && (live || showroom) ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <SectionLabel>{copy.rooms} · {data.rooms.length}</SectionLabel>
      <Segmented value={filter} options={[{ key: 'all', label: copy.all }, { key: 'attention', label: copy.needsAttention }]} onChange={setFilter}/>
      <Text style={[font.small, { color: c.textMuted }]}>{copy.gridHint}</Text>
      <GlassCard style={{ padding: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
          <View style={{ width: LABEL_WIDTH, flexShrink: 0 }}>
            <View style={{ height: 46, flexDirection: 'row', alignItems: 'center', gap: 4 }}>
              <BedDouble size={18} color={c.primary}/><Text style={[font.label, { color: c.textMuted }]}>{copy.rooms}</Text>
            </View>
            {shownRooms.map(room => <View key={room.id} style={{ height: ROW_HEIGHT, justifyContent: 'center', paddingRight: 6, borderBottomWidth: 1, borderColor: c.border }}>
              <Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{room.code}</Text>
              <Text style={[font.small, { color: room.operational_state === 'TECH_BLOCK' ? c.danger : c.textMuted }]} numberOfLines={2}>{roomState(room)}</Text>
            </View>)}
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator accessibilityLabel={copy.pms}>
            <View>
              <View style={{ flexDirection: 'row', height: 46, alignItems: 'center' }}>
                {dates.map(date => <View key={date} style={{ width: CELL_WIDTH, alignItems: 'center', paddingVertical: 7, borderRadius: radius.sm, backgroundColor: date === localDate() ? c.primarySoft : 'transparent' }}>
                  <Text style={[font.small, { color: date === localDate() ? c.primary : c.text, fontWeight: '800' }]}>{date.slice(5)}</Text>
                  <Text style={[font.label, { color: c.textMuted }]}>{pmsWeekdayLabels[locale][new Date(date + 'T12:00:00').getDay()]}</Text>
                </View>)}
              </View>
              {shownRooms.map(room => <View key={room.id} style={{ flexDirection: 'row', height: ROW_HEIGHT, alignItems: 'center', borderBottomWidth: 1, borderColor: c.border }}>
                {dates.map(date => cell(room, date))}
              </View>)}
            </View>
          </ScrollView>
        </View>
      </GlassCard>
      {shownRooms.length === 0 ? <Empty text={filter === 'attention' ? copy.empty : copy.noRooms}/> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        <Badge label={'● ' + copy.bookings} tone="primary"/>
        <Badge label={'H ' + copy.holds} tone="warning"/>
        <Badge label={'— ' + copy.available} tone="neutral"/>
        <Badge label={'× ' + copy.blocked} tone="danger"/>
        <Badge label={'! ' + copy.conflict} tone="danger"/>
      </View>
      <SectionLabel>{copy.bookings}</SectionLabel>
      {shownRooms.flatMap(room => room.blocks.filter(b => b.type === 'RESERVATION' && b.reservation_id).map(b => ({room, b}))).slice(0,24).map(({room,b}) =>
        <GlassCard key={b.id} onPress={!showroom && b.reservation_id && user?.role !== 'AGENT' ? () => router.push({ pathname:'/reservation/[id]', params:{id:b.reservation_id!} }) : undefined}>
          <Text style={[font.h2, { color:c.text }]}>{room.code} · {b.booking_number || '—'}</Text>
          <Text style={[font.small, { color:c.textMuted }]}>{b.start} → {b.end} · {b.guest_name || copy.readOnly}</Text>
        </GlassCard>)}

    </> : null}
    <PmsBookingSheet selected={selectedBlock} showroom={showroom} live={live}
      canOpenDetails={!!user && user.role !== 'AGENT' && allowed}
      onClose={() => setSelectedBlock(null)}
      onOpen={reservationId => router.push({ pathname: '/reservation/[id]', params: { id: reservationId } })}/>
  </FutureScreen>;
}
