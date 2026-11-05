import React from 'react';
import { Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ChevronLeft, Wallet, Clock3, Landmark, BedDouble } from 'lucide-react-native';
import { PressScale, Empty } from '../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, MetricCard, PremiumHeader } from '../src/components/Future';
import { useSession } from '../src/state/session';
import { useLiveModules, localDate } from '../src/api/liveModules';
import { canReadFinance } from '../src/api/financeAccess';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { useAsync } from '../src/lib/useAsync';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

export default function Finance() {
  const { user, hotel, api } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const modules = useLiveModules();
  const allowed = api?.mode === 'LIVE' && canReadFinance(user);
  // A property-local report period is supplied to the server; it applies its
  // own timezone when computing the totals. Never fabricate a financial row.
  const from = localDate(-29), to = localDate();
  const { data, loading, error, reload } = useAsync(
    () => allowed && modules ? modules.financeSummary(from, to) : Promise.resolve(null),
    [modules, allowed, hotel?.id, user?.id, user?.module_permissions?.join(',')],
  );
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  const money = (v: number) => Number(v).toLocaleString('ru-RU') + ' ' + (data?.range.currency || 'KGS');
  return <FutureScreen>
    <PressScale accessibilityLabel={copy.close} onPress={() => router.back()}
      style={{ minHeight: 44, flexDirection: 'row', alignItems: 'center', gap: 6 }}>
      <ChevronLeft color={c.primary} size={22}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text>
    </PressScale>
    <PremiumHeader title={copy.financeTitle} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    <GlassCard><Text style={[font.body, { color: c.textMuted }]}>{copy.financeRange}: {from} — {to}</Text></GlassCard>
    {loading ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {!modules && !loading ? <Empty text={copy.unavailable}/> : null}
    {data ? <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        <MetricCard icon={Wallet} tone="success" label={copy.financeReceived} value={money(data.period_payments.received_kgs)}/>
        <MetricCard icon={Clock3} tone="warning" label={copy.financePending} value={money(data.period_payments.pending_created_kgs)}/>
        <MetricCard icon={Landmark} tone="warning" label={copy.financeDebt} value={money(data.receivables_snapshot.outstanding_kgs)}/>
        <MetricCard icon={BedDouble} tone="cyan" label={copy.financeActive} value={money(data.active_reservations_snapshot.outstanding_kgs)}/>
      </View>
      <GlassCard style={{ gap: space.sm }}>
        <Text style={[font.body, { color: c.text }]}>{copy.financeCount}: {data.period_payments.received_count}</Text>
        <Text style={[font.body, { color: c.text }]}>{copy.financeDebtors}: {data.receivables_snapshot.debtor_count}</Text>
      </GlassCard>
      <Text style={[font.small, { color: c.textMuted }]}>{copy.financeDisclaimer}</Text>
    </> : null}
  </FutureScreen>;
