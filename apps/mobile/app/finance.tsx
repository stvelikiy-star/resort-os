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
import { OwnerExpenses } from '../src/components/OwnerExpenses';
import { font, space } from '../src/theme/tokens';

const KITCHEN_REPORT_COPY={
 ru:{title:'Кухня — себестоимость и закупки',production:'Производственная себестоимость',
  losses:'Порча и потери',waste:'Потери',spoilage:'Порча',stock:'Стоимость остатков по движениям',
  approved:'Утверждённые поставки к приходу',unapproved:'Заявки без утверждения',
  returns:'Возврат поставщику — стоимость товара',gross:'Накладные поставщиков',
  settled:'Оплаты поставщикам (зарегистрированные)',credits:'Кредитовые корректировки',
  outstanding:'Долг поставщикам',legacyDifference:'Расхождение цен старых приходов и накладных',
  returnDifference:'Разница кредита и складской стоимости возвратов',
  reconciliation:'Требуется сверка складских движений или документов',
  notice:'Склад оценён по сохранённым движениям; заявки — предварительные оценки. Накладные, оплаты и возвраты — отдельные записи. Это не подтверждённая прибыль.'},
 kg:{title:'Ашкана — өздүк нарк жана сатып алуулар',production:'Өндүрүштүн өздүк наркы',
  losses:'Бузулуу жана жоготуулар',waste:'Жоготуулар',spoilage:'Бузулуу',
  stock:'Кампанын кыймылдар боюнча баасы',approved:'Бекитилген, бирок келе элек товарлар',
  unapproved:'Бекитиле элек өтүнмөлөр',
  returns:'Жеткирүүчүгө кайтарылган товар баасы',gross:'Жеткирүүчүнүн накладнойлору',
  settled:'Жеткирүүчүгө катталган төлөмдөр',credits:'Кредиттик түзөтүүлөр',
  outstanding:'Жеткирүүчүлөргө карыз',legacyDifference:'Эски кириштер менен накладнойлордун баа айырмасы',
  returnDifference:'Кредит менен кайтарылган товардын нарк айырмасы',
  reconciliation:'Кампа кыймылдарын же документтерди салыштыруу керек',
  notice:'Кампа кыймылдардын наркы менен бааланат, өтүнмөлөр болжолдуу. Бул текшерилген пайда эмес.'},
 en:{title:'Kitchen — costs & procurement',production:'Production cost',
  losses:'Spoilage and waste cost',waste:'Waste',spoilage:'Spoilage',
  stock:'Inventory value from recorded movements',approved:'Approved products not yet received',
  unapproved:'Requests awaiting approval',
  returns:'Supplier returns — stock carrying cost',gross:'Supplier invoice obligations',
  settled:'Recorded supplier settlements',credits:'Supplier credit notes',
  outstanding:'Supplier payables outstanding',
  legacyDifference:'Legacy receipt vs invoice cost difference',
  returnDifference:'Supplier credit vs stock return cost difference',
  reconciliation:'Stock or document reconciliation required',
  notice:'Inventory uses recorded movement values; open requests are estimates. Invoices, settlements and credits are separate facts. Recognized profit is unavailable.'},
 kz:{title:'Асхана — өзіндік құн және сатып алу',production:'Өндіріс шығыны',
  losses:'Бүліну және шығындар',waste:'Шығындар',spoilage:'Бүліну',
  stock:'Қозғалыстар бойынша қойма құны',approved:'Бекітілген, бірақ келмеген өнімдер',
  unapproved:'Бекітілмеген өтінімдер',returns:'Жеткізушіге қайтарылған тауар құны',
  gross:'Жеткізушінің жүкқұжаттары',settled:'Тіркелген жеткізуші төлемдері',
  credits:'Кредиттік түзетулер',outstanding:'Жеткізушілерге берешек',
  legacyDifference:'Ескі кірістер мен жүкқұжат бағасының айырмасы',
  returnDifference:'Кредит пен қайтарылған тауар құнының айырмасы',
  reconciliation:'Қойма жазбаларын немесе құжаттарды салыстыру қажет',
  notice:'Қойма құны тіркелген қозғалыстарға негізделген; өтінімдер бағалау ғана. Бұл расталған пайда емес.'},
} as const;

