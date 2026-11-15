import React, { useCallback, useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useFocusEffect } from 'expo-router';
import type { DiningFloor, DiningSeatingSession, createLiveModules } from '../api/liveModules';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { useAsync } from '../lib/useAsync';
import { beginPendingDiningWrite, clearPendingDiningWrite, readPendingDiningWrite, type PendingDiningWrite } from '../lib/durableDiningWrites';
import { wasWriteRejected } from '../lib/writeOutcome';
import { Button, SectionLabel } from './ui';
import { GlassCard } from './Future';
import { font, space } from '../theme/tokens';

const LABELS = {
  ru: { title:'Посадка гостей и счёт номера', seats:'Посадить гостя', guest:'Гость из бронирования',
    tables:'Выберите свободный стол', active:'Обслуживание сегодня', move:'Пересадить', release:'Завершить обслуживание',
    waiting:'Ожидает посадки', seated:'За столом', folio:'Начисления на номер', post:'Начислить на номер',
    posted:'Уже начислено', notPayment:'Начисление в Folio — не оплата. Денежные поступления учитываются отдельно.',
    empty:'Нет активных посадок', noGuests:'Нет доступных проживаний на эту дату',
    confirm:'Подтвердить операцию?', cancel:'Отмена', approve:'Подтвердить',
    success:'Операция подтверждена сервером', failed:'Операция отклонена сервером',
    unknown:'Результат неизвестен. Повторная запись заблокирована до сверки с Web.',
    check:'Обновить данные', reviewed:'Я сверил результат в Web', reviewConfirm:'Подтвердите, что результат уже проверен в основной платформе. Это снимет защитную блокировку.',
    review:'Сверить вручную', unavailable:'Данные недоступны', select:'Выбрать', toTable:'Новый стол',
  },
  kg: { title:'Конокторду отургузуу жана бөлмөнүн эсеби', seats:'Конокту отургузуу', guest:'Брондогу конок',
    tables:'Бош үстөлдү тандаңыз', active:'Бүгүнкү тейлөө', move:'Башка үстөлгө которуу', release:'Тейлөөнү аяктоо',
    waiting:'Отурууну күтүп жатат', seated:'Үстөлдө', folio:'Бөлмөнүн эсебине жазуулар', post:'Бөлмөнүн эсебине кошуу',
    posted:'Эсепке кошулган', notPayment:'Бөлмөнүн эсебине кошуу төлөм эмес. Акча түшүүлөрү өзүнчө эсептелет.',
    empty:'Активдүү отургузуулар жок', noGuests:'Бул күнгө ылайыктуу коноктор жок',
    confirm:'Аракетти ырастайсызбы?', cancel:'Жокко чыгаруу', approve:'Ырастоо',
    success:'Аракет сервер тарабынан ырасталды', failed:'Сервер аракетти четке какты',
    unknown:'Жыйынтык белгисиз. Web аркылуу текшерилмейинче кайра жазуу бөгөттөлдү.',
    check:'Маалыматты жаңылоо', reviewed:'Натыйжаны Web аркылуу текшердим', reviewConfirm:'Натыйжаны негизги платформадан текшергениңизди ырастап, бөгөттү алып салыңыз.',
    review:'Кол менен текшерүү', unavailable:'Маалымат жеткиликсиз', select:'Тандоо', toTable:'Жаңы үстөл',
  },
  en: { title:'Guest seating and room folio', seats:'Seat guest', guest:'Guest from reservation',
    tables:'Select available table', active:'Today’s seating', move:'Move guest', release:'Finish service',
    waiting:'Waiting', seated:'Seated', folio:'Room folio charges', post:'Post to room',
    posted:'Already posted', notPayment:'A folio charge is not a payment. Receipts are recorded separately.',
    empty:'No active seating', noGuests:'No eligible stays for this date',
    confirm:'Confirm this operation?', cancel:'Cancel', approve:'Confirm',
    success:'Server confirmed the operation', failed:'Server rejected the operation',
    unknown:'Outcome unknown. New writes are blocked until reconciled in Web.',
    check:'Refresh data', reviewed:'I verified the outcome in Web', reviewConfirm:'Confirm that you checked the result in the main platform. This clears the protective lock.',
    review:'Reconcile manually', unavailable:'Data unavailable', select:'Select', toTable:'New table',
  },
  kz: { title:'Қонақтарды отырғызу және бөлме шоты', seats:'Қонақты отырғызу', guest:'Брондағы қонақ',
    tables:'Бос үстелді таңдаңыз', active:'Бүгінгі қызмет', move:'Басқа үстелге ауыстыру', release:'Қызметті аяқтау',
    waiting:'Күтіп отыр', seated:'Үстелде', folio:'Бөлме шоты бойынша жазбалар', post:'Бөлме шотына қосу',
    posted:'Шотқа қосылған', notPayment:'Бөлме шотына жазу төлем емес. Түскен төлемдер бөлек есептеледі.',
    empty:'Белсенді отырғызулар жоқ', noGuests:'Бұл күнге қолайлы қонақтар жоқ',
    confirm:'Әрекетті растайсыз ба?', cancel:'Бас тарту', approve:'Растау',
    success:'Сервер әрекетті растады', failed:'Сервер әрекеттен бас тартты',
    unknown:'Нәтиже белгісіз. Web арқылы тексерілгенше жаңа жазбалар бұғатталған.',
    check:'Деректерді жаңарту', reviewed:'Нәтижені Web арқылы тексердім', reviewConfirm:'Нәтижені негізгі платформадан тексергеніңізді растаңыз. Бұл бұғаттауды алып тастайды.',
    review:'Қолмен тексеру', unavailable:'Деректер қолжетімсіз', select:'Таңдау', toTable:'Жаңа үстел',
  },
} as const;

