import React, { useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ChevronLeft } from 'lucide-react-native';
import { Badge, Button, Card, Empty, Field, PressScale, Screen, SectionLabel, Title } from '../src/components/ui';
import { BookingDraft, BookingPreview, localDate, useLiveModules } from '../src/api/liveModules';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { useSession } from '../src/state/session';
import { useAsync } from '../src/lib/useAsync';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

function dateValid(value: string) { return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value + 'T12:00:00')); }
export default function NewBooking() {
  const live = useLiveModules();
  const { user } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const [start, setStart] = useState(localDate(1));
  const [end, setEnd] = useState(localDate(2));
  const [roomId, setRoomId] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [adults, setAdults] = useState('2');
  const [children, setChildren] = useState('0');
  const [preview, setPreview] = useState<BookingPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [unknown, setUnknown] = useState(false);
  const busyLock = useRef(false);
  const [busy, setBusy] = useState(false);
  const validDates = dateValid(start) && dateValid(end) && start < end && (Date.parse(end + 'T12:00:00') - Date.parse(start + 'T12:00:00')) / 86400000 <= 60;
  const { data: grid, loading, error: gridError, reload } = useAsync(() => live && validDates ? live.pmsGrid(start, end) : Promise.resolve(null), [live, start, end, validDates]);
  const draft = (): BookingDraft => ({ room_id: roomId, check_in: start, check_out: end,
    adults: Number(adults), children: Number(children), guest_phone: phone.trim() });
  const resetPreview = () => { setPreview(null); setError(null); };
  const validate = () => validDates && roomId && name.trim().length >= 2 && phone.trim().length >= 5 && Number.isInteger(Number(adults)) && Number(adults) >= 1 && Number(adults) <= 20 && Number.isInteger(Number(children)) && Number(children) >= 0 && Number(children) <= 20;
  const doPreview = async () => {
    if (!live || !validate() || busyLock.current || unknown) return;
    busyLock.current = true; setBusy(true); setError(null); setPreview(null);
    try { setPreview(await live.bookingPreview(draft())); }
    catch(e) { setError(e instanceof Error ? e.message : copy.unknown); }
    finally { busyLock.current = false; setBusy(false); }
  };
  const doCommit = () => Alert.alert(copy.confirm, copy.total + ': ' + preview?.pricing.total_kgs + ' KGS', [{text: copy.close,style:'cancel'}, {text:copy.commit,onPress: async () => {
    if (!live || !preview?.can_commit || !preview.pricing.total_kgs || busyLock.current || unknown) return;
    busyLock.current = true; setBusy(true); setError(null);
    try {
      const saved = await live.bookingCommit({ ...draft(), guest_name: name.trim(), phone: phone.trim(),
        expected_total_kgs: preview.pricing.total_kgs, expected_pricing_source: preview.pricing.source });
      setResult(saved.booking_number + ' · ' + saved.total_kgs + ' KGS');
      setPreview(null); // A committed booking must not be submitted twice.
      setUnknown(true);
    } catch(e) {
      // A POST may have committed even if its response was lost. Never automatically repeat it.
      setUnknown(true);
      setError(e instanceof Error && /HTTP 409|HTTP 422|HTTP 400|HTTP 403/.test(e.message) ? e.message : copy.resultUnknown);
    } finally { busyLock.current = false; setBusy(false); }
  }}]);
  if (!user || !['OWNER','MANAGER','AGENT'].includes(user.role) || !user.module_permissions?.includes('PMS')) return <Screen><Empty text={copy.denied}/></Screen>;
  return <Screen>
    <PressScale onPress={() => router.back()} style={{ minHeight: 44, flexDirection: 'row', alignItems: 'center' }}><ChevronLeft color={c.primary} size={24}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <Title>{copy.newBooking}</Title>
    {!live ? <Empty text={copy.unavailable}/> : null}
    <Field label={copy.start + ' · ' + copy.dateFormat} value={start} onChangeText={v => {setStart(v);setRoomId('');resetPreview();}} autoCapitalize="none"/>
    <Field label={copy.end + ' · ' + copy.dateFormat} value={end} onChangeText={v => {setEnd(v);setRoomId('');resetPreview();}} autoCapitalize="none"/>
    <SectionLabel>{copy.rooms}</SectionLabel>
    {loading ? <Empty text={copy.loading}/> : null}
    {gridError ? <Card onPress={reload}><Text style={[font.body, { color: c.danger }]}>{gridError.message} · {copy.retry}</Text></Card> : null}
    <View style={{ flexDirection:'row',flexWrap:'wrap',gap:space.sm }}>
      {(grid?.rooms ?? []).map(room => {
        const available = !room.blocks.length && room.operational_state !== 'TECH_BLOCK';
        return <PressScale key={room.id} testID={'booking-room-' + room.id} disabled={!available || unknown}
          onPress={() => {setRoomId(room.id);resetPreview();}}
          style={{ minWidth: 90,minHeight:48,borderRadius:12,padding:12,backgroundColor: roomId === room.id ? c.primary : c.surfaceAlt,opacity:available?1:0.45,alignItems:'center',justifyContent:'center' }}>
          <Text style={[font.h2,{color:roomId === room.id?'#fff':c.text}]}>{room.code}</Text>
        </PressScale>;
      })}
    </View>
    <Field label={copy.guestName} value={name} onChangeText={v=>{setName(v);resetPreview();}} maxLength={160}/>
    <Field label={copy.phone} value={phone} onChangeText={v=>{setPhone(v);resetPreview();}} keyboardType="phone-pad" maxLength={40}/>
    <View style={{flexDirection:'row',gap:space.sm}}>
      <View style={{flex:1}}><Field label={copy.adults} value={adults} onChangeText={v=>{setAdults(v);resetPreview();}} keyboardType="number-pad"/></View>
      <View style={{flex:1}}><Field label={copy.children} value={children} onChangeText={v=>{setChildren(v);resetPreview();}} keyboardType="number-pad"/></View>
    </View>
    <Button testID="booking-preview" label={copy.preview} disabled={!validate() || busy || unknown} onPress={() => void doPreview()}/>
    {preview ? <Card style={{gap:8}}>
      <Text style={[font.h2,{color:c.text}]}>{preview.room.code} · {preview.nights} nights</Text>
      <Badge label={preview.pricing.source} tone="primary"/>
      <Text style={[font.title,{color:c.text}]}>{preview.pricing.total_kgs === null ? '—' : preview.pricing.total_kgs.toLocaleString('ru-RU')} KGS</Text>
      {preview.pricing.discount_percent ? <Text style={[font.small,{color:c.textMuted}]}>Discount: {preview.pricing.discount_percent}%</Text> : null}
      {!preview.can_commit ? <Text style={[font.body,{color:c.danger}]}>{copy.conflict} · {preview.pricing.reason || ''}</Text> : null}
      <Button testID="booking-commit" label={copy.commit} disabled={!preview.can_commit || busy || unknown} onPress={doCommit}/>
    </Card> : null}
    {result ? <Card><Text style={[font.h2,{color:c.success}]}>{copy.confirmed}: {result}</Text></Card> : null}
    {error ? <Card><Text accessibilityRole="alert" style={[font.body,{color:c.danger}]}>{error}</Text></Card> : null}
    {unknown ? <Text style={[font.small,{color:c.warning}]}>{copy.resultUnknown}</Text> : null}
  </Screen>;
}
