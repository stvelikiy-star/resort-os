import React, { useCallback, useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { ChefHat, UtensilsCrossed } from 'lucide-react-native';
import { Badge, Button, Empty, SectionLabel } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { DiningFloor, KitchenOrder, KitchenStatus, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useSession } from '../../src/state/session';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

const NEXT: Partial<Record<KitchenStatus, KitchenStatus>> = { NEW: 'ACCEPTED', ACCEPTED: 'COOKING', COOKING: 'READY' };
export default function Dining() {
  const { user, hotel } = useSession();
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const cook = user?.role === 'COOK';
  const waiter = user?.role === 'WAITER';
  const { data, loading, error, reload } = useAsync<KitchenOrder[] | DiningFloor | null>(() => live ? cook ? live.kitchenOrders() : live.diningFloor() : Promise.resolve(null), [live, cook, user?.id]);
  const focused = useRef(false);
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const orders = Array.isArray(data) ? data : (data?.orders ?? []);
  const floor = !Array.isArray(data) && data ? data : null;
  const change = (run: () => Promise<unknown>) => Alert.alert(copy.confirm, '', [{text: copy.close, style:'cancel'}, {text: copy.choose, onPress: async () => {
    if (locked.current || unknownResult) return;
    locked.current = true; setBusy(true);
    try {
      await run();
      try { await reload(); }
      catch { Alert.alert(copy.confirmed, copy.retry); } // write was ACKed, only refresh failed
    } catch (e: unknown) {
      const rejected = wasWriteRejected(e);
      if (!rejected) setUnknownResult(true);
      Alert.alert(rejected ? copy.conflict : copy.resultUnknown);
    } finally { locked.current = false; setBusy(false); }
  }}]);
  if (!user || !user.module_permissions?.includes('DINING') || !['COOK','WAITER','OWNER','MANAGER'].includes(user.role))
    return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.dining} subtitle={hotel?.name} eyebrow="MARINA SMART" right={cook ? <ChefHat size={27} color={c.primary}/> : <UtensilsCrossed size={27} color={c.primary}/>}/>
    {!live ? <Empty text={copy.unavailable}/> : null}
    {unknownResult ? <GlassCard testID="dining-unknown-result"><Text accessibilityRole="alert" style={[font.body, { color: c.warning }]}>{copy.resultUnknown}</Text></GlassCard> : null}
    {loading && live ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {floor ? <><SectionLabel>{copy.tables}</SectionLabel><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>{floor.tables.map(t => <GlassCard key={t.id} style={{ width: '47%' }}><Text style={[font.h2, { color: c.text }]}>{t.code}</Text><Text style={[font.small, { color: c.textMuted }]}>{t.status} · {t.seats}</Text></GlassCard>)}</View></> : null}
    <SectionLabel>{copy.orders} · {orders.length}</SectionLabel>
    {orders.map((o,i) => <StaggerItem key={o.id} index={i}><GlassCard testID={'order-' + o.id} style={{ gap: 8 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}><Text style={[font.h2, { color: c.text }]}>{o.order_number}</Text><Badge label={o.status} tone={o.status === 'READY' ? 'success' : 'info'}/></View>
      <Text style={[font.body, { color: c.textMuted }]}>{o.table_code || o.room_code || '—'}</Text>
      {'notes' in o && o.notes ? <Text style={[font.small, { color: c.text }]}>{o.notes}</Text> : null}
      {cook && NEXT[o.status as KitchenStatus] ? <Button testID={'order-next-' + o.id} label={NEXT[o.status as KitchenStatus]!} disabled={busy || unknownResult} onPress={() => change(() => live!.kitchenStatus(o.id, NEXT[o.status as KitchenStatus]!))}/> : null}
      {waiter && !('waiter_id' in o && o.waiter_id) ? <Button testID={'waiter-claim-' + o.id} label={copy.take} disabled={busy || unknownResult} onPress={() => change(() => live!.claimWaiterOrder(o.id, user.id))}/> : null}
      {waiter && o.status === 'READY' ? <Text style={[font.small, { color: c.warning }]}>{copy.status}: READY · {copy.readOnly}</Text> : null}
    </GlassCard></StaggerItem>)}
    {!loading && !error && orders.length === 0 ? <Empty text={copy.empty}/> : null}
  </FutureScreen>;
}
