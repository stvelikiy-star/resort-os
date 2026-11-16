import React, { useCallback, useRef } from 'react';
import { Text, View, useWindowDimensions } from 'react-native';
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

const ACCRUAL_READINESS_COPY={
 ru:{
  delivered:'Проживание по фактическим ночам (оценка)',deliveredCount:'Подтверждённые ночи',deliveredExcluded:'Брони, требующие сверки',folioLinked:'Обслуженные заказы со сверенным folio',folioExcluded:'Заказы, требующие сверки',deliveredNotice:'Оценка проживания распределена по фактическим ночам. Пакеты услуг, скидки, налоги и возвраты ещё не сверены.',
  title:'OWNER · сверка доходов и расходов',
  posted:'Проведённые обязательства',nonstock:'Расходы к классификации (не склад)',
  stockreview:'Расходы с риском дублирования склада',
  kitchen:'Кухня — стоимость приготовления',loss:'Порча и потери по движениям',
  served:'Обслуженные заказы — стоимость продаж (не выручка)',
  lodging:'Выехавшие брони — стоимость проживания (не выручка)',
  missing:'Заказы без связанной записи folio',
  status:'Признанная прибыль недоступна',notice:'Это показатели для сверки, не отчёт о прибыли. Платежи, накладные, продажи и расходы не складываются автоматически.'},
 kg:{
  delivered:'Чыныгы түндөр боюнча жашоо баасы (болжол)',deliveredCount:'Ырасталган түндөр',deliveredExcluded:'Текшерүүнү талап кылган брондор',folioLinked:'Folio менен салыштырылган заказдар',folioExcluded:'Текшерүүнү талап кылган заказдар',deliveredNotice:'Жашоо баасы чыныгы түндөр боюнча бөлүндү. Пакеттер, арзандатуулар, салыктар жана кайтаруулар текшериле элек.',
  title:'ЭЭСИ · киреше жана чыгаша салыштыруусу',
  posted:'Катталган милдеттенмелер',nonstock:'Кампага кирбеген чыгаша талапкерлери',
  stockreview:'Кампа менен кош эсептелүү коркунучу',
  kitchen:'Ашкана — даярдоонун наркы',loss:'Жоготуу жана бузулуу',
  served:'Тейленген буйрутмалар — баа (киреше эмес)',
  lodging:'Чыккан коноктордун брондору — баа (киреше эмес)',
  missing:'Folio жазуусу жок буйрутмалар',
  status:'Таанылган пайда жеткиликсиз',notice:'Бул пайда эмес, салыштыруу үчүн маалымат. Төлөмдөр, накладнойлор жана чыгашалар автоматтык кошулбайт.'},
 en:{
  delivered:'Lodging by delivered night (candidate)',deliveredCount:'Verified nights',deliveredExcluded:'Bookings requiring review',folioLinked:'Served orders matched to folio',folioExcluded:'Orders requiring review',deliveredNotice:'Booked value is allocated by verified stay nights. Packages, discounts, tax and refunds remain unverified.',
  title:'OWNER · revenue and expense reconciliation',
  posted:'Posted obligations',nonstock:'Non-stock expense candidates',
  stockreview:'Expense amounts requiring stock-overlap review',
  kitchen:'Kitchen production carrying cost',loss:'Spoilage and waste movement cost',
  served:'Served order face value (not recognized revenue)',
  lodging:'Checked-out booking face value (not recognized revenue)',
  missing:'Served orders with no linked folio',
  status:'Recognized profit unavailable',
  notice:'Operational candidates only, not a profit report. Payments, supplier invoices, sales and expenses must not be added automatically.'},
 kz:{
  delivered:'Нақты түндер бойынша тұру құны (бағалау)',deliveredCount:'Расталған түндер',deliveredExcluded:'Тексеруді қажет ететін броньдар',folioLinked:'Folio-мен сәйкес берілген тапсырыстар',folioExcluded:'Тексеруді қажет ететін тапсырыстар',deliveredNotice:'Тұру құны расталған түндерге бөлінді. Пакеттер, жеңілдіктер, салық және қайтарым тексерілмеген.',
  title:'ИЕСІ · табыс пен шығынды салыстыру',
  posted:'Тіркелген міндеттемелер',nonstock:'Қоймадан тыс шығын үміткерлері',
  stockreview:'Қоймамен қайталану қаупі бар шығындар',
  kitchen:'Асхана — дайындау құны',loss:'Бүліну мен шығын құны',
  served:'Берілген тапсырыстар құны (табыс емес)',
  lodging:'Шыққан қонақ броньдары құны (табыс емес)',
  missing:'Folio жазбасыз тапсырыстар',
  status:'Танылған пайда қолжетімсіз',
  notice:'Бұл пайда есебі емес, салыстыру көрсеткіштері. Төлем, жүкқұжат, сату және шығын автоматты түрде қосылмайды.'},
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
  const accrualCopy = ACCRUAL_READINESS_COPY[locale];
  const cashCopy = CASH_RECONCILIATION_COPY[locale];
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const compactRows = width < 375 || fontScale > 1.25;
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
  const refreshReports = useCallback(() => {
    void reload(); void reloadKitchen(); void reloadCash();
  }, [reload, reloadKitchen, reloadCash]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (focused.current) { void reload(); void reloadKitchen(); void reloadCash(); } else focused.current = true;
  }, [reload,reloadKitchen,reloadCash]));
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  const money = (v: number) => Number(v).toLocaleString('ru-RU') + ' ' + (data?.range.currency || 'KGS');
  const line = (label: string, amount: string, caption?: string) =>
    <View key={label} style={{ flexDirection:compactRows?'column':'row',alignItems:compactRows?'stretch':'center',justifyContent:'space-between',gap:8,paddingVertical:8,
      borderBottomWidth:1,borderBottomColor:c.border }}>
      <View style={{flex:1,minWidth:0,gap:3}}>
        <Text style={[font.body,{color:c.text}]}>{label}</Text>
        {caption ? <Text style={[font.small,{color:c.textMuted}]}>{caption}</Text> : null}
      </View>
      <Text style={[font.body,{color:c.text,fontWeight:'700',textAlign:compactRows?'left':'right',flexShrink:1,maxWidth:'100%'}]}>{amount}</Text>
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
      {user?.role==='OWNER' && data.owner_accrual_readiness_snapshot ? <>
        <SectionLabel>{accrualCopy.title}</SectionLabel>
        <GlassCard style={{gap:space.sm}}>
          {line(accrualCopy.posted,
            data.owner_accrual_readiness_snapshot.posted_owner_obligations.posted_total_kgs+' '+data.range.currency)}
          {line(accrualCopy.nonstock,
            data.owner_accrual_readiness_snapshot.posted_owner_obligations.non_stock_obligations_candidate_kgs+' '+data.range.currency)}
          {line(accrualCopy.stockreview,
            data.owner_accrual_readiness_snapshot.posted_owner_obligations.stock_overlap_review_kgs+' '+data.range.currency)}
          {line(accrualCopy.kitchen,
            data.owner_accrual_readiness_snapshot.kitchen_cost_movements.production_cost_candidate_kgs+' '+data.range.currency)}
          {line(accrualCopy.loss,
            data.owner_accrual_readiness_snapshot.kitchen_cost_movements.loss_cost_candidate_kgs+' '+data.range.currency)}
          {line(accrualCopy.served,
            data.owner_accrual_readiness_snapshot.revenue_source_candidates.served_dining_face_value_kgs+' '+data.range.currency)}
          {line(accrualCopy.lodging,
            data.owner_accrual_readiness_snapshot.revenue_source_candidates.checked_out_booked_total_kgs+' '+data.range.currency)}
          {line(accrualCopy.missing,
            String(data.owner_accrual_readiness_snapshot.revenue_source_candidates.served_without_linked_folio_count))}
          {line(accrualCopy.delivered,
            data.owner_accrual_readiness_snapshot.delivered_revenue_sources.accommodation.allocated_booking_face_value_kgs+' '+data.range.currency)}
          {line(accrualCopy.deliveredCount,
            String(data.owner_accrual_readiness_snapshot.delivered_revenue_sources.accommodation.delivered_booked_nights_count))}
          {line(accrualCopy.deliveredExcluded,
            String(data.owner_accrual_readiness_snapshot.delivered_revenue_sources.accommodation.excluded_reservations_count))}
          {line(accrualCopy.folioLinked,
            data.owner_accrual_readiness_snapshot.delivered_revenue_sources.dining.single_source_folio_linked_candidate_kgs+' '+data.range.currency)}
          {line(accrualCopy.folioExcluded,
            String(data.owner_accrual_readiness_snapshot.delivered_revenue_sources.dining.excluded_orders_count))}
          <Text style={[font.small,{color:c.textMuted}]}>{accrualCopy.deliveredNotice}</Text>
          <Text style={[font.body,{color:c.warning,fontWeight:'700'}]}>{accrualCopy.status}</Text>
          <Text style={[font.small,{color:c.textMuted}]}>{accrualCopy.notice}</Text>
        </GlassCard>
      </> : null}
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
      {user?.role==='OWNER' && modules ? <OwnerExpenses live={modules} from={from} to={to} onRecorded={refreshReports}/> : null}
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