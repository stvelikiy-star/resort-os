import React from 'react';
import { Linking, Pressable, ScrollView, Text, View, useWindowDimensions } from 'react-native';
import { CalendarDays, ChevronRight, Phone, UserRound, X } from 'lucide-react-native';
import type { GridBlock, GridRoom, useLiveModules } from '../api/liveModules';
import type { GridCellState } from '../roles/pmsPresentation';
import { useAsync } from '../lib/useAsync';
import { useMobileCopy } from '../i18n/mobileCopy';
import { reservationGuestName, reservationRoomStateLabel, reservationStatusLabel, reservationTelephone } from '../roles/reservationPresentation';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space } from '../theme/tokens';
import { Badge, Button, Empty } from './ui';
import { AnimatedSheet, ConfirmedChange } from './Motion';

export interface PmsSelectedBlock { room: GridRoom; block: GridBlock; state: GridCellState }
interface Props {
  selected: PmsSelectedBlock | null;
  showroom: boolean;
  live: ReturnType<typeof useLiveModules>;
  canOpenDetails: boolean;
  onClose: () => void;
  onOpen: (reservationId: string) => void;
}
function readObject(input: unknown): Record<string, unknown> {
  return input && typeof input === 'object' ? input as Record<string, unknown> : {};
}
function readValue(input: unknown): string | null {
  return typeof input === 'string' && input.trim() ? input.trim() : null;
}
/** Uses the existing server-authenticated reservation detail API only.
 * Never infers a guest phone or chat ID from PMS grid cells. */
export function PmsBookingSheet({ selected, showroom, live, canOpenDetails, onClose, onOpen }: Props) {
  const { c } = useTheme();
  const copy = useMobileCopy();
  const { height: windowHeight } = useWindowDimensions();
  const id = selected?.state === 'RESERVATION' ? selected.block.reservation_id : null;
  const details = useAsync<Record<string, unknown> | null>(
    () => id && live && !showroom && canOpenDetails ? live.reservation(id) : Promise.resolve(null),
    [id, live, showroom, canOpenDetails],
  );
  const record = readObject(details.data);
  const reservation = readObject(record.reservation);
  const guest = readObject(record.guest);
  const room = selected?.room;
  const block = selected?.block;
  const name = reservationGuestName(guest.first_name, guest.last_name, block?.guest_name || copy.guest);
  const phone = !showroom ? readValue(guest.phone) : null;
  const dial = !showroom ? reservationTelephone(phone) : null;
  const email = !showroom ? readValue(guest.email) : null;
  const source = !showroom ? readValue(readObject(record.source).channel) : null;

  const isReservation = selected?.state === 'RESERVATION';
  const status = reservationStatusLabel(readValue(reservation.status) || selected?.state || '—', copy);
  const roomName = [room?.code, room?.name?.trim() || room?.room_type_name].filter(Boolean).join(' · ');
  return <AnimatedSheet visible={!!selected} onRequestClose={onClose} closeLabel={copy.close}>
      <View testID="pms-booking-sheet" style={{
        backgroundColor: c.surface, borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl,
        borderColor: c.border, borderWidth: 1, paddingHorizontal: space.xl, paddingTop: space.lg,
        paddingBottom: 32, maxHeight: Math.round(windowHeight * 0.8),
      }}>
        <View style={{ width: 44, height: 5, borderRadius: 3, backgroundColor: c.border, alignSelf: 'center', marginBottom: space.md }}/>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm, marginBottom: space.md }}>
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text style={[font.label,{color:c.cyan}]}>{roomName || '—'} · {block?.booking_number || copy.pms}</Text>
            <Text style={[font.h2,{color:c.text, marginTop: 5}]} numberOfLines={2}>
              {isReservation ? name : selected?.state === 'HOLD' ? copy.holds : selected?.state === 'CONFLICT' ? copy.conflict : copy.blocked}
            </Text>
          </View>
          <Pressable testID="pms-sheet-close" accessibilityRole="button" accessibilityLabel={copy.close}
            onPress={onClose} style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center',
            backgroundColor: c.surfaceAlt, borderRadius: radius.md }}>
            <X size={23} color={c.text}/>
          </Pressable>
        </View>
        <ScrollView showsVerticalScrollIndicator contentContainerStyle={{gap:space.md}}>
          {showroom ? <Badge label={copy.demoLabel} tone="warning"/> : null}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <CalendarDays size={20} color={c.primary}/>
            <Text style={[font.body,{color:c.text, flex:1}]}>{block?.start || '—'} → {block?.end || '—'}</Text>
          </View>
          <ConfirmedChange value={status} style={{ alignSelf: 'stretch' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <UserRound size={20} color={c.primary}/>
              <Text style={[font.body,{color:c.text, flex:1}]}>{copy.status}: {status}</Text>
            </View>
          </ConfirmedChange>
          {room?.operational_state ? <Text style={[font.small,{color:c.textMuted}]}>
            {copy.roomCondition}: {reservationRoomStateLabel(room.operational_state, copy)}
          </Text> : null}
          {details.loading ? <Text style={[font.small,{color:c.textMuted}]}>{copy.loading}</Text> : null}
          {details.error ? <Text accessibilityRole="alert" style={[font.small,{color:c.danger}]}>
            {details.error.message} · {copy.retry}
          </Text> : null}
          {isReservation ? <>
            <View style={{backgroundColor:c.surfaceAlt,borderRadius:radius.md,padding:space.md,gap:space.sm}}>
              <Text style={[font.small,{color:c.textMuted}]}>{copy.guestName}</Text>
              <Text style={[font.h2,{color:c.text}]}>{name}</Text>
              <Text style={[font.small,{color:c.textMuted}]}>{copy.phone}</Text>
              <Text style={[font.body,{color:c.text}]}>{phone ?? '—'}</Text>
              {email ? <><Text style={[font.small,{color:c.textMuted}]}>{copy.guestEmail}</Text>
                <Text style={[font.body,{color:c.text}]}>{email}</Text></> : null}
              {source ? <><Text style={[font.small,{color:c.textMuted}]}>{copy.bookingSource}</Text>
                <Text style={[font.body,{color:c.text}]}>{source}</Text></> : null}
              {readValue(reservation.booking_number) ? <Text style={[font.small,{color:c.textMuted}]}>
                {copy.bookings}: {String(reservation.booking_number)}
              </Text> : null}
            </View>
            {dial ? <Button testID="pms-call-guest" label={copy.callGuest} icon={Phone}
              variant="secondary" onPress={() => void Linking.openURL(dial)}/> : null}
            {!showroom && id && canOpenDetails ? <Button testID="pms-open-booking" label={copy.openBooking}
              icon={ChevronRight} disabled={details.loading || !!details.error} onPress={() => { onClose(); onOpen(id); }}/> : null}
          </> : <Empty text={copy.pmsUnavailableAction}/>}
          {showroom ? <Text style={[font.small,{color:c.textMuted}]}>{copy.demoOnlyCard}</Text> : null}
        </ScrollView>
      </View>
  </AnimatedSheet>;
}