type Modules = ReturnType<typeof createLiveModules>;
type Table = DiningFloor['tables'][number];

/** A separate operational panel; no API or server permission is modified by this UI. */
export function DiningServiceMobile({ live, tables, reloadFloor }: {
  live: Modules; tables: DiningFloor['tables']; reloadFloor: () => Promise<unknown>;
}) {
  const { user, hotel, locale } = useSession();
  const { c } = useTheme();
  const t = LABELS[locale];
  const identity = user?.id && hotel?.id ? { hotelId:hotel.id, userId:user.id } : null;
  const sessions = useAsync(() => live.diningSeatingSessions(), [live, identity?.hotelId, identity?.userId]);
  const stays = useAsync(() => live.diningStays(), [live, identity?.hotelId, identity?.userId]);
  const folio = useAsync(() => live.diningFolioOrders(), [live, identity?.hotelId, identity?.userId]);
  const journal = useAsync(() => identity
    ? readPendingDiningWrite(identity.hotelId, identity.userId) : Promise.reject(new Error('No verified operator')),
    [identity?.hotelId, identity?.userId]);
  const busyLock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [selectedStay, setSelectedStay] = useState('');
  const [selectedTable, setSelectedTable] = useState('');
  const [movingSession, setMovingSession] = useState<DiningSeatingSession | null>(null);
  const [targetTable, setTargetTable] = useState('');
  const blocked = busy || journal.loading || !!journal.error || !!journal.data;
  const refresh = useCallback(async () => {
    await Promise.all([sessions.reload(),stays.reload(),folio.reload(),reloadFloor()]);
  },[sessions.reload,stays.reload,folio.reload,reloadFloor]);
  useFocusEffect(useCallback(() => { void refresh(); },[refresh]));
  const day = stays.data?.local_date ?? '';
  const eligibleStays = (stays.data?.items ?? []).filter(s => s.check_in <= day && day <= s.check_out);
  const selected = eligibleStays.find(s => s.stay_id === selectedStay);
  const available = (table: Table) => table.status === 'AVAILABLE' && !!selected &&
    table.seats >= selected.adults + selected.children;
  const seatTable = tables.find(table => table.id === selectedTable);
  const act = (kind: PendingDiningWrite['operation'], run: () => Promise<unknown>) => {
    Alert.alert(t.confirm,'',[
      { text:t.cancel,style:'cancel' },
      { text:t.approve,onPress:() => { void (async () => {
        if (busyLock.current || blocked || !identity) return;
        busyLock.current=true;setBusy(true);setMessage('');
        let recorded=false;
        try {
          await beginPendingDiningWrite(identity.hotelId,identity.userId,kind);
          recorded=true;
          await journal.reload();
          await run(); // Only a validated server acknowledgement permits clearing.
          await clearPendingDiningWrite(identity.hotelId,identity.userId);
          await journal.reload();
          setMessage(t.success);
          try { await refresh(); } catch { /* acknowledgement is valid; refresh remains user-retryable */ }
          setSelectedStay('');setSelectedTable('');setMovingSession(null);setTargetTable('');
        } catch (error) {
          if (recorded && wasWriteRejected(error)) {
            try { await clearPendingDiningWrite(identity.hotelId,identity.userId); } catch { /* preserve lock */ }
            setMessage(t.failed);
          } else {
            setMessage(t.unknown);
          }
          await journal.reload().catch(()=>{});
        } finally { busyLock.current=false;setBusy(false); }
      })(); } },
    ]);
  };
  const manuallyReviewed = () => {
    if (!identity || !journal.data || busy || busyLock.current) return;
    Alert.alert(t.review,t.reviewConfirm,[
      {text:t.cancel,style:'cancel'},
      {text:t.approve,onPress:()=>{void (async()=>{
        if(busyLock.current || !identity)return;
        busyLock.current=true;setBusy(true);
        try { await refresh(); await clearPendingDiningWrite(identity.hotelId,identity.userId); await journal.reload();setMessage(''); }
        catch {setMessage(t.unknown);}
        finally {busyLock.current=false;setBusy(false);}
      })();}},
    ]);
  };
  return <View style={{gap:space.md}} testID="dining-service-mobile">
    <SectionLabel>{t.title}</SectionLabel>
    {journal.data || journal.error ? <GlassCard style={{gap:8}}>
      <Text accessibilityRole="alert" style={[font.body,{color:c.warning}]}>{t.unknown}</Text>
      <Button label={t.check} onPress={()=>void refresh()} disabled={busy}/>
      {journal.data ? <Button label={t.reviewed} onPress={manuallyReviewed} disabled={busy}/> : null}
    </GlassCard> : null}
    {(sessions.error || stays.error || folio.error) ? <GlassCard style={{gap:8}}>
      <Text accessibilityRole="alert" style={[font.body,{color:c.danger}]}>{t.unavailable}</Text>
      <Button label={t.check} onPress={()=>void refresh()}/>
    </GlassCard> : null}
    <GlassCard style={{gap:8}}>
      <SectionLabel>{t.seats}</SectionLabel>
      {!eligibleStays.length ? <Text style={[font.small,{color:c.textMuted}]}>{t.noGuests}</Text> : null}
      <Text style={[font.small,{color:c.textMuted}]}>{t.guest}</Text>
      {eligibleStays.map(s=><Button key={s.stay_id} variant={selectedStay===s.stay_id?'primary':'secondary'}
        label={s.guest_name+' · '+(s.room_code||s.booking_number)}
        onPress={()=>{setSelectedStay(s.stay_id);setSelectedTable('');}} disabled={blocked}/>)}
      {selected ? <Text style={[font.small,{color:c.textMuted}]}>{t.tables} · {selected.adults+selected.children}</Text> : null}
      {selected ? tables.filter(available).map(table=><Button key={table.id}
        label={table.code+' · '+table.seats}
        variant={selectedTable===table.id?'primary':'secondary'}
        onPress={()=>setSelectedTable(table.id)} disabled={blocked}/>) : null}
      <Button testID="seat-guest-submit" label={t.seats} disabled={blocked || !selected || !seatTable || !available(seatTable) || !day}
        onPress={()=>act('SEAT_GUEST',()=>live.createDiningSeatingSession(selectedStay,selectedTable,day))}/>
    </GlassCard>
    <GlassCard style={{gap:8}}>
      <SectionLabel>{t.active}</SectionLabel>
      {(sessions.data ?? []).length === 0 ? <Text style={[font.small,{color:c.textMuted}]}>{t.empty}</Text> : null}
      {(sessions.data ?? []).map(s=><View key={s.id} style={{gap:8,paddingVertical:9,borderBottomWidth:1,borderBottomColor:c.border}}>
        <Text style={[font.body,{color:c.text}]}>{s.guest_name} · {s.table_code} · {s.party_size}</Text>
        <Text style={[font.small,{color:c.textMuted}]}>{s.status==='SEATED'?t.seated:t.waiting}</Text>
        {s.status==='WAITING' ? <Button label={t.seats} disabled={blocked} onPress={()=>act('SEAT_GUEST',()=>live.setDiningSeatingStatus(s.id,'SEATED'))}/> : null}
        {s.status==='SEATED' ? <Button label={t.release} disabled={blocked} onPress={()=>act('RELEASE_TABLE',()=>live.setDiningSeatingStatus(s.id,'RELEASED'))}/> : null}
        <Button variant="secondary" label={t.move} disabled={blocked} onPress={()=>{setMovingSession(movingSession?.id===s.id?null:s);setTargetTable('');}}/>
        {movingSession?.id===s.id ? <>
          <Text style={[font.small,{color:c.textMuted}]}>{t.toTable}</Text>
          {tables.filter(x=>x.status==='AVAILABLE'&&x.seats>=s.party_size&&x.id!==s.table_id).map(x=>
            <Button key={x.id} variant={targetTable===x.id?'primary':'secondary'} label={x.code} disabled={blocked} onPress={()=>setTargetTable(x.id)}/>)}
          <Button testID="move-guest-submit" label={t.move} disabled={blocked||!targetTable}
            onPress={()=>act('MOVE_GUEST',()=>live.moveDiningSeatingSession(s.id,targetTable))}/>
        </> : null}
      </View>)}
    </GlassCard>
    <GlassCard style={{gap:8}}>
      <SectionLabel>{t.folio}</SectionLabel>
      <Text style={[font.small,{color:c.warning}]}>{t.notPayment}</Text>
      {(folio.data ?? []).map(o=><View key={o.id} style={{gap:6,paddingVertical:9,borderBottomWidth:1,borderBottomColor:c.border}}>
        <Text style={[font.body,{color:c.text}]}>{o.order_number} · {o.guest_name} · {o.total_kgs} KGS</Text>
        <Text style={[font.small,{color:c.textMuted}]}>{o.table_code||o.room_code||'—'}</Text>
        {o.folio_charge_id ? <Text style={[font.small,{color:c.success}]}>{t.posted}</Text> :
          <Button testID={'post-folio-'+o.id} label={t.post} disabled={blocked||!o.eligible_to_post}
            onPress={()=>act('POST_FOLIO',()=>live.postDiningFolioCharge(o.id))}/>}
      </View>)}
    </GlassCard>
    {message ? <Text accessibilityRole="alert" style={[font.small,{color:c.text}]}>{message}</Text> : null}
    <Button label={t.check} variant="secondary" onPress={()=>void refresh()} disabled={busy}/>
  </View>;
}
