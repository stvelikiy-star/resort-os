import React, { useCallback, useRef, useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react-native';
import { Badge, Card, Empty, PressScale, Screen, SectionLabel, Title } from '../../src/components/ui';
import { Grid, GridRoom, localDate, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

function dayAt(start: string, offset: number): string {
  const d = new Date(start + 'T12:00:00'); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
export default function Pms() {
  const { hotel, user } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const [start, setStart] = useState(() => localDate());
  const { data, loading, error, reload } = useAsync<Grid | null>(() => live ? live.pmsGrid(start, dayAt(start, 7)) : Promise.resolve(null), [live, user?.id, start]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const dates = Array.from({ length: 7 }, (_, i) => dayAt(start, i));
  const cols = 76, rowHeight = 58;
  const roomCell = (room: GridRoom, day: string) => {
    const block = room.blocks.find(b => b.start <= day && day < b.end);
    const occupied = Boolean(block);
    const color = occupied ? c.primary : c.surfaceAlt;
    const label = occupied ? (block!.type === 'RESERVATION' ? '●' : 'H') : '·';
    return <PressScale key={day} testID={'pms-' + room.id + '-' + day} onPress={() => {
      if (block?.reservation_id) router.push({ pathname: '/reservation/[id]', params: { id: block.reservation_id } });
    }} style={{ width: cols - 4, height: rowHeight - 4, marginRight: 4, borderRadius: radius.sm, backgroundColor: color, justifyContent: 'center', alignItems: 'center' }}>
      <Text style={[font.body, { color: occupied ? '#fff' : c.textMuted }]}>{label}</Text>
    </PressScale>;
  };
  return <Screen>
    <Title sub={hotel?.name}>{copy.pms}</Title>
    {!live ? <Empty text={copy.unavailable} /> : null}
    <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center' }}>
      <PressScale testID="pms-prev" onPress={() => setStart(dayAt(start, -7))} style={{ minHeight: 48, minWidth: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: c.surface, borderRadius: radius.md }}><ChevronLeft color={c.primary} size={24}/></PressScale>
      <View style={{ flex: 1, alignItems: 'center' }}><Text style={[font.h2, { color: c.text }]}>{start} — {dayAt(start, 6)}</Text></View>
      <PressScale testID="pms-next" onPress={() => setStart(dayAt(start, 7))} style={{ minHeight: 48, minWidth: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: c.surface, borderRadius: radius.md }}><ChevronRight color={c.primary} size={24}/></PressScale>
      <PressScale testID="pms-today" onPress={() => setStart(localDate())} style={{ minHeight: 48, minWidth: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: c.primarySoft, borderRadius: radius.md }}><CalendarDays color={c.primary} size={23}/></PressScale>
    </View>
    {loading && live ? <Empty text={copy.loading} /> : null}
    {error ? <Card onPress={reload}><Text accessibilityRole="alert" style={[font.body, { color: c.danger }]}>{error.message} · {copy.retry}</Text></Card> : null}
    {data ? <>
      <Card style={{ gap: 8, paddingHorizontal: 12 }}>
        <SectionLabel>{copy.available} · {data.rooms.length}</SectionLabel>
        <ScrollView horizontal showsHorizontalScrollIndicator accessibilityLabel={copy.pms}>
          <View>
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 5 }}>
              <View style={{ width: 104 }}><Text style={[font.small, { color: c.textMuted }]}>{copy.rooms}</Text></View>
              {dates.map(d => <View key={d} style={{ width: cols, alignItems: 'center', paddingVertical: 8 }}><Text style={[font.small, { color: c.text }]}>{d.slice(5)}</Text></View>)}
            </View>
            {data.rooms.map(room => <View key={room.id} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
              <View style={{ width: 104, paddingRight: 6 }}><Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{room.code}</Text>
                <Text style={[font.small, { color: room.operational_state === 'TECH_BLOCK' ? c.danger : c.textMuted }]} numberOfLines={1}>{room.operational_state}</Text>
              </View>
              {dates.map(date => roomCell(room, date))}
            </View>)}
          </View>
        </ScrollView>
      </Card>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}><Badge label="● Reservation" tone="primary"/><Badge label="H HOLD" tone="warning"/><Badge label="· Free" tone="neutral"/></View>
      <SectionLabel>{copy.bookings}</SectionLabel>
      {data.rooms.flatMap(r => r.blocks.filter(b => b.reservation_id).map(b => ({ r, b }))).slice(0, 30).map(({r,b}) =>
        <Card key={b.id} onPress={() => { if (b.reservation_id) router.push({ pathname: '/reservation/[id]', params: { id: b.reservation_id } }); }}>
          <Text style={[font.h2, { color: c.text }]}>{r.code} · {b.booking_number || '—'}</Text>
          <Text style={[font.small, { color: c.textMuted }]}>{b.start} → {b.end} · {b.guest_name || copy.readOnly}</Text>
        </Card>)}
      {data.rooms.length === 0 ? <Empty text={copy.noRooms}/> : null}
      <Text style={[font.small, { color: c.textMuted }]}>{copy.readOnly} · {copy.senderBlocked === '' ? '' : 'PMS'}</Text>
    </> : null}
  </Screen>;
}
