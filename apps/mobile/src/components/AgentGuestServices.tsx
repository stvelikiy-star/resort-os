import React, { useRef, useState } from 'react';
import { Alert, Text } from 'react-native';
import { AGENT_SERVICES, AgentServiceCode, useLiveModules } from '../api/liveModules';
import { ApiError } from '../api/types';
import { acknowledgePendingAgentService, beginPendingAgentService, clearPendingAgentService, readPendingAgentService } from '../lib/pendingAgentService';
import { wasWriteRejected } from '../lib/writeOutcome';
import { useAsync } from '../lib/useAsync';
import { useMobileCopy } from '../i18n/mobileCopy';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { font } from '../theme/tokens';
import { Button, Field } from './ui';
import { agentServiceDraft, AgentServiceList } from '../api/agentServices';
import { GlassCard } from './Future';

const agentReconcileCopy = {
  ru: { action: 'Я сверил заявку с менеджером', warning: 'Проверьте в платформе бронь, код услуги и статус заявки с менеджером. Подтверждение только снимает локальную блокировку и НЕ создаёт новую заявку.', confirm: 'Я проверил результат заявки в платформе и понимаю, что повторная отправка может создать дубль.' },
  en: { action: 'I verified with the manager', warning: 'Verify the reservation, service code and request status with the manager in the platform. This only clears the local lock; it does NOT create another request.', confirm: 'I checked the request outcome in the platform and understand that a new submission could create a duplicate.' },
  kg: { action: 'Арызды менеджер менен текшердим', warning: 'Платформадан бронду, кызмат кодун жана арыздын абалын менеджер менен текшериңиз. Бул аракет жергиликтүү бөгөттү гана алып салат, жаңы арыз түзбөйт.', confirm: 'Арыздын жыйынтыгын платформадан текшердим. Кайра жөнөтүү кайталанган арыз түзүшү мүмкүн экенин түшүнөм.' },
  kz: { action: 'Өтінімді менеджермен тексердім', warning: 'Платформада брондауды, қызмет кодын және өтінім күйін менеджермен тексеріңіз. Бұл әрекет тек жергілікті бұғаттауды алып тастайды, жаңа өтінім жасамайды.', confirm: 'Өтінім нәтижесін платформада тексердім. Қайта жіберу қайталанған өтінім жасауы мүмкін екенін түсінемін.' },
} as const;

const agentServiceLabels = {
  ru: ['Добавить услугу', 'Трансфер', 'Питание', 'Парковка', 'Сауна', 'Бильярд', 'Экскурсия'],
  en: ['Add service', 'Transfer', 'Meals', 'Parking', 'Sauna', 'Billiards', 'Excursion'],
  kg: ['Кызмат кошуу', 'Трансфер', 'Тамактануу', 'Унаа токтотуучу жай', 'Сауна', 'Бильярд', 'Экскурсия'],
  kz: ['Қызмет қосу', 'Трансфер', 'Тамақтану', 'Автотұрақ', 'Сауна', 'Бильярд', 'Экскурсия'],
} as const;

const serviceCopy = {
  ru: {date:'Дата услуги (ГГГГ-ММ-ДД, необязательно)',time:'Время услуги (ЧЧ:ММ, необязательно)',note:'Примечание к услуге',list:'Заявки по этой брони',empty:'Заявок пока нет',partial:'Показана часть заявок',invalid:'Проверьте дату, время и примечание',statuses:{OPEN:'Новая',IN_PROGRESS:'В работе',DONE:'Выполнена',CANCELLED:'Отменена'}},
  en: {date:'Service date (YYYY-MM-DD, optional)',time:'Service time (HH:MM, optional)',note:'Service note',list:'Requests for this booking',empty:'No requests yet',partial:'Only part of the requests is shown',invalid:'Check service date, time and note',statuses:{OPEN:'New',IN_PROGRESS:'In progress',DONE:'Completed',CANCELLED:'Cancelled'}},
  kg: {date:'Кызмат күнү (ЖЖЖЖ-АА-КК, милдеттүү эмес)',time:'Кызмат убактысы (СС:ММ, милдеттүү эмес)',note:'Кызматка эскертүү',list:'Бул брондун өтүнмөлөрү',empty:'Өтүнмө жок',partial:'Өтүнмөлөрдүн бир бөлүгү көрсөтүлдү',invalid:'Күндү, убакытты жана эскертүүнү текшериңиз',statuses:{OPEN:'Жаңы',IN_PROGRESS:'Аткарылууда',DONE:'Аткарылды',CANCELLED:'Жокко чыгарылды'}},
  kz: {date:'Қызмет күні (ЖЖЖЖ-АА-КК, міндетті емес)',time:'Қызмет уақыты (СС:ММ, міндетті емес)',note:'Қызметке ескерту',list:'Осы брондаудың өтінімдері',empty:'Өтінім жоқ',partial:'Өтінімдердің бір бөлігі көрсетілді',invalid:'Күнді, уақытты және ескертуді тексеріңіз',statuses:{OPEN:'Жаңа',IN_PROGRESS:'Орындалуда',DONE:'Орындалды',CANCELLED:'Бас тартылды'}},
} as const;

