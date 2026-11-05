import React, { useCallback, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, Plus, BedDouble } from 'lucide-react-native';
import { Badge, Button, Empty, PressScale, SectionLabel, Segmented, DemoBanner } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { Grid, GridRoom, localDate, useLiveModules } from '../../src/api/liveModules';
import { CONFIRMED_BACKEND_FEATURES } from '../../src/api/features';
import { canOpenPmsReservation, pmsCellState } from '../../src/roles/pmsPresentation';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { demoGrid } from '../../src/api/demoPresentation';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius } from '../../src/theme/tokens';

function dayAt(start: string, offset: number): string {
  const d = new Date(start + 'T12:00:00'); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
const DAYS = 7, CELL_WIDTH = 72, ROW_HEIGHT = 76, LABEL_WIDTH = 104;
const DAY_NAMES = {
  ru: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  kg: ['Жек', 'Дүй', 'Шей', 'Шар', 'Бей', 'Жум', 'Ише'],
  en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  kz: ['Жс', 'Дс', 'Сс', 'Ср', 'Бс', 'Жм', 'Сб'],
} as const;
export default function Pms() {
  const { hotel, user, locale, api } = useSession();
  const showroom = api?.mode === 'DEMO';
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const [start, setStart] = useState(() => localDate());
  const [filter, setFilter] = useState<'all' | 'attention'>('all');
  const { data, loading, error, reload } = useAsync<Grid | null>(async () => showroom && api ? demoGrid(locale, await api.listRooms(), hotel?.name ?? 'DEMO') : live ? live.pmsGrid(start, dayAt(start, DAYS)) : null, [live, api, showroom, user?.id, start, locale, hotel?.id]);
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
    const label = state === 'RESERVATION' ? '●' : state === 'HOLD' ? 'H'
      : state === 'BLOCKED' ? '×' : state === 'CONFLICT' ? '!' : '—';
    const semantic = state === 'RESERVATION' ? copy.bookings : state === 'HOLD' ? copy.holds
      : state === 'BLOCKED' ? copy.blocked : state === 'CONFLICT' ? copy.conflict : copy.available;
    const canOpen = !showroom && canOpenPmsReservation(blocks, day, user?.role);
    return <PressScale key={day} testID={'pms-' + room.id + '-' + day}
      accessibilityLabel={room.code + ' ' + day + ' · ' + semantic}
      disabled={!canOpen} dimWhenDisabled={false} onPress={() => { if (canOpen) router.push({ pathname: '/reservation/[id]', params: { id: block.reservation_id! } }); }}
      style={{ width: CELL_WIDTH - 4, height: ROW_HEIGHT - 6, marginRight: 4, borderRadius: radius.sm, backgroundColor: tone, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: state === 'RESERVATION' ? tone : c.border }}>
      <Text style={[font.h2, { color: ink }]}>{label}</Text>
    </PressScale>;
  };
  const roomState = (room: GridRoom) =>
    room.operational_state === 'CLEAN' ? copy.clean : room.operational_state === 'DIRTY' ? copy.dirty
      : room.operational_state === 'TECH_BLOCK' ? copy.tech : room.operational_state === 'IN_INSPECTION' ? copy.checking : room.operational_state;
  return <FutureScreen>
    <PremiumHeader title={copy.pms} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    {live && user && ['OWNER','MANAGER','AGENT'].includes(user.role) ? <Button testID="pms-new-booking" label={copy.newBooking} icon={Plus} onPress={() => router.push('/new-booking')}/> : null}
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
                  <Text style={[font.label, { color: c.textMuted }]}>{DAY_NAMES[locale][new Date(date + 'T12:00:00').getDay()]}</Text>
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
  </FutureScreen>;
}
