import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { ChevronLeft, Wallet, Clock3, Landmark, BedDouble } from 'lucide-react-native';
import { PressScale, Empty, SectionLabel } from '../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, MetricCard, PremiumHeader } from '../src/components/Future';
import { useSession } from '../src/state/session';
import { useLiveModules, localDate } from '../src/api/liveModules';
import { canReadFinance } from '../src/api/financeAccess';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { OWNER_FINANCE_COPY } from '../src/i18n/extendedOperations';
import { useAsync } from '../src/lib/useAsync';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

/** Only amounts verified in the exact hotel Core report are displayed.
 * Incoming payments are not earnings; this is NOT a P&L or tax report. */
export default function Finance() {
  const { user, hotel, api, locale } = useSession();
  const copy = useMobileCopy();
  const extra = OWNER_FINANCE_COPY[locale];
  const { c } = useTheme();
  const router = useRouter();
  const modules = useLiveModules();
  const allowed = api?.mode === 'LIVE' && canReadFinance(user);
  const from = localDate(-29), to = localDate();
  const { data, loading, error, reload } = useAsync(
    () => allowed && modules ? modules.financeSummary(from, to) : Promise.resolve(null),
    [modules, allowed, hotel?.id, user?.id, user?.module_permissions?.join(',')],
  );
  const focused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (focused.current) void reload(); else focused.current = true;
  }, [reload]));
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  const money = (v: number) => Number(v).toLocaleString('ru-RU') + ' ' + (data?.range.currency || 'KGS');
  const line = (label: string, amount: string, caption?: string) =>
    <View key={label} style={{ flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:12,paddingVertical:8,
      borderBottomWidth:1,borderBottomColor:c.border }}>
      <View style={{flex:1,minWidth:0,gap:3}}>
        <Text style={[font.body,{color:c.text}]}>{label}</Text>
        {caption ? <Text style={[font.small,{color:c.textMuted}]}>{caption}</Text> : null}
      </View>
      <Text style={[font.body,{color:c.text,fontWeight:'700',textAlign:'right'}]}>{amount}</Text>
    </View>;
  return <FutureScreen>
    <PressScale accessibilityLabel={copy.close} onPress={() => router.back()}
      style={{ minHeight:44,flexDirection:'row',alignItems:'center',gap:6 }}>
      <ChevronLeft color={c.primary} size={22}/><Text style={[font.body,{color:c.primary}]}>{copy.close}</Text>
    </PressScale>
    <PremiumHeader title={copy.financeTitle} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    <GlassCard><Text style={[font.body,{color:c.textMuted}]}>{copy.financeRange}: {from} — {to}</Text></GlassCard>
    {loading ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {!modules && !loading ? <Empty text={copy.unavailable}/> : null}
    {data ? <>
      <View style={{ flexDirection:'row',flexWrap:'wrap',gap:space.md }}>
        <MetricCard icon={Wallet} tone="success" label={copy.financeReceived} value={money(data.period_payments.received_kgs)}/>
        <MetricCard icon={Clock3} tone="warning" label={copy.financePending} value={money(data.period_payments.pending_created_kgs)}/>
        <MetricCard icon={Landmark} tone="warning" label={copy.financeDebt} value={money(data.receivables_snapshot.outstanding_kgs)}/>
        <MetricCard icon={BedDouble} tone="cyan" label={copy.financeActive} value={money(data.active_reservations_snapshot.outstanding_kgs)}/>
      </View>
      <GlassCard style={{gap:space.sm}}>
        {line(copy.financeCount,String(data.period_payments.received_count))}
        {line(copy.financeDebtors,String(data.receivables_snapshot.debtor_count))}
        {line(extra.activeBookings,String(data.active_reservations_snapshot.reservation_count))}
        {data.active_reservations_snapshot.booked_total_kgs !== undefined ?
          line(extra.bookingTotal,money(data.active_reservations_snapshot.booked_total_kgs)) : null}
        {data.active_reservations_snapshot.received_kgs !== undefined ?
          line(extra.bookingReceived,money(data.active_reservations_snapshot.received_kgs)) : null}
      </GlassCard>
      {data.receivables_snapshot.checked_out_kgs !== undefined &&
        data.receivables_snapshot.in_house_kgs !== undefined &&
        data.receivables_snapshot.pre_arrival_kgs !== undefined ? <>
        <SectionLabel>{extra.debtStages}</SectionLabel>
        <GlassCard style={{gap:5}}>
          {line(extra.checkedOut,money(data.receivables_snapshot.checked_out_kgs),
            String(data.receivables_snapshot.checked_out_count) + ' ' + extra.activeBookings)}
          {line(extra.inHouse,money(data.receivables_snapshot.in_house_kgs),
            String(data.receivables_snapshot.in_house_count) + ' ' + extra.activeBookings)}
          {line(extra.beforeArrival,money(data.receivables_snapshot.pre_arrival_kgs),
            String(data.receivables_snapshot.pre_arrival_count) + ' ' + extra.activeBookings)}
        </GlassCard>
      </> : null}
      {data.awaiting_prepayment_snapshot ? <>
        <SectionLabel>{extra.prepayment}</SectionLabel>
        <GlassCard style={{gap:5}}>
          {line(extra.requests,String(data.awaiting_prepayment_snapshot.request_count))}
          {line(extra.balance,money(data.awaiting_prepayment_snapshot.remaining_kgs))}
        </GlassCard>
      </> : null}
      {data.finance_exceptions || data.refunded_snapshot_all_time ? <>
        <SectionLabel>{extra.exceptions}</SectionLabel>
        <GlassCard style={{gap:5}}>
          {data.finance_exceptions ?
            <>
              {line(extra.overpaid,money(data.finance_exceptions.snapshot.overpaid_kgs),
                String(data.finance_exceptions.snapshot.overpaid_count))}
              {line(extra.cancelledPaid,money(data.finance_exceptions.snapshot.cancelled_with_received_kgs),
                String(data.finance_exceptions.snapshot.cancelled_with_received_count))}
            </> : null}
          {data.refunded_snapshot_all_time ?
            line(extra.refunded,money(data.refunded_snapshot_all_time.amount_kgs),
              String(data.refunded_snapshot_all_time.payment_count)) : null}
        </GlassCard>
      </> : null}
      {data.received_by_method ? <>
        <SectionLabel>{extra.methods}</SectionLabel>
        {data.received_by_method.length ? <GlassCard style={{gap:5}}>
          {data.received_by_method.map(row => line(row.method,money(row.amount_kgs),
            String(row.payment_count)+' '+extra.payments))}
        </GlassCard> : <Empty text={extra.noPayments}/>}
      </> : null}
      {data.received_by_day ? <>
        <SectionLabel>{extra.daily}</SectionLabel>
        {data.received_by_day.length ? <GlassCard style={{gap:5}}>
          {data.received_by_day.slice(-10).reverse().map(row => line(row.local_date,money(row.amount_kgs),
            String(row.payment_count)+' '+extra.payments))}
        </GlassCard> : <Empty text={extra.noPayments}/>}
      </> : null}
      {data.debtors ? <>
        <SectionLabel>{extra.debtors} · {data.receivables_snapshot.debtor_count}</SectionLabel>
        {data.debtors.length ? <GlassCard style={{gap:5}}>
          {data.debtors.slice(0,10).map(row => line(row.booking_number + (row.room_code ? ' · '+row.room_code : ''),
            money(row.remaining_kgs),row.guest_name || row.status))}
        </GlassCard> : <Empty text={extra.noDebtors}/>}
      </> : null}
      {data.recent_payments ? <>
        <SectionLabel>{extra.recent}</SectionLabel>
        {data.recent_payments.length ? <GlassCard style={{gap:5}}>
          {data.recent_payments.slice(0,10).map(row => line(row.booking_number || row.id.slice(0,8),
            money(row.amount_kgs),row.status+' · '+row.method))}
        </GlassCard> : <Empty text={extra.noPayments}/>}
      </> : null}
      {!data.received_by_method && !data.awaiting_prepayment_snapshot ?
        <GlassCard><Text style={[font.small,{color:c.textMuted}]}>{extra.noExtra}</Text></GlassCard> : null}
      <GlassCard><Text style={[font.small,{color:c.textMuted}]}>{extra.notProfit} {copy.financeDisclaimer}</Text></GlassCard>
    </> : null}
  </FutureScreen>;
}