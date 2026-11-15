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
import { Button } from './ui';
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

/** Same journal and creation flow for new and existing agent reservations.
 * The API rechecks ACTIVE membership and ownership; navigation is no authority. */
export function AgentGuestServices({ reservationId }: { reservationId: string | null }) {
  const live = useLiveModules();
  const { user, hotel, api, locale, serverAuthMode } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const showroom = api?.mode === 'DEMO';
  const allowed = user?.role === 'AGENT' && !!user.module_permissions?.includes('PMS');
  const agentIdentity = allowed && hotel?.id && user.id
    ? { hotelId: hotel.id, userId: user.id } : null;
  const [serviceOpen, setServiceOpen] = useState(false);
  const [serviceMessage, setServiceMessage] = useState('');
  const [serviceUnknown, setServiceUnknown] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyLock = useRef(false);
  const agentPending = useAsync(() => agentIdentity
    ? readPendingAgentService(agentIdentity.hotelId, agentIdentity.userId) : Promise.resolve(null),
    [agentIdentity?.hotelId, agentIdentity?.userId]);
  const serviceLocked = serviceUnknown || agentPending.loading || !!agentPending.error || !!agentPending.data;
  const addService = (service: AgentServiceCode, label: string) => Alert.alert(agentServiceLabels[locale][0], label, [
    { text: copy.close, style: 'cancel' },
    { text: copy.confirm, onPress: async () => {
      if (!live || !reservationId || !allowed || user?.role !== 'AGENT' ||
        showroom || serverAuthMode === 'shared_auth_preview' || busyLock.current || serviceLocked || !agentIdentity) return;
      busyLock.current = true;
      setBusy(true);
      setServiceMessage('');
      let recorded = false;
      try {
        await beginPendingAgentService(agentIdentity.hotelId, agentIdentity.userId, reservationId, service);
        recorded = true;
        await agentPending.reload();
        await live.addAgentGuestService(reservationId, service);
        await clearPendingAgentService(agentIdentity.hotelId, agentIdentity.userId);
        await agentPending.reload();
        setServiceMessage(copy.confirmed + ' · ' + label);
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
      {agentPending.data ? <Text style={[font.small,{color:c.text}]}>{agentPending.data.serviceCode} · {agentPending.data.reservationId}</Text> : null}
      <Text style={[font.small,{color:c.text}]}>{agentReconcileCopy[locale].warning}</Text>
      <Button label={copy.retry} disabled={busy} variant="secondary" onPress={() => void agentPending.reload()}/>
      {agentPending.data ? <Button testID="agent-service-acknowledge" label={agentReconcileCopy[locale].action}
        disabled={busy} variant="secondary" onPress={acknowledgeAgentService}/> : null}
    </GlassCard> : null}
      {reservationId ? <>
        <Button label={agentServiceLabels[locale][0]} variant="secondary" disabled={busy || serviceLocked} onPress={() => setServiceOpen(!serviceOpen)}/>
        {serviceOpen ? AGENT_SERVICES.map((service, index) => <Button key={service}
          label={agentServiceLabels[locale][index + 1]} variant="secondary" disabled={busy || serviceLocked}
          onPress={() => addService(service, agentServiceLabels[locale][index + 1])}/>) : null}
        {serviceLocked ? <Text accessibilityRole="alert" style={[font.body, { color: c.warning }]}>{copy.resultUnknown} · {agentReconcileCopy[locale].warning}</Text> : null}
        {serviceMessage ? <Text accessibilityRole="alert" style={[font.body, { color: c.text }]}>{serviceMessage}</Text> : null}
      </> : null}
  </>;
}
