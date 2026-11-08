import React, { useCallback, useRef, useState } from 'react';
import { Alert, Text, View, useWindowDimensions } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { ChefHat, UtensilsCrossed, Clock3, CheckCircle2 } from 'lucide-react-native';
import { Badge, Button, Empty, SectionLabel, DemoBanner } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { DiningFloor, KitchenOrder, KitchenStatus, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { kitchenItemName } from '../../src/i18n/kitchenLabels';
import { orderStatusLabel, diningTableStatusLabel } from '../../src/i18n/statusLabels';
import { demoDiningFloor, demoKitchenOrders } from '../../src/api/demoPresentation';
import { useSession } from '../../src/state/session';
import { hasTabForSession } from '../../src/roles/registry';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useTheme } from '../../src/theme/ThemeProvider';
import { WaiterOperations } from '../../src/components/WaiterOperations';
import { font, space } from '../../src/theme/tokens';

const NEXT: Partial<Record<KitchenStatus, KitchenStatus>> = { NEW: 'ACCEPTED', ACCEPTED: 'COOKING', COOKING: 'READY' };
export default function Dining() {
  const { user, hotel, api, locale, serverAuthMode } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'dining', serverAuthMode)
    && ['COOK', 'WAITER', 'OWNER', 'MANAGER'].includes(user.role);
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const singleColumn = width < 365 || fontScale > 1.35;
  const cook = user?.role === 'COOK';
  const waiter = user?.role === 'WAITER';
  const { data, loading, error, reload } = useAsync<KitchenOrder[] | DiningFloor | null>(() => !allowed ? Promise.resolve(null) : showroom ? Promise.resolve(cook ? demoKitchenOrders(locale) : demoDiningFloor(locale)) : live ? cook ? live.kitchenOrders() : live.diningFloor() : Promise.resolve(null), [live, showroom, cook, user?.id, locale, allowed]);
  const focused = useRef(false);
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const orders = Array.isArray(data) ? data : (data?.orders ?? []);
  const floor = !Array.isArray(data) && data ? data : null;
  const orderTone = (status: string) => status === 'READY' ? 'success' as const : status === 'CANCELLED' ? 'danger' as const : status === 'NEW' ? 'warning' as const : status === 'COOKING' ? 'info' as const : 'primary' as const;
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
  if (!allowed)
    return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.dining} subtitle={hotel?.name} eyebrow="MARINA SMART" right={cook ? <ChefHat size={27} color={c.primary}/> : <UtensilsCrossed size={27} color={c.primary}/>}/>
    {showroom ? <DemoBanner/> : null}
    {waiter && live && !showroom && floor ? <WaiterOperations key={hotel?.id + ':' + user.id} live={live} tables={floor.tables} reload={reload}/> : null}
    {!live && !showroom ? <Empty text={copy.unavailable}/> : null}
    {unknownResult ? <GlassCard testID="dining-unknown-result"><Text accessibilityRole="alert" style={[font.body, { color: c.warning }]}>{copy.resultUnknown}</Text></GlassCard> : null}
    {loading && (live || showroom) ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {floor ? <><SectionLabel>{copy.tables}</SectionLabel><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>{floor.tables.map(t => <GlassCard key={t.id} style={{ width: singleColumn ? '100%' : '47%', gap: 6 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}><UtensilsCrossed size={21} color={c.primary}/><Text style={[font.h2, { color: c.text, flex: 1 }]}>{t.code}</Text></View>
      <Badge label={diningTableStatusLabel(t.status, copy)} tone={t.status === 'AVAILABLE' || t.status === 'FREE' ? 'success' : t.status === 'OCCUPIED' ? 'warning' : t.status === 'RESERVED' ? 'info' : 'neutral'}/>
      <Text style={[font.small, { color: c.textMuted }]}>{t.seats}</Text>
    </GlassCard>)}</View></> : null}
    <SectionLabel>{copy.orders} · {orders.length}</SectionLabel>
    {orders.map((o,i) => <StaggerItem key={o.id} index={i}><GlassCard testID={'order-' + o.id} style={{ gap: 10, borderLeftWidth: 4, borderLeftColor: o.status === 'NEW' ? c.warning : o.status === 'READY' ? c.success : o.status === 'CANCELLED' ? c.danger : c.primary }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}><Text style={[font.h2, { color: c.text }]}>{o.order_number}</Text><Badge label={orderStatusLabel(o.status, copy)} tone={orderTone(o.status)}/></View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}><Clock3 size={17} color={c.textMuted}/><Text style={[font.body, { color: c.textMuted }]}>{o.table_code || o.room_code || '—'}</Text></View>
      {'items' in o && Array.isArray(o.items) && o.items.length ? <View style={{ gap: 4, borderTopWidth: 1, borderColor: c.border, paddingTop: 10 }}>
        {o.items.map((item, index) => <View key={item.id || index} style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <CheckCircle2 size={15} color={c.cyan}/>
          <Text style={[font.body, { color: c.text, flex: 1 }]}>{typeof item.quantity === 'number' && item.quantity > 0 ? item.quantity + ' × ' : ''}{kitchenItemName(item, locale) || '—'}</Text>
        </View>)}
      </View> : null}
      {'notes' in o && o.notes ? <Text style={[font.small, { color: c.text }]}>{o.notes}</Text> : null}
      {!showroom && cook && NEXT[o.status as KitchenStatus] ? <Button testID={'order-next-' + o.id} label={orderStatusLabel(NEXT[o.status as KitchenStatus]!, copy)} disabled={busy || unknownResult} onPress={() => change(() => live!.kitchenStatus(o.id, NEXT[o.status as KitchenStatus]!))}/> : null}
      {!showroom && waiter && !('waiter_id' in o && o.waiter_id) ? <Button testID={'waiter-claim-' + o.id} label={copy.take} disabled={busy || unknownResult} onPress={() => change(() => live!.claimWaiterOrder(o.id, user.id))}/> : null}
      {waiter && o.status === 'READY' ? <Text style={[font.small, { color: c.warning }]}>{copy.status}: {orderStatusLabel('READY', copy)} · {copy.readOnly}</Text> : null}
    </GlassCard></StaggerItem>)}
    {!loading && !error && orders.length === 0 ? <Empty text={copy.empty}/> : null}
  </FutureScreen>;
}