const CASH_RECONCILIATION_COPY={
 ru:{title:'Сверка зарегистрированных денежных операций',
  received:'Поступления от гостей (записанные)',paid:'Ручные оплаты расходов',
  difference:'Разница зарегистрированных операций',open:'Неоплаченные расходы',
  notice:'Это не прибыль, банковский остаток и не полный денежный поток. Возвраты, незарегистрированные операции и начисления не сверены.'},
 kg:{title:'Катталган акча операцияларын салыштыруу',
  received:'Коноктордон түшкөн төлөмдөр',paid:'Чыгымдар боюнча кол менен төлөмдөр',
  difference:'Катталган операциялардын айырмасы',open:'Төлөнө элек чыгымдар',
  notice:'Бул пайда, банктагы калдык же толук акча агымы эмес. Кайтаруулар жана башка операциялар салыштырылган жок.'},
 en:{title:'Recorded cash movement comparison',
  received:'Recorded guest receipts',paid:'Manually recorded expense payments',
  difference:'Difference in recorded movements',open:'Unsettled expenses',
  notice:'Not profit, verified bank balance or complete cash flow. Refunds, missing movements and recognition differences are not reconciled.'},
 kz:{title:'Тіркелген ақша қозғалысын салыстыру',
  received:'Қонақтардан тіркелген түсімдер',paid:'Қолмен тіркелген шығыс төлемдері',
  difference:'Тіркелген қозғалыс айырмасы',open:'Төленбеген шығыстар',
  notice:'Бұл пайда, банк қалдығы немесе толық ақша ағымы емес. Қайтарымдар және басқа операциялар салыстырылмаған.'},
} as const;

/** Only amounts verified in the exact hotel Core report are displayed.
 * Incoming payments are not earnings; this is NOT a P&L or tax report. */
