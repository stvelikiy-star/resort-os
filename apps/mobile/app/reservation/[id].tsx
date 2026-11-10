import React, { useRef, useState } from 'react';
import { Alert, Linking, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { BedDouble, CalendarDays, ChevronLeft, KeyRound, Mail, Phone, Wallet } from 'lucide-react-native';
import { Badge, Button, Card, Empty, Field, PressScale, Screen } from '../../src/components/ui';
import { SchedulePreview, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { reservationAmount, reservationGuestName, reservationRoomStateLabel, reservationStatusLabel, reservationTelephone } from '../../src/roles/reservationPresentation';
import { canReadFinance } from '../../src/api/financeAccess';
import { GlassCard, PremiumHeader } from '../../src/components/Future';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function ReservationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useSession();
  const allowed = !!user && ['OWNER','MANAGER','RECEPTION'].includes(user.role) && !!user.module_permissions?.includes('RESERVATIONS');
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [editingDates, setEditingDates] = useState(false);
  const [newStart, setNewStart] = useState('');
  const [newEnd, setNewEnd] = useState('');
  const [datesPreview, setDatesPreview] = useState<SchedulePreview | null>(null);
  const [datesBusy, setDatesBusy] = useState(false);
  const [datesUnknown, setDatesUnknown] = useState(false);
  const dateLock = useRef(false);
  const { data, loading, error, reload } = useAsync<Record<string, unknown> | null>(() => allowed && live && id ? live.reservation(id) : Promise.resolve(null), [live, id, user?.id, allowed]);
  const act = (kind: 'in' | 'out') => Alert.alert(copy.confirm, '', [{ text: copy.close, style: 'cancel' }, { text: copy.choose, onPress: async () => {
    if (locked.current || unknownResult || !allowed || !live || !id) return;
    locked.current = true; setBusy(true); setFeedback(null);
    try { await (kind === 'in' ? live.checkIn(id) : live.checkOut(id)); setFeedback(copy.confirmed); await reload(); }
    catch (error: unknown) {
      const rejected = wasWriteRejected(error);
      if (!rejected) setUnknownResult(true);
      setFeedback(rejected ? copy.conflict : copy.resultUnknown);
    }
    finally { locked.current = false; setBusy(false); }
  }}]);
  const segments = Array.isArray(data?.schedule) ? data.schedule as Record<string, unknown>[] : [];
  const oneRoom = segments.length === 1 && typeof segments[0].room_id === 'string';
  const roomId = oneRoom ? String(segments[0].room_id) : null;
  const canEditDates = allowed && !!live && !!user && ['OWNER','MANAGER'].includes(user.role) &&
    !!user.module_permissions?.includes('PMS') && oneRoom &&
    ['GUARANTEED','CHECKED_IN'].includes(String((data?.reservation as Record<string,unknown> | undefined)?.status ?? ''));
  const validDates = /^\d{4}-\d{2}-\d{2}$/.test(newStart) && /^\d{4}-\d{2}-\d{2}$/.test(newEnd) &&
    newStart < newEnd;
  const previewDateChange = async () => {
    if (!canEditDates || !roomId || !id || !validDates || dateLock.current || datesUnknown) return;
    dateLock.current = true; setDatesBusy(true); setFeedback(null); setDatesPreview(null);
    try {
      const result = await live!.schedulePreview(id,[{room_id:roomId,start:newStart,end:newEnd}]);
      setDatesPreview(result);
      if (!result.can_commit) setFeedback(copy.scheduleConflict);
    } catch (error:unknown) {
      setFeedback(wasWriteRejected(error) ? copy.scheduleConflict : copy.resultUnknown);
    } finally { dateLock.current = false; setDatesBusy(false); }
  };
  const commitDateChange = () => Alert.alert(copy.confirm, copy.scheduleWarning, [
    {text:copy.close,style:'cancel'},
    {text:copy.choose,onPress:()=>{void (async()=>{
      if (!canEditDates || !roomId || !id || !validDates || !datesPreview?.can_commit ||
          datesPreview.proposed_check_in !== newStart || datesPreview.proposed_check_out !== newEnd ||
          dateLock.current || datesUnknown) return;
      const expectedVersion = datesPreview.reservation.version;
      dateLock.current = true;setDatesBusy(true);setFeedback(null);
      try {
        await live!.scheduleCommit(id,[{room_id:roomId,start:newStart,end:newEnd}],expectedVersion);
        setDatesPreview(null);setEditingDates(false);setFeedback(copy.confirmed);
        await reload();
      } catch (error:unknown) {
        if (!wasWriteRejected(error)) setDatesUnknown(true);
        setDatesPreview(null);
        setFeedback(wasWriteRejected(error) ? copy.scheduleConflict : copy.resultUnknown);
      } finally {dateLock.current=false;setDatesBusy(false);}
    })();}},
  ]);
  if (!allowed)
    return <Screen><Empty text={copy.denied}/></Screen>;
  const x = (data?.reservation && typeof data.reservation === 'object' ? data.reservation as Record<string, unknown> : {}) as Record<string, unknown>;
  const guest = (data?.guest && typeof data.guest === 'object' ? data.guest as Record<string, unknown> : {}) as Record<string, unknown>;
  const room = (data?.room && typeof data.room === 'object' ? data.room as Record<string, unknown> : {}) as Record<string, unknown>;
  const finance = (data?.finance && typeof data.finance === 'object' ? data.finance as Record<string, unknown> : {}) as Record<string, unknown>;
  const text = (obj: Record<string, unknown>, k: string) => typeof obj[k] === 'string' || typeof obj[k] === 'number' ? String(obj[k]) : '—';
  const guestName = reservationGuestName(guest.first_name, guest.last_name, copy.guest);
  const phone = reservationTelephone(guest.phone);
  const email = typeof guest.email === 'string' && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(guest.email.trim()) ? guest.email.trim() : null;
  const roomTitle = [room.code, room.room_type_name].filter((v): v is string => typeof v === 'string' && !!v.trim()).join(' · ');
  const canFinance = !!user && canReadFinance(user);
  const money = (key: string) => reservationAmount(finance[key]);
  return <Screen>
    <PressScale onPress={() => router.back()} style={{ minHeight: 44, flexDirection: 'row', gap: 5, alignItems: 'center' }}><ChevronLeft color={c.primary} size={22}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <PremiumHeader title={copy.bookings} subtitle={text(x, 'booking_number')} eyebrow="MARINA SMART"/>
    {loading ? <Empty text={copy.loading}/> : null}
    {error ? <Card onPress={reload}><Text accessibilityRole="alert" style={[font.body, { color: c.danger }]}>{error.message} · {copy.retry}</Text></Card> : null}
    {data ? <>
      <GlassCard testID="reservation-guest-summary" style={{ gap: space.md, padding: space.lg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
          <View style={{ width: 48, height: 48, borderRadius: 15, alignItems: 'center',
            justifyContent: 'center', backgroundColor: c.primarySoft }}>
            <KeyRound size={23} color={c.primary}/>
          </View>
          <View style={{ flex: 1, minWidth: 0, gap: 5 }}>
            <Text style={[font.h2, { color: c.text }]} numberOfLines={2}>{guestName}</Text>
            <Text style={[font.small, { color: c.textMuted }]}>{copy.bookings} · {text(x, 'booking_number')}</Text>
          </View>
        </View>
        <Badge label={reservationStatusLabel(text(x, 'status'), copy)} tone="info"/>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <CalendarDays size={20} color={c.cyan}/>
          <Text style={[font.body, { color: c.text, flex: 1 }]}>{text(x, 'check_in')} → {text(x, 'check_out')}</Text>
        </View>
        {roomTitle ? <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <BedDouble size={20} color={c.cyan}/>
          <Text style={[font.body, { color: c.text, flex: 1 }]} numberOfLines={2}>{roomTitle}</Text>
        </View> : null}
        {typeof room.state === 'string' && room.state.trim() ?
          <Text style={[font.small, { color: c.textMuted }]}>{copy.roomCondition}: {reservationRoomStateLabel(room.state, copy)}</Text> : null}
        {phone ? <Button testID="reservation-call-guest" label={copy.callGuest} icon={Phone}
          variant="secondary" onPress={() => void Linking.openURL(phone)}/> : null}
        {email ? <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Mail size={19} color={c.textMuted}/><Text selectable style={[font.small, { color: c.text, flex: 1 }]}>{email}</Text>
        </View> : null}
      </GlassCard>
      {canFinance && (money('total_kgs') || money('paid_kgs') || money('remaining_kgs')) ? <GlassCard
        testID="reservation-finance" style={{ gap: space.sm, padding: space.lg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Wallet size={21} color={c.gold}/><Text style={[font.h2, { color: c.text }]}>{copy.financeTitle}</Text>
        </View>
        {money('total_kgs') ? <Text style={[font.body, { color: c.text }]}>{copy.total}: {money('total_kgs')}</Text> : null}
        {money('paid_kgs') ? <Text style={[font.body, { color: c.text }]}>{copy.financeReceived}: {money('paid_kgs')}</Text> : null}
        {money('remaining_kgs') ? <Text style={[font.body, { color: c.text }]}>{copy.financeDebt}: {money('remaining_kgs')}</Text> : null}
        <Text style={[font.small, { color: c.textMuted }]}>{copy.paymentsNotProfit}</Text>
      </GlassCard> : null}
      {text(x, 'status') === 'GUARANTEED' ? <Button testID="reservation-checkin" label={copy.checkIn} disabled={busy || unknownResult} onPress={() => act('in')}/> : null}
      {text(x, 'status') === 'CHECKED_IN' ? <Button testID="reservation-checkout" label={copy.checkOut} disabled={busy || unknownResult} onPress={() => act('out')}/> : null}
      {canEditDates ? <Card style={{ gap: space.md }}>
        <Button testID="reservation-edit-dates" label={copy.scheduleEdit} variant="secondary" disabled={datesBusy || datesUnknown}
          onPress={() => { setNewStart(text(x,'check_in'));setNewEnd(text(x,'check_out'));setDatesPreview(null);setEditingDates(!editingDates); }}/>
        {editingDates ? <>
          <Field testID="schedule-new-start" label={copy.scheduleStart} value={newStart}
            onChangeText={value => {setNewStart(value);setDatesPreview(null);}} autoCapitalize="none"/>
          <Field testID="schedule-new-end" label={copy.scheduleEnd} value={newEnd}
            onChangeText={value => {setNewEnd(value);setDatesPreview(null);}} autoCapitalize="none"/>
          <Text style={[font.small,{color:c.textMuted}]}>{copy.scheduleWarning}</Text>
          <Button testID="schedule-preview" label={copy.schedulePreview} disabled={!validDates || datesBusy || datesUnknown}
            onPress={() => void previewDateChange()}/>
          {datesPreview ? <>
            <Text style={[font.body,{color:datesPreview.can_commit?c.success:c.warning}]}>
              {datesPreview.proposed_check_in} → {datesPreview.proposed_check_out}
            </Text>
            {datesPreview.can_commit ?
              <Button testID="schedule-commit" label={copy.scheduleApply} disabled={datesBusy || datesUnknown} onPress={commitDateChange}/>
              : <Text accessibilityRole="alert" style={[font.body,{color:c.danger}]}>{copy.scheduleConflict}</Text>}
          </> : null}
        </> : null}
      </Card> : allowed && user && ['OWNER','MANAGER'].includes(user.role) && data && !oneRoom ?
        <Text style={[font.small,{color:c.textMuted}]}>{copy.scheduleUnavailable}</Text> : null}
      <Text style={[font.small, { color: c.textMuted }]}>{copy.readOnly} · {copy.paymentsNotProfit}</Text>
      {feedback ? <Card><Text accessibilityRole="alert" testID={unknownResult ? 'reservation-unknown-result' : 'reservation-feedback'} style={[font.body, { color: unknownResult ? c.warning : c.text }]}>{feedback}</Text></Card> : null}
    </> : null}
  </Screen>;
}
