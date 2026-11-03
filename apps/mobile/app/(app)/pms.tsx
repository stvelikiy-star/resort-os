import React, { useCallback, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, Plus, BedDouble } from 'lucide-react-native';
import { Badge, Button, Empty, PressScale, SectionLabel } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { Grid, GridRoom, localDate, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius } from '../../src/theme/tokens';

function dayAt(start: string, offset: number): string {
  const d = new Date(start + 'T12:00:00'); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
const DAYS = 7, CELL_WIDTH = 68, ROW_HEIGHT = 66, LABEL_WIDTH = 92;
export default function Pms() {
  const { hotel, user } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const [start, setStart] = useState(() => localDate());
  const { data, loading, error, reload } = useAsync<Grid | null>(() => live ? live.pmsGrid(start, dayAt(start, DAYS)) : Promise.resolve(null), [live, user?.id, start]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const dates = Array.from({ length: DAYS }, (_, i) => dayAt(start, i));
  const occupancyFor = (room: GridRoom, day: string) => room.blocks.filter(b => b.start <= day && day < b.end);
  const cell = (room: GridRoom, day: string) => {
    const blocks = occupancyFor(room, day);
    const block = blocks[0];
    const clash = blocks.length > 1;
    const booked = block?.type === 'RESERVATION';
    const filled = !!block || clash;
    const tone = clash ? c.danger : booked ? c.primary : filled ? c.warning : c.surfaceAlt;
    const label = clash ? '!' : filled ? booked ? '●' : 'H' : '—';
    const semantic = clash ? copy.conflict : !block ? copy.available : booked ? copy.bookings : copy.holds;
    const canOpen = !clash && !!block?.reservation_id && user?.role !== 'AGENT';
    return <PressScale key={day} testID={'pms-' + room.id + '-' + day}
      accessibilityLabel={room.code + ' ' + day + ' · ' + semantic}
      disabled={!canOpen} onPress={() => { if (canOpen) router.push({ pathname: '/reservation/[id]', params: { id: block.reservation_id! } }); }}
      style={{ width: CELL_WIDTH - 4, height: ROW_HEIGHT - 6, marginRight: 4, borderRadius: radius.sm, backgroundColor: tone, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: filled ? tone : c.border }}>
      <Text style={[font.h2, { color: filled ? booked ? c.primaryText : c.bg : c.textMuted }]}>{label}</Text>
    </PressScale>;
  };
  const roomState = (room: GridRoom) =>
    room.operational_state === 'CLEAN' ? copy.clean : room.operational_state === 'DIRTY' ? copy.dirty
      : room.operational_state === 'TECH_BLOCK' ? copy.tech : room.operational_state;
  return <FutureScreen>
    <PremiumHeader title={copy.pms} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    {live && user && ['OWNER','MANAGER','AGENT'].includes(user.role) ? <Button testID="pms-new-booking" label={copy.newBooking} icon={Plus} onPress={() => router.push('/new-booking')}/> : null}
    {live && user && ['OWNER','MANAGER'].includes(user.role) ? <Button testID="pms-holds" variant="secondary" label={copy.holds} icon={Clock3} onPress={() => router.push('/holds')}/> : null}
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
    {!live ? <Empty text={copy.unavailable}/> : null}
    {loading && live ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <SectionLabel>{copy.available} · {data.rooms.length}</SectionLabel>
      <GlassCard style={{ padding: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
          <View style={{ width: LABEL_WIDTH, flexShrink: 0 }}>
            <View style={{ height: 46, flexDirection: 'row', alignItems: 'center', gap: 4 }}>
              <BedDouble size={18} color={c.primary}/><Text style={[font.label, { color: c.textMuted }]}>{copy.rooms}</Text>
            </View>
            {data.rooms.map(room => <View key={room.id} style={{ height: ROW_HEIGHT, justifyContent: 'center', paddingRight: 6, borderBottomWidth: 1, borderColor: c.border }}>
              <Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{room.code}</Text>
              <Text style={[font.small, { color: room.operational_state === 'TECH_BLOCK' ? c.danger : c.textMuted }]} numberOfLines={1}>{roomState(room)}</Text>
            </View>)}
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator accessibilityLabel={copy.pms}>
            <View>
              <View style={{ flexDirection: 'row', height: 46, alignItems: 'center' }}>
                {dates.map(date => <View key={date} style={{ width: CELL_WIDTH, alignItems: 'center' }}>
                  <Text style={[font.small, { color: c.text, fontWeight: '700' }]}>{date.slice(5)}</Text>
                </View>)}
              </View>
              {data.rooms.map(room => <View key={room.id} style={{ flexDirection: 'row', height: ROW_HEIGHT, alignItems: 'center', borderBottomWidth: 1, borderColor: c.border }}>
                {dates.map(date => cell(room, date))}
              </View>)}
            </View>
          </ScrollView>
        </View>
      </GlassCard>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        <Badge label={'● ' + copy.bookings} tone="primary"/>
        <Badge label={'H ' + copy.holds} tone="warning"/>
        <Badge label={'— ' + copy.available} tone="neutral"/>
        <Badge label={'! ' + copy.conflict} tone="danger"/>
      </View>
      <SectionLabel>{copy.bookings}</SectionLabel>
      {data.rooms.flatMap(room => room.blocks.filter(b => b.reservation_id).map(b => ({room, b}))).slice(0,24).map(({room,b}) =>
        <GlassCard key={b.id} onPress={() => { if (b.reservation_id && user?.role !== 'AGENT') router.push({ pathname:'/reservation/[id]', params:{id:b.reservation_id} }); }}>
          <Text style={[font.h2, { color:c.text }]}>{room.code} · {b.booking_number || '—'}</Text>
          <Text style={[font.small, { color:c.textMuted }]}>{b.start} → {b.end} · {b.guest_name || copy.readOnly}</Text>
        </GlassCard>)}
      {data.rooms.length === 0 ? <Empty text={copy.noRooms}/> : null}
    </> : null}
  </FutureScreen>;
}
