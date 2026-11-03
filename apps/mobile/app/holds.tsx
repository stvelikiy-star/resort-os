import React, { useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { ChevronLeft, Clock3 } from 'lucide-react-native';
import { Button, Card, Empty, Field, PressScale, Screen, SectionLabel, Title } from '../src/components/ui';
import { Hold, localDate, useLiveModules } from '../src/api/liveModules';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { useSession } from '../src/state/session';
import { useAsync } from '../src/lib/useAsync';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

export default function Holds() {
  const live = useLiveModules();
  const { user } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [unknown, setUnknown] = useState(false);
  const [room, setRoom] = useState('');
  const [start, setStart] = useState(localDate(1));
  const [end, setEnd] = useState(localDate(2));
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const { data, error, loading, reload } = useAsync<Hold[] | null>(() => live ? live.holds() : Promise.resolve(null), [live, user?.id]);
  const { data: grid } = useAsync(() => live && /^\d{4}-\d{2}-\d{2}$/.test(start) && /^\d{4}-\d{2}-\d{2}$/.test(end) && start < end ? live.pmsGrid(start, end) : Promise.resolve(null), [live,start,end]);
  const mutation = async (run: () => Promise<unknown>) => {
    if (lock.current || unknown) return;
    lock.current=true; setBusy(true); setErrorMessage(null);
    try { await run(); await reload(); setUnknown(true); }
    catch(e) { setUnknown(true); setErrorMessage(e instanceof Error ? e.message : copy.unknown); }
    finally { lock.current=false; setBusy(false); }
  };
  const create = () => Alert.alert(copy.confirm,'',[{text:copy.close,style:'cancel'},{text:copy.holdCreate,onPress:()=>void mutation(() => live!.createHold({room_id:room,check_in:start,check_out:end,guest_name:name.trim(),guest_phone:phone.trim()}))}]);
  const release = (id: string) => Alert.alert(copy.confirm,'',[{text:copy.close,style:'cancel'},{text:copy.release,onPress:()=>void mutation(() => live!.releaseHold(id))}]);
  if (!user || !['OWNER','MANAGER'].includes(user.role) || !user.module_permissions?.includes('PMS')) return <Screen><Empty text={copy.denied}/></Screen>;
  return <Screen>
    <PressScale onPress={() => router.back()} style={{minHeight:44,flexDirection:'row',alignItems:'center'}}><ChevronLeft color={c.primary} size={24}/><Text style={[font.body,{color:c.primary}]}>{copy.close}</Text></PressScale>
    <View style={{flexDirection:'row',gap:space.md,alignItems:'center'}}><Clock3 color={c.primary} size={28}/><Title>{copy.holds}</Title></View>
    {!live ? <Empty text={copy.unavailable}/> : null}
    {loading ? <Empty text={copy.loading}/> : null}
    {error ? <Card onPress={reload}><Text style={[font.body,{color:c.danger}]}>{error.message} · {copy.retry}</Text></Card> : null}
    {(data ?? []).map(h => <Card key={h.id} style={{gap:8}}>
      <Text style={[font.h2,{color:c.text}]}>{h.guestName} · {h.roomId.slice(0,8)}</Text>
      <Text style={[font.body,{color:c.textMuted}]}>{h.checkIn} → {h.checkOut}</Text>
      <Text style={[font.small,{color:c.warning}]}>{copy.expires}: {h.expiresAt}</Text>
      <Button variant="danger" disabled={busy || unknown} label={copy.release} onPress={() => release(h.id)}/>
    </Card>)}
    <SectionLabel>{copy.holdCreate}</SectionLabel>
    <Field label={copy.start} value={start} onChangeText={setStart}/>
    <Field label={copy.end} value={end} onChangeText={setEnd}/>
    <View style={{flexDirection:'row',flexWrap:'wrap',gap:space.sm}}>
      {(grid?.rooms ?? []).filter(r => !r.blocks.length && r.operational_state!=='TECH_BLOCK').map(r =>
        <PressScale key={r.id} onPress={()=>setRoom(r.id)} disabled={busy||unknown} style={{minWidth:85,minHeight:48,backgroundColor:room===r.id?c.primary:c.surfaceAlt,borderRadius:12,justifyContent:'center',alignItems:'center'}}>
          <Text style={[font.h2,{color:room===r.id?'#fff':c.text}]}>{r.code}</Text>
        </PressScale>)}
    </View>
    <Field label={copy.guestName} value={name} onChangeText={setName}/>
    <Field label={copy.phone} value={phone} onChangeText={setPhone} keyboardType="phone-pad"/>
    <Button testID="hold-create" disabled={!room||name.trim().length<2||phone.trim().length<5||busy||unknown} label={copy.holdCreate} onPress={create}/>
    {errorMessage ? <Card><Text accessibilityRole="alert" style={[font.body,{color:c.danger}]}>{errorMessage} · {copy.resultUnknown}</Text></Card>:null}
    {unknown ? <Card><Text style={[font.small,{color:c.warning}]}>{copy.resultUnknown}</Text><Button variant="secondary" label={copy.retry} onPress={()=>{setUnknown(false);void reload();}}/></Card>:null}
  </Screen>;
}
