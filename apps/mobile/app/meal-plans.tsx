import React, { useCallback, useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { CalendarDays, ChevronLeft, ClipboardList } from 'lucide-react-native';
import type { DiningStay, DiningStayEntitlements, DiningStays, MealType } from '../src/api/liveModules';
import { useLiveModules } from '../src/api/liveModules';
import { useSession } from '../src/state/session';
import { useAsync } from '../src/lib/useAsync';
import { wasWriteRejected } from '../src/lib/writeOutcome';
import { useMobileCopy } from '../src/i18n/mobileCopy';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';
import { Badge, Button, Empty, Field, PressScale, SectionLabel } from '../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../src/components/Future';

const MEALS: MealType[] = ['BREAKFAST','LUNCH','DINNER'];
const isoDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  !Number.isNaN(Date.parse(value+'T12:00:00')) &&
  new Date(value+'T12:00:00').getFullYear()===Number(value.slice(0,4));
const portions = (value: string) => /^\d{1,2}$/.test(value) && Number(value)>=0 && Number(value)<=50;

/** One hotel and server-gated RECEPTION/OWNER/MANAGER only.
 * The server creates the meal entitlement; the app never creates a payment.
 * Failed or ambiguous writes are NOT automatically retried. */
export default function MealPlans() {
  const { user, hotel, api, serverAuthMode } = useSession();
  const roleAllowed = !!user && ['OWNER','MANAGER','RECEPTION'].includes(user.role);
  const granted = !!user && (user.module_permissions?.includes('PMS') ||
    user.module_permissions?.includes('RESERVATIONS'));
  const allowed = roleAllowed && granted && api?.mode === 'LIVE' && serverAuthMode !== 'shared_auth_preview';
  const live = useLiveModules();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const router = useRouter();
  const [selectedId, setSelectedId] = useState('');
  const [date, setDate] = useState('');
  const [meal, setMeal] = useState<MealType>('BREAKFAST');
  const [adults, setAdults] = useState('2');
  const [children, setChildren] = useState('0');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const busyLock = useRef(false);
  const [needsReview, setNeedsReview] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [result, setResult] = useState('');
  const { data, loading, error, reload } = useAsync<DiningStays | null>(
    () => allowed && live ? live.diningStays() : Promise.resolve(null),
    [allowed, live, hotel?.id, user?.id],
  );
  const selected = data?.items.find(stay=>stay.stay_id===selectedId);
  const { data: saved, error: savedError, loading: savedLoading, reload: reloadSaved } =
    useAsync<DiningStayEntitlements | null>(
      () => allowed && live && selected ? live.diningStayEntitlements(selected.stay_id) : Promise.resolve(null),
      [allowed, live, selectedId, hotel?.id, user?.id],
    );
  const focused = useRef(false);
  useFocusEffect(useCallback(()=>{ if(focused.current) { void reload(); void reloadSaved(); }
    else focused.current=true; },[reload,reloadSaved]));
  const chooseStay = (stay: DiningStay) => {
    if (busyLock.current || needsReview) return;
    setSelectedId(stay.stay_id);
    setDate(stay.check_in > (data?.local_date??'') ? stay.check_in : (data?.local_date??stay.check_in));
    setAdults(String(stay.adults)); setChildren(String(stay.children));
    setMeal('BREAKFAST'); setNotes(''); setReviewNote(''); setResult('');
  };
  const valid = !!selected && isoDate(date) && date >= selected.check_in && date <= selected.check_out &&
    portions(adults) && portions(children) && Number(adults)+Number(children)>0;
  const selectedRecords = saved?.items.filter(x=>x.service_date===date && x.meal_type===meal) ?? [];
  const current = selectedRecords.find(x=>x.status==='ACTIVE');
  const readback = async () => {
    if(!live || !selected || busyLock.current) return;
    busyLock.current = true; setBusy(true);
    try {
      const response = await live.diningStayEntitlements(selected.stay_id);
      const record=response.items.find(x=>x.service_date===date && x.meal_type===meal && x.status==='ACTIVE');
      setReviewNote(record ? copy.mealConfirmed+': '+record.adult_portions+' + '+record.child_portions :
        copy.mealNotConfirmed);
      // The operator must inspect the readback; don't silently re-issue an ambiguous PUT.
      await reloadSaved();
    } catch(e) { setReviewNote(e instanceof Error?e.message:copy.unknown); }
    finally { busyLock.current=false; setBusy(false); }
  };
  const save = () => Alert.alert(copy.confirm, copy.mealPlanSaveConfirm, [
    { text: copy.close, style: 'cancel' },
    { text: copy.mealPlanSave, onPress: async () => {
      if(!live || !selected || !valid || busyLock.current || needsReview) return;
      busyLock.current=true; setBusy(true); setResult('');
      const draft={from_date:date,through_date:date,meals:[meal],
        adult_portions:Number(adults), child_portions:Number(children), notes:notes.trim()||null,
        replace_range:false as const};
      try {
        await live.diningMealPlan(selected.stay_id,draft);
        const verified=await live.diningStayEntitlements(selected.stay_id);
        const found=verified.items.find(x=>x.status==='ACTIVE' && x.service_date===date && x.meal_type===meal &&
          x.adult_portions===draft.adult_portions && x.child_portions===draft.child_portions);
        if(!found) {
          setNeedsReview(true); setReviewNote(copy.mealReadbackMismatch);
          return;
        }
        setResult(copy.mealConfirmed); await reloadSaved(); await reload();
      } catch(e) {
        const rejected=wasWriteRejected(e);
        setNeedsReview(!rejected);
        setResult(rejected ? (e instanceof Error?e.message:copy.conflict) : copy.resultUnknown);
      } finally { busyLock.current=false; setBusy(false); }
    }},
  ]);
  if(!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PressScale accessibilityLabel={copy.close} onPress={()=>router.back()}
      style={{minHeight:48,flexDirection:'row',alignItems:'center',gap:8}}>
      <ChevronLeft size={23} color={c.primary}/><Text style={[font.body,{color:c.primary}]}>{copy.close}</Text>
    </PressScale>
    <PremiumHeader eyebrow="MARINA SMART" title={copy.mealPlansTitle} subtitle={hotel?.name}/>
    <Text style={[font.small,{color:c.textMuted}]}>{copy.mealPlansNotice}</Text>
    {loading ? <LoadingShimmer count={2}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <SectionLabel>{copy.bookings} · {data.items.length}</SectionLabel>
      {data.items.length===0 ? <Empty text={copy.mealNoStays}/> : null}
      {data.items.map(stay=><GlassCard testID={'meal-stay-'+stay.stay_id} key={stay.stay_id}
        onPress={()=>chooseStay(stay)} style={{gap:5,borderColor:selectedId===stay.stay_id?c.primary:c.border}}>
        <Text style={[font.body,{color:c.text,fontWeight:'700'}]}>{stay.room_code||'—'} · {stay.guest_name}</Text>
        <Text style={[font.small,{color:c.textMuted}]}>{stay.booking_number} · {stay.check_in} → {stay.check_out}</Text>
        <Text style={[font.small,{color:c.cyan}]}>{copy.mealPlansCurrent}: {stay.entitlement_count}</Text>
      </GlassCard>)}
    </>:null}
    {selected ? <GlassCard style={{gap:space.md}}>
      <SectionLabel>{copy.mealPlansTitle} · {selected.room_code||selected.booking_number}</SectionLabel>
      <Field label={copy.mealServiceDate} value={date} onChangeText={setDate} autoCapitalize="none"/>
      <View style={{flexDirection:'row',flexWrap:'wrap',gap:space.sm}}>
        {MEALS.map(value=><PressScale key={value} testID={'meal-type-'+value}
          accessibilityLabel={value} onPress={()=>{setMeal(value);setResult('');}}
          style={{paddingHorizontal:14,paddingVertical:12,borderRadius:12,minHeight:46,
            backgroundColor:value===meal?c.primary:c.surfaceAlt}}>
          <Text style={[font.small,{color:value===meal?c.primaryText:c.text,fontWeight:'700'}]}>
            {value==='BREAKFAST'?copy.kitchenBreakfast:value==='LUNCH'?copy.kitchenLunch:copy.kitchenDinner}
          </Text>
        </PressScale>)}
      </View>
      {savedLoading ? <LoadingShimmer count={1}/> : null}
      {savedError ? <ErrorState text={savedError.message} retry={copy.retry} onRetry={reloadSaved}/> : null}
      {current ? <Badge label={copy.mealPlansCurrent+': '+current.adult_portions+' + '+current.child_portions} tone="success"/> : null}
      <View style={{flexDirection:'row',gap:space.sm}}>
        <View style={{flex:1}}><Field label={copy.adults} value={adults} onChangeText={setAdults} keyboardType="number-pad"/></View>
        <View style={{flex:1}}><Field label={copy.children} value={children} onChangeText={setChildren} keyboardType="number-pad"/></View>
      </View>
      <Field label={copy.note} value={notes} onChangeText={setNotes} maxLength={1000}/>
      <Text style={[font.small,{color:c.textMuted}]}>{copy.mealNoPayments}</Text>
      {needsReview ? <View style={{gap:space.sm}}>
        <Text accessibilityRole="alert" style={[font.body,{color:c.warning}]}>{copy.mealReviewRequired}</Text>
        <Button testID="meal-reconcile" label={copy.mealReadback} onPress={()=>void readback()} disabled={busy}/>
        {reviewNote ? <Text style={[font.body,{color:c.text}]}>{reviewNote}</Text> : null}
        <Button variant="secondary" label={copy.mealReviewAck} disabled={busy||!reviewNote}
          onPress={()=>Alert.alert(copy.confirm,copy.mealReviewAckConfirm,[
            {text:copy.close,style:'cancel'},
            {text:copy.confirm,onPress:()=>{setNeedsReview(false);setReviewNote('');setResult('');}}
          ])}/>
      </View> : <Button testID="meal-plan-save" icon={ClipboardList} label={copy.mealPlanSave}
        onPress={save} disabled={!valid || busy || savedLoading || !!savedError}/>}
      {result ? <Text accessibilityRole="alert" style={[font.body,{color:c.text}]}>{result}</Text> : null}
    </GlassCard> : null}
  </FutureScreen>;
}
