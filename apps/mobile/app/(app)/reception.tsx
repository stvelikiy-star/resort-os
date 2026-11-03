import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronRight } from 'lucide-react-native';
import { Badge, Empty, SectionLabel } from '../../src/components/ui';
import { AIOrb, ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { useLiveModules, ReceptionList } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useSession } from '../../src/state/session';
import { useAsync } from '../../src/lib/useAsync';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function Reception() {
  const { user, hotel } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const { data, loading, error, reload } = useAsync<ReceptionList | null>(() => live ? live.reception() : Promise.resolve(null), [live, user?.id]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const arrivals = (data?.items ?? []).filter(x => x.checkIn === data?.local_date && x.status === 'GUARANTEED');
  const departures = (data?.items ?? []).filter(x => x.checkOut === data?.local_date && x.status === 'CHECKED_IN');
  const item = (x: ReceptionList['items'][number]) => <GlassCard key={x.id} testID={'reservation-' + x.id}
    onPress={() => router.push({ pathname: '/reservation/[id]', params: { id: x.id } })}>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={[font.h2, { color: c.text }]}>{x.firstName || x.bookingNumber}</Text>
        <Text style={[font.small, { color: c.textMuted }]}>{x.bookingNumber} · {x.room_code || '—'}</Text>
        <Text style={[font.small, { color: c.textMuted }]}>{x.checkIn} → {x.checkOut}</Text>
        <Badge label={x.status} tone={x.room_state === 'TECH_BLOCK' || x.room_state === 'DIRTY' ? 'danger' : 'primary'} />
      </View>
      <ChevronRight color={c.primary} size={24}/>
    </View>
  </GlassCard>;
  return <FutureScreen>
    <PremiumHeader title={copy.reception} subtitle={hotel?.name} eyebrow="MARINA SMART" right={live ? <AIOrb label="MARINA AI" size={44} onPress={() => router.push('/ai')}/> : null}/>
    {!live ? <Empty text={copy.unavailable} /> : null}
    {loading && live ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <GlassCard style={{ gap: 8 }}><CalendarDays size={28} color={c.primary}/><Text style={[font.h2, { color: c.text }]}>{data.local_date}</Text>
        <Text style={[font.body, { color: c.textMuted }]}>{copy.arrivals}: {arrivals.length} · {copy.departures}: {departures.length}</Text></GlassCard>
      <SectionLabel>{copy.arrivals}</SectionLabel>
      {arrivals.length ? arrivals.map(item) : <Empty text={copy.empty}/>}
      <SectionLabel>{copy.departures}</SectionLabel>
      {departures.length ? departures.map(item) : <Empty text={copy.empty}/>}
      <SectionLabel>{copy.bookings} · {data.items.length}</SectionLabel>
      {data.items.filter(x => !arrivals.includes(x) && !departures.includes(x)).map(item)}
    </> : null}
  </FutureScreen>;
}