/** Same journal and creation flow for new and existing agent reservations.
 * The API rechecks ACTIVE membership and ownership; navigation is no authority. */
export function AgentGuestServices({ reservationId }: { reservationId: string | null }) {
  const live = useLiveModules();
  const { user, hotel, api, locale, serverAuthMode } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const t = serviceCopy[locale];
  const showroom = api?.mode === 'DEMO';
  const allowed = user?.role === 'AGENT' && !!user.module_permissions?.includes('PMS');
  const agentIdentity = allowed && hotel?.id && user.id
    ? { hotelId: hotel.id, userId: user.id } : null;
  const [serviceDate, setServiceDate] = useState('');
  const [serviceTime, setServiceTime] = useState('');
  const [description, setDescription] = useState('');
  const [serviceOpen, setServiceOpen] = useState(false);
  const [serviceMessage, setServiceMessage] = useState('');
  const [serviceUnknown, setServiceUnknown] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyLock = useRef(false);
  const agentPending = useAsync(() => agentIdentity
    ? readPendingAgentService(agentIdentity.hotelId, agentIdentity.userId) : Promise.resolve(null),
    [agentIdentity?.hotelId, agentIdentity?.userId]);
  const history = useAsync<AgentServiceList | null>(() => allowed && !showroom && live && reservationId &&
    serverAuthMode !== 'shared_auth_preview' ? live.agentGuestServices(reservationId) : Promise.resolve(null),
    [allowed, showroom, live, reservationId, serverAuthMode, hotel?.id, user?.id]);
  let scheduleValid = true;
  try { agentServiceDraft({ service_date: serviceDate, service_time: serviceTime, description }); }
  catch { scheduleValid = false; }
  const serviceLocked = serviceUnknown || agentPending.loading || !!agentPending.error || !!agentPending.data;
  const addService = (service: AgentServiceCode, label: string) => Alert.alert(agentServiceLabels[locale][0],
    [label, serviceDate, serviceTime, description].filter(Boolean).join(' · '), [
    { text: copy.close, style: 'cancel' },
    { text: copy.confirm, onPress: async () => {
      if (!live || !reservationId || !allowed || user?.role !== 'AGENT' ||
        showroom || serverAuthMode === 'shared_auth_preview' || busyLock.current || serviceLocked || !scheduleValid || !agentIdentity) return;
      busyLock.current = true;
      setBusy(true);
      setServiceMessage('');
      let recorded = false;
      try {
        await beginPendingAgentService(agentIdentity.hotelId, agentIdentity.userId, reservationId, service, { service_date: serviceDate, service_time: serviceTime });
        recorded = true;
        await agentPending.reload();
        await live.addAgentGuestService(reservationId, service,
          agentServiceDraft({ service_date: serviceDate, service_time: serviceTime, description }));
        await clearPendingAgentService(agentIdentity.hotelId, agentIdentity.userId);
        await agentPending.reload();
        setServiceMessage(copy.confirmed + ' · ' + label);
        await history.reload();
      } catch (error) {
        // 409 may mean the service already exists (GUEST_SERVICE_DUPLICATE_ACTIVE).
        // Never clear the journal on 409 without manual server reconciliation.
        const rejected = recorded && error instanceof ApiError && error.code !== 'CONFLICT' && wasWriteRejected(error);
        if (rejected) {
          try { await clearPendingAgentService(agentIdentity.hotelId, agentIdentity.userId); }
          catch { setServiceUnknown(true); }
        } else {
          setServiceUnknown(true);
        }
        await agentPending.reload().catch(() => {});
        setServiceMessage(rejected && error instanceof Error ? error.message : copy.resultUnknown);
      } finally {
        busyLock.current = false;
        setBusy(false);
      }
    } },
  ]);
  const acknowledgeAgentService = () => Alert.alert(agentReconcileCopy[locale].action,
    agentReconcileCopy[locale].confirm, [
      { text: copy.close, style: 'cancel' },
      { text: copy.confirm, onPress: async () => {
        const inspected = agentPending.data;
        if (!agentIdentity || !inspected || busyLock.current || busy) return;
        busyLock.current = true; setBusy(true);
        try {
          if (await acknowledgePendingAgentService(agentIdentity.hotelId, agentIdentity.userId, inspected)) {
            setServiceUnknown(false); setServiceMessage('');
          }
        } catch { setServiceMessage(copy.resultUnknown); }
        finally { await agentPending.reload(); busyLock.current = false; setBusy(false); }
      } },
    ]);
  if (!allowed || showroom || !live || serverAuthMode === 'shared_auth_preview') return null;
  return <>
    {user?.role === 'AGENT' && serviceLocked && !showroom ? <GlassCard testID="agent-service-pending" style={{gap:8,borderLeftWidth:4,borderLeftColor:c.warning}}>
      <Text accessibilityRole="alert" style={[font.body,{color:c.warning}]}>{copy.resultUnknown}</Text>
      {agentPending.data ? <Text style={[font.small,{color:c.text}]}>{agentPending.data.serviceCode} · {agentPending.data.reservationId} · {agentPending.data.serviceDate ?? ''} {agentPending.data.serviceTime ?? ''}</Text> : null}
      <Text style={[font.small,{color:c.text}]}>{agentReconcileCopy[locale].warning}</Text>
      <Button label={copy.retry} disabled={busy} variant="secondary" onPress={() => void agentPending.reload()}/>
      {agentPending.data ? <Button testID="agent-service-acknowledge" label={agentReconcileCopy[locale].action}
        disabled={busy} variant="secondary" onPress={acknowledgeAgentService}/> : null}
    </GlassCard> : null}
      {reservationId ? <>
        <Button label={agentServiceLabels[locale][0]} variant="secondary" disabled={busy || serviceLocked} onPress={() => setServiceOpen(!serviceOpen)}/>
        {serviceOpen ? <>
          <Field label={t.date} value={serviceDate} onChangeText={setServiceDate} maxLength={10} editable={!busy && !serviceLocked}/>
          <Field label={t.time} value={serviceTime} onChangeText={setServiceTime} maxLength={5} editable={!busy && !serviceLocked}/>
          <Field label={t.note} value={description} onChangeText={setDescription} maxLength={2000} editable={!busy && !serviceLocked}/>
          {!scheduleValid ? <Text accessibilityRole="alert" style={[font.small,{color:c.danger}]}>{t.invalid}</Text> : null}
          {AGENT_SERVICES.map((service, index) => <Button key={service}
            label={agentServiceLabels[locale][index + 1]} variant="secondary" disabled={busy || serviceLocked || !scheduleValid}
            onPress={() => addService(service, agentServiceLabels[locale][index + 1])}/>)}
        </> : null}
        {serviceLocked ? <Text accessibilityRole="alert" style={[font.body, { color: c.warning }]}>{copy.resultUnknown} · {agentReconcileCopy[locale].warning}</Text> : null}
        {serviceMessage ? <Text accessibilityRole="alert" style={[font.body, { color: c.text }]}>{serviceMessage}</Text> : null}
      </> : null}
    {reservationId ? <GlassCard testID="agent-service-history" style={{gap:8}}>
      <Text style={[font.h2,{color:c.text}]}>{t.list}</Text>
      <Button label={copy.retry} variant="secondary" disabled={history.loading} onPress={() => void history.reload()}/>
      {history.loading ? <Text style={[font.small,{color:c.textMuted}]}>{copy.loading}</Text> : null}
      {history.error ? <Text accessibilityRole="alert" style={[font.small,{color:c.danger}]}>{history.error.message}</Text> : null}
      {history.data?.items.length === 0 ? <Text style={[font.small,{color:c.textMuted}]}>{t.empty}</Text> : null}
      {history.data?.preview_truncated ? <Text style={[font.small,{color:c.warning}]}>{t.partial}</Text> : null}
      {history.data?.items.map(item => <React.Fragment key={item.id}>
        <Text style={[font.body,{color:c.text}]}>{agentServiceLabels[locale][AGENT_SERVICES.indexOf(item.service_code) + 1]} · {t.statuses[item.status]}</Text>
        <Text selectable style={[font.small,{color:c.textMuted}]}>{item.id} · {item.service_date ?? '—'} {item.service_time ?? ''}</Text>
        {item.description ? <Text style={[font.small,{color:c.text}]}>{item.description}</Text> : null}
      </React.Fragment>)}
    </GlassCard> : null}
  </>;
}
