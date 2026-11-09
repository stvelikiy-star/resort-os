import React, { useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ChevronLeft } from 'lucide-react-native';
import { Badge, Button, Empty, Field, PressScale, SectionLabel } from '../src/components/ui';
import { AGENT_SERVICES, AgentServiceCode, BookingDraft, BookingPreview, localDate, useLiveModules } from '../src/api/liveModules';
import { ApiError } from '../src/api/types';
import { acknowledgePendingBooking, clearPendingBooking, finishPendingBooking, readPendingBooking, recordPendingBooking } from '../src/lib/pendingBooking';
import { wasWriteRejected } from '../src/lib/writeOutcome';
import { beginPendingAgentService, clearPendingAgentService, readPendingAgentService } from '../src/lib/pendingAgentService';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { useSession } from '../src/state/session';
import { canCreateBooking } from '../src/roles/bookingAccess';
import { demoGrid } from '../src/api/demoPresentation';
import { hasTabForSession } from '../src/roles/registry';
import { useAsync } from '../src/lib/useAsync';
import { useTheme } from '../src/theme/ThemeProvider';
import { FutureScreen, GlassCard, PremiumHeader, LoadingShimmer, ErrorState } from '../src/components/Future';
import { font, space } from '../src/theme/tokens';

const reviewCopy = {
  ru: { review: 'Сверить с шахматкой', missing: 'Номер или запись больше недоступны.', storage: 'Журнал брони недоступен. Повторить проверку.', candidate: 'Возможная бронь: ', unconfirmed: 'В шахматке нет подтверждённого совпадения. Проверьте список броней в платформе.', ack: 'Я сверил бронь в платформе', manual: 'Подтвердите, что проверили результат в платформе и решили, нужна ли новая бронь.' },
  en: { review: 'Check PMS grid', missing: 'The room or record is no longer available.', storage: 'Booking journal unavailable. Retry the check.', candidate: 'Possible booking: ', unconfirmed: 'The grid did not confirm a match. Check reservations in the platform.', ack: 'I checked the platform', manual: 'Confirm that you checked the outcome in the platform and decided whether a new booking is needed.' },
  kg: { review: 'Шахматкадан текшерүү', missing: 'Бөлмө же жазуу жеткиликсиз.', storage: 'Бронь журналы жеткиликсиз. Кайра текшериңиз.', candidate: 'Мүмкүн болгон бронь: ', unconfirmed: 'Дал келген бронь ырасталган жок. Платформадан текшериңиз.', ack: 'Платформадан текшердим', manual: 'Платформадан жыйынтыкты текшерип, жаңы бронь керекпи чечкениңизди ырастаңыз.' },
  kz: { review: 'Шахматкадан тексеру', missing: 'Бөлме немесе жазба қолжетімсіз.', storage: 'Бронь журналы қолжетімсіз. Қайта тексеріңіз.', candidate: 'Ықтимал бронь: ', unconfirmed: 'Сәйкестік расталмады. Платформадан тексеріңіз.', ack: 'Платформадан тексердім', manual: 'Нәтижені платформадан тексеріп, жаңа бронь қажет пе екенін шешкеніңізді растаңыз.' },
};

const agentServiceLabels = {
  ru: ['Добавить услугу', 'Трансфер', 'Питание', 'Парковка', 'Сауна', 'Бильярд', 'Экскурсия'],
  en: ['Add service', 'Transfer', 'Meals', 'Parking', 'Sauna', 'Billiards', 'Excursion'],
  kg: ['Кызмат кошуу', 'Трансфер', 'Тамактануу', 'Унаа токтотуучу жай', 'Сауна', 'Бильярд', 'Экскурсия'],
  kz: ['Қызмет қосу', 'Трансфер', 'Тамақтану', 'Автотұрақ', 'Сауна', 'Бильярд', 'Экскурсия'],
} as const;

function dateValid(value: string) { return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + 'T12:00:00')); }
export default function NewBooking() {
  const { user, hotel } = useSession();
  const journalKey = user && hotel && !hotel.demo
    ? ['marina.pending-booking.v1', hotel.id, user.tenant_id ?? '', user.property_id ?? user.property_code]
      .map(part => encodeURIComponent(part).replace(/%/g, '_')).join('.') : null;
  return <BookingForm key={journalKey ?? 'none'} journalKey={journalKey}/>;
}