export default function Finance() {
  const { user, hotel, api, locale } = useSession();
  const copy = useMobileCopy();
  const extra = OWNER_FINANCE_COPY[locale];
  const kitchenCopy = KITCHEN_REPORT_COPY[locale];
  const cashCopy = CASH_RECONCILIATION_COPY[locale];
  const { c } = useTheme();
  const router = useRouter();
  const modules = useLiveModules();
  const allowed = api?.mode === 'LIVE' && canReadFinance(user);
  const from = localDate(-29), to = localDate();
  const { data, loading, error, reload } = useAsync(
    () => allowed && modules ? modules.financeSummary(from, to) : Promise.resolve(null),
    [modules, allowed, hotel?.id, user?.id, user?.module_permissions?.join(',')],
  );
  const ownerKitchen=useAsync(
    () => allowed && user?.role==='OWNER' && modules ?
      modules.ownerKitchenManagement(from,to):Promise.resolve(null),
    [modules,allowed,user?.role,user?.id,hotel?.id],
  );
  const recordedCash=useAsync(
    () => allowed && user?.role==='OWNER' && modules ?
      modules.ownerRecordedCashMovements(from,to):Promise.resolve(null),
    [modules,allowed,user?.role,user?.id,hotel?.id],
  );
  const reloadCash = recordedCash.reload;
  const reloadKitchen = ownerKitchen.reload;
  const focused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (focused.current) { void reload(); void reloadKitchen(); void reloadCash(); } else focused.current = true;
  }, [reload,reloadKitchen,reloadCash]));
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
      {data.kitchen_stock_cost ? <>
        <SectionLabel>{extra.stockCost}</SectionLabel>
        <GlassCard style={{gap:space.sm}}>
          {line(extra.stockCost,data.kitchen_stock_cost.real_production_cost_kgs+' '+data.range.currency,extra.stockNotice)}
          {Number(data.kitchen_stock_cost.sample_production_cost_kgs) > 0 ?
            line(extra.sampleCost,data.kitchen_stock_cost.sample_production_cost_kgs+' '+data.range.currency) : null}
        </GlassCard>
      </> : null}
      {user?.role==='OWNER'?<>
        <SectionLabel>{kitchenCopy.title}</SectionLabel>
        {ownerKitchen.loading?<LoadingShimmer count={1}/>:null}
        {ownerKitchen.error?<ErrorState text={ownerKitchen.error.message} retry={copy.retry}
          onRetry={ownerKitchen.reload}/>:null}
        {ownerKitchen.data?<GlassCard style={{gap:space.sm}}>
          {line(kitchenCopy.production,
            ownerKitchen.data.real_production_cost_kgs+' '+data.range.currency)}
          {line(kitchenCopy.losses,
            ownerKitchen.data.real_loss_cost_kgs+' '+data.range.currency)}
          {line(kitchenCopy.waste,
            ownerKitchen.data.real_inventory_movements.WASTE.cost_kgs+' '+data.range.currency)}
          {line(kitchenCopy.spoilage,
            ownerKitchen.data.real_inventory_movements.SPOILAGE.cost_kgs+' '+data.range.currency)}
          {line(kitchenCopy.returns,
            ownerKitchen.data.real_supplier_return_stock_debit_kgs+' '+data.range.currency)}
          {line(kitchenCopy.stock,
            ownerKitchen.data.current_stock.real_book_inventory_value_kgs===null
              ? '—' : ownerKitchen.data.current_stock.real_book_inventory_value_kgs+' '+data.range.currency)}
          {line(kitchenCopy.gross,
            ownerKitchen.data.procurement_exposure.gross_supplier_obligations_kgs+' '+data.range.currency)}
          {line(kitchenCopy.settled,
            ownerKitchen.data.procurement_exposure.settled_supplier_payables_kgs+' '+data.range.currency)}
          {line(kitchenCopy.credits,
            ownerKitchen.data.procurement_exposure.credited_supplier_payables_kgs+' '+data.range.currency)}
          {line(kitchenCopy.outstanding,
            ownerKitchen.data.procurement_exposure.outstanding_supplier_payables_kgs+' '+data.range.currency)}
          {line(kitchenCopy.legacyDifference,
            ownerKitchen.data.source_reconciliation.inventory.linked_source.legacy_invoice_vs_stock_cost_delta_kgs+' '+data.range.currency)}
          {line(kitchenCopy.returnDifference,
            ownerKitchen.data.source_reconciliation.supplier_documents.return_credit_minus_stock_cost_kgs+' '+data.range.currency)}
          {ownerKitchen.data.current_stock.valuation_status!=='MOVEMENT_BASED'||
            ownerKitchen.data.source_reconciliation.inventory.linked_source.source_mismatch_count>0||
            ownerKitchen.data.source_reconciliation.supplier_documents.payables_status!=='RECORDED_OBLIGATIONS_BALANCED'
             ? <Text style={[font.small,{color:c.warning}]}>{kitchenCopy.reconciliation}</Text> : null}
          {line(kitchenCopy.approved,
            ownerKitchen.data.procurement_exposure.approved_unreceived_at_current_item_cost_kgs+' '+data.range.currency)}
          {line(kitchenCopy.unapproved,
            ownerKitchen.data.procurement_exposure.unapproved_requests_at_current_item_cost_kgs+' '+data.range.currency)}
          <Text style={[font.small,{color:c.textMuted}]}>
            {kitchenCopy.notice}
          </Text>
        </GlassCard>:null}
      </>:null}
      {user?.role==='OWNER'?<>
        <SectionLabel>{cashCopy.title}</SectionLabel>
        {recordedCash.loading?<LoadingShimmer count={1}/>:null}
        {recordedCash.error?<ErrorState text={recordedCash.error.message}
          retry={copy.retry} onRetry={recordedCash.reload}/>:null}
        {recordedCash.data?<GlassCard style={{gap:space.sm}}>
          {line(cashCopy.received,money(recordedCash.data.customer_payments_received_kgs))}
          {line(cashCopy.paid,money(recordedCash.data.owner_expense_manual_settlements_kgs))}
          {line(cashCopy.difference,money(recordedCash.data.observed_recorded_difference_kgs))}
          {line(cashCopy.open,money(recordedCash.data.all_time_unsettled_expenses_kgs))}
          <Text style={[font.small,{color:c.textMuted}]}>{cashCopy.notice}</Text>
        </GlassCard>:null}
      </>:null}
      {user?.role==='OWNER' && modules ? <OwnerExpenses live={modules} from={from} to={to} onChanged={() => Promise.all([reload(), reloadKitchen(), reloadCash()])}/> : null}
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