import React, { useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ChevronLeft, KeyRound } from 'lucide-react-native';
import { Badge, Button, Card, Empty, PressScale, Screen, Title } from '../../src/components/ui';
import { useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function ReservationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const { data, loading, error, reload } = useAsync<Record<string, unknown> | null>(() => live && id ? live.reservation(id) : Promise.resolve(null), [live, id, user?.id]);
  const act = (kind: 'in' | 'out') => Alert.alert(copy.confirm, '', [{ text: copy.close, style: 'cancel' }, { text: copy.choose, onPress: async () => {
    if (locked.current || !live || !id) return;
    locked.current = true; setBusy(true); setFeedback(null);
    try { await (kind === 'in' ? live.checkIn(id) : live.checkOut(id)); setFeedback(copy.confirmed); await reload(); }
    catch { setFeedback(copy.unknown); /* unknown outcome must never auto-retry */ }
    finally { locked.current = false; setBusy(false); }
  }}]);
  if (!user || !['OWNER','MANAGER','RECEPTION'].includes(user.role) || !user.module_permissions?.includes('RESERVATIONS'))
    return <Screen><Empty text={copy.denied}/></Screen>;
  const x = data ?? {};
  const text = (k: string) => typeof x[k] === 'string' || typeof x[k] === 'number' ? String(x[k]) : '—';
  return <Screen>
    <PressScale onPress={() => router.back()} style={{ minHeight: 44, flexDirection: 'row', gap: 5, alignItems: 'center' }}><ChevronLeft color={c.primary} size={22}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <Title>{copy.bookings} · {text('bookingNumber')}</Title>
    {loading ? <Empty text={copy.loading}/> : null}
    {error ? <Card onPress={reload}><Text accessibilityRole="alert" style={[font.body, { color: c.danger }]}>{error.message} · {copy.retry}</Text></Card> : null}
    {data ? <>
      <Card style={{ gap: 10 }}>
        <View style={{ flexDirection: 'row', gap: space.md, alignItems: 'center' }}><KeyRound size={24} color={c.primary}/><Text style={[font.h2, { color: c.text }]}>{text('firstName')} {text('lastName')}</Text></View>
        <Badge label={text('status')} tone="info"/>
        <Text style={[font.body, { color: c.text }]}>{text('checkIn')} → {text('checkOut')}</Text>
        <Text style={[font.body, { color: c.textMuted }]}>{text('phone')}</Text>
      </Card>
      {text('status') === 'GUARANTEED' ? <Button testID="reservation-checkin" label={copy.checkIn} disabled={busy} onPress={() => act('in')}/> : null}
      {text('status') === 'CHECKED_IN' ? <Button testID="reservation-checkout" label={copy.checkOut} disabled={busy} onPress={() => act('out')}/> : null}
      <Text style={[font.small, { color: c.textMuted }]}>{copy.readOnly} · {copy.paymentsNotProfit}</Text>
      {feedback ? <Card><Text accessibilityRole="alert" style={[font.body, { color: c.text }]}>{feedback}</Text></Card> : null}
    </> : null}
  </Screen>;
}