function BookingForm({ journalKey }: { journalKey: string | null }) {
  const live = useLiveModules();
  const { user, locale, hotel, api, serverAuthMode } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = showroom ? !!user && hasTabForSession(user.role, user.module_permissions, 'DEMO', 'pms') : canCreateBooking(user);
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ room_id?: string; check_in?: string; check_out?: string }>();
  const selectedStart = typeof params.check_in === 'string' ? params.check_in : '';
  const selectedEnd = typeof params.check_out === 'string' ? params.check_out : '';
  const validSelection = dateValid(selectedStart) && dateValid(selectedEnd) &&
    selectedStart >= localDate() && selectedStart < selectedEnd &&
    (Date.parse(selectedEnd + 'T12:00:00') - Date.parse(selectedStart + 'T12:00:00')) / 86400000 <= 60;
  const selectedRoom = typeof params.room_id === 'string' && (showroom || /^[0-9a-f]{8}-[0-9a-f-]{27,}$/i.test(params.room_id))
    ? params.room_id : '';
  const [start, setStart] = useState(() => validSelection ? selectedStart : localDate(1));
  const [end, setEnd] = useState(() => validSelection ? selectedEnd : localDate(2));
  const [roomId, setRoomId] = useState(() => validSelection ? selectedRoom : '');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [adults, setAdults] = useState('2');
  const [children, setChildren] = useState('0');
  const [preview, setPreview] = useState<BookingPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reservationId, setReservationId] = useState<string | null>(null);
  const [serviceOpen, setServiceOpen] = useState(false);
  const [serviceMessage, setServiceMessage] = useState('');
  const [serviceUnknown, setServiceUnknown] = useState(false);
  const agentIdentity = user?.role === 'AGENT' && hotel?.id && user.id
    ? { hotelId: hotel.id, userId: user.id } : null;
  const agentPending = useAsync(() => agentIdentity
    ? readPendingAgentService(agentIdentity.hotelId, agentIdentity.userId) : Promise.resolve(null),
    [agentIdentity?.hotelId, agentIdentity?.userId]);
  const serviceLocked = serviceUnknown || agentPending.loading || !!agentPending.error || !!agentPending.data;
  const [result, setResult] = useState<string | null>(null);
  const journal = useAsync(() => journalKey ? readPendingBooking(journalKey) : Promise.resolve(null), [journalKey]);
  const [readback, setReadback] = useState<string | null>(null);
  const [unknown, setUnknown] = useState(false);
  const lockedForReview = unknown || !!journal.data || !!journal.error || journal.loading || (!journalKey && !showroom);
  const [completed, setCompleted] = useState(false);
  const busyLock = useRef(false);
  const [busy, setBusy] = useState(false);
  const validDates = dateValid(start) && dateValid(end) && start < end && (Date.parse(end + 'T12:00:00') - Date.parse(start + 'T12:00:00')) / 86400000 <= 60;
  const { data: grid, loading, error: gridError, reload } = useAsync(async () => {
    if (!allowed || !validDates) return null;
    if (showroom) return demoGrid(locale, await api.listRooms(), hotel?.name ?? 'DEMO');
    return live ? live.pmsGrid(start, end) : null;
  }, [api, live, start, end, validDates, allowed, showroom, locale, hotel?.name]);
  const draft = (): BookingDraft => ({ room_id: roomId, check_in: start, check_out: end,
    adults: Number(adults), children: Number(children), guest_phone: phone.trim() });
  const resetPreview = () => { setPreview(null); setError(null); };
  const resetForm = () => {
    setReservationId(null); setServiceOpen(false); setServiceMessage(''); setServiceUnknown(false);
    setCompleted(false); setUnknown(false); setResult(null); setError(null); setPreview(null);
    setStart(localDate(1)); setEnd(localDate(2)); setRoomId(''); setName(''); setPhone(''); setAdults('2'); setChildren('0');
  };
  const validate = () => validDates && roomId && name.trim().length >= 2 && phone.trim().length >= 5 && Number.isInteger(Number(adults)) && Number(adults) >= 1 && Number(adults) <= 20 && Number.isInteger(Number(children)) && Number(children) >= 0 && Number(children) <= 20;
  const doPreview = async () => {
    if (!allowed || !live || !validate() || busyLock.current || lockedForReview || completed) return;
    busyLock.current = true; setBusy(true); setError(null); setPreview(null);
    try { setPreview(await live.bookingPreview(draft())); }
    catch(e) { setError(e instanceof Error ? e.message : copy.unknown); }
    finally { busyLock.current = false; setBusy(false); }
  };
  const doCommit = () => Alert.alert(copy.confirm, copy.total + ': ' + preview?.pricing.total_kgs + ' KGS', [{text: copy.close,style:'cancel'}, {text:copy.commit,onPress: async () => {
    if (!allowed || !live || !journalKey || !preview?.can_commit || !preview.pricing.total_kgs || busyLock.current || lockedForReview || completed) return;
    busyLock.current = true; setBusy(true); setError(null);
    const payload = { ...draft(), guest_name: name.trim(), phone: phone.trim(),
      expected_total_kgs: preview.pricing.total_kgs, expected_pricing_source: preview.pricing.source };
    let recorded = false;
    try {
      try {
        const { room_id, check_in, check_out } = payload;
        recorded = await recordPendingBooking(journalKey, { room_id, check_in, check_out });
      } catch {
        setError(reviewCopy[locale].storage);
      }
      if (!recorded) {
        await journal.reload();
        return;
      }
      try {
        const saved = await live.bookingCommit(payload);
        setReservationId(saved.reservation_id);
        setResult(saved.booking_number + ' · ' + saved.total_kgs + ' KGS');
        setPreview(null);
        setCompleted(true);
        await clearPendingBooking(journalKey).catch(() => journal.reload());
      } catch (e) {
        const knownRejected = wasWriteRejected(e);
        setUnknown(!knownRejected);
        const code = e instanceof ApiError ? e.code : null;
        setError(!knownRejected ? copy.resultUnknown : code === 'FORBIDDEN' ? copy.denied
          : code === 'NOT_FOUND' ? reviewCopy[locale].missing : code === 'CONFLICT' ? copy.conflict : copy.unknown);
        setPreview(null);
        if (knownRejected) await clearPendingBooking(journalKey).catch(() => {});
        await journal.reload();
      }
    } finally {
      if (recorded) finishPendingBooking(journalKey);
      busyLock.current = false; setBusy(false);
    }
  }}]);
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
        const rejected = recorded && wasWriteRejected(error);
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
  const reconcile = async () => {
    const pending = journal.data;
    if (!live || !pending || busyLock.current) return;
    busyLock.current = true; setBusy(true); setReadback(null);
    try {
      const current = await live.pmsGrid(pending.check_in, pending.check_out);
      const room = current.rooms.find(item => item.id === pending.room_id);
      const matches = room?.blocks.filter(block => block.reservation_id &&
        block.start === pending.check_in && block.end === pending.check_out) ?? [];
      const numbers = matches.flatMap(block => block.booking_number ? [block.booking_number] : []);
      setReadback(numbers.length ? reviewCopy[locale].candidate + numbers.join(', ') : reviewCopy[locale].unconfirmed);
    } catch { setError(copy.unknown); }
    finally { busyLock.current = false; setBusy(false); }
  };
  const acknowledge = () => Alert.alert(reviewCopy[locale].review, reviewCopy[locale].manual, [
    { text: copy.close, style: 'cancel' },
    { text: copy.confirm, onPress: async () => {
      if (!journalKey || !journal.data || busyLock.current) return;
      busyLock.current = true; setBusy(true);
      try {
        // Only release the exact journal record the operator inspected.
        if (!await acknowledgePendingBooking(journalKey, journal.data)) {
          setReadback(null);
          return;
        }
        setUnknown(false); setReadback(null); setError(null); setPreview(null);
      } catch { setError(reviewCopy[locale].storage); }
      finally { await journal.reload(); busyLock.current = false; setBusy(false); }
    }},
  ]);
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PressScale onPress={() => router.back()} style={{ minHeight: 44, flexDirection: 'row', alignItems: 'center' }}><ChevronLeft color={c.primary} size={24}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <PremiumHeader title={{ ru: 'Предварительное бронирование', en: 'Booking preview', kg: 'Алдын ала брондоо', kz: 'Алдын ала брондау' }[locale]} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
    {showroom ? <Empty text={copy.demoOnlyCard}/> : !live ? <Empty text={copy.unavailable}/> : null}
    <Field label={copy.start + ' · ' + copy.dateFormat} value={start} onChangeText={v => {setStart(v);setRoomId('');resetPreview();}} autoCapitalize="none"/>
    <Field label={copy.end + ' · ' + copy.dateFormat} value={end} onChangeText={v => {setEnd(v);setRoomId('');resetPreview();}} autoCapitalize="none"/>
    <SectionLabel>{copy.rooms}</SectionLabel>
    {loading ? <LoadingShimmer count={2}/> : null}
    {gridError ? <ErrorState text={gridError.message} retry={copy.retry} onRetry={reload}/> : null}
    <View style={{ flexDirection:'row',flexWrap:'wrap',gap:space.sm }}>
      {(grid?.rooms ?? []).map(room => {
        const available = !room.blocks.some(block => block.start < end && start < block.end) && room.operational_state !== 'TECH_BLOCK';
        return <PressScale key={room.id} testID={'booking-room-' + room.id} disabled={!available || lockedForReview || completed}
          onPress={() => {setRoomId(room.id);resetPreview();}}
          style={{ minWidth: 90,minHeight:48,borderRadius:12,padding:12,backgroundColor: roomId === room.id ? c.primary : c.surfaceAlt,opacity:available?1:0.45,alignItems:'center',justifyContent:'center' }}>
          <Text style={[font.h2,{color:roomId === room.id?c.primaryText:c.text}]}>{room.code}</Text>
        </PressScale>;
      })}
    </View>
    <Field label={copy.guestName} value={name} onChangeText={v=>{setName(v);resetPreview();}} maxLength={160}/>
    <Field label={copy.phone} value={phone} onChangeText={v=>{setPhone(v);resetPreview();}} keyboardType="phone-pad" maxLength={40}/>
    <View style={{flexDirection:'row',gap:space.sm}}>
      <View style={{flex:1}}><Field label={copy.adults} value={adults} onChangeText={v=>{setAdults(v);resetPreview();}} keyboardType="number-pad"/></View>
      <View style={{flex:1}}><Field label={copy.children} value={children} onChangeText={v=>{setChildren(v);resetPreview();}} keyboardType="number-pad"/></View>
    </View>
    <Button testID="booking-preview" label={copy.preview} disabled={!live || !validate() || busy || lockedForReview || completed} onPress={() => void doPreview()}/>
    {preview ? <GlassCard style={{gap:8,borderLeftWidth:4,borderLeftColor:preview.can_commit?c.success:c.danger}}>
      <Text style={[font.h2,{color:c.text}]}>{preview.room.code} · {preview.nights} {copy.nights}</Text>
      <Badge label={preview.pricing.source} tone="primary"/>
      <Text style={[font.title,{color:c.text}]}>{preview.pricing.total_kgs === null ? '—' : preview.pricing.total_kgs.toLocaleString('ru-RU') + ' KGS'}</Text>
      {preview.pricing.discount_percent ? <Text style={[font.small,{color:c.textMuted}]} >{copy.discount}: {preview.pricing.discount_percent}%</Text> : null}
      {!preview.can_commit ? <Text style={[font.body,{color:c.danger}]}>{copy.conflict} · {preview.pricing.reason || ''}</Text> : null}
      <Button testID="booking-commit" label={copy.commit} disabled={!preview.can_commit || busy || lockedForReview || completed} onPress={doCommit}/>
    </GlassCard> : null}
    {result ? <GlassCard style={{gap:8,borderLeftWidth:4,borderLeftColor:c.success}}><Text style={[font.h2,{color:c.success}]}>{copy.confirmed}: {result}</Text>
      {user?.role === 'AGENT' && live && reservationId && serverAuthMode !== 'shared_auth_preview' ? <>
        <Button label={agentServiceLabels[locale][0]} variant="secondary" disabled={busy || serviceLocked} onPress={() => setServiceOpen(!serviceOpen)}/>
        {serviceOpen ? AGENT_SERVICES.map((service, index) => <Button key={service}
          label={agentServiceLabels[locale][index + 1]} variant="secondary" disabled={busy || serviceLocked}
          onPress={() => addService(service, agentServiceLabels[locale][index + 1])}/>) : null}
        {serviceLocked ? <Text accessibilityRole="alert" style={[font.body, { color: c.warning }]}>{copy.resultUnknown} · {reviewCopy[locale].manual}</Text> : null}
        {serviceMessage ? <Text accessibilityRole="alert" style={[font.body, { color: c.text }]}>{serviceMessage}</Text> : null}
      </> : null}
      <Button testID="booking-create-another" label={copy.anotherBooking} variant="secondary" disabled={busy} onPress={resetForm}/>
    </GlassCard> : null}
    {error ? <GlassCard><Text accessibilityRole="alert" style={[font.body,{color:c.danger}]}>{error}</Text></GlassCard> : null}
    {journal.error ? <Button label={reviewCopy[locale].storage} onPress={journal.reload}/> : null}
    {journal.data ? <GlassCard style={{ gap: 8, borderLeftWidth:4,borderLeftColor:c.warning }}>
      <Text style={[font.small,{color:c.warning}]}>{copy.resultUnknown}</Text>
      <Button testID="booking-reconcile" label={reviewCopy[locale].review} disabled={busy} onPress={() => void reconcile()}/>
      {readback ? <><Text style={[font.body,{color:c.text}]}>{readback}</Text>
        <Button label={reviewCopy[locale].ack} disabled={busy} onPress={acknowledge}/></> : null}
    </GlassCard> : null}
  </FutureScreen>;
}
