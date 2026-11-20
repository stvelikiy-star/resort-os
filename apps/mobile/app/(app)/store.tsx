import React, {useCallback, useRef, useState} from 'react';
import { Alert, Text } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { FutureScreen, PremiumHeader, GlassCard, LoadingShimmer, ErrorState } from '../../src/components/Future';
import { Button, Empty, Field, SectionLabel } from '../../src/components/ui';
import { useSession } from '../../src/state/session';
import { useLiveModules } from '../../src/api/liveModules';
import { KitchenLosses } from '../../src/components/KitchenLosses';
import { KitchenProcurement } from '../../src/components/KitchenProcurement';
import { hasTabForSession } from '../../src/roles/registry';
import { executeStockReceipt, readStockReceipt } from '../../src/lib/pendingStockReceipt';
import { receiptQuantity, receiptUuid } from '../../src/api/stockReceipt';
import { useAsync } from '../../src/lib/useAsync';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font,space } from '../../src/theme/tokens';
const COPY = {
  ru:{title:'Склад',receipt:'Приход продукта',select:'Выберите продукт',quantity:'Количество',save:'Записать приход',success:'Приход сохранён',warning:'Тестовые продукты не являются реальными запасами.',noPayment:'Приход не создаёт платёж. Себестоимость списаний ведётся отдельно.',invalid:'Введите положительное количество.',empty:'Продукты не добавлены собственником.'},
  kg:{title:'Кампа',receipt:'Азык кабыл алуу',select:'Азыкты тандаңыз',quantity:'Саны',save:'Кирешелөө',success:'Кабыл алуу сакталды',warning:'Сыноо азыктары чыныгы кампа запасы эмес.',noPayment:'Азык кабыл алуу төлөм түзбөйт. Өздүк нарк өзүнчө эсептелет.',invalid:'Оң санды киргизиңиз.',empty:'Азыктар ээси тарабынан кошула элек.'},
  en:{title:'Stock',receipt:'Receive stock',select:'Select product',quantity:'Quantity',save:'Record receipt',success:'Stock receipt saved',warning:'Sample ingredients are not real inventory.',noPayment:'Receiving stock does not create a payment. Consumption cost is tracked separately.',invalid:'Enter a positive quantity.',empty:'No products set up by the owner yet.'},
  kz:{title:'Қойма',receipt:'Өнім қабылдау',select:'Өнімді таңдаңыз',quantity:'Саны',save:'Кірісті тіркеу',success:'Кіріс сақталды',warning:'Сынақ өнімдері нақты қойма қоры емес.',noPayment:'Қабылдау төлем жасамайды. Өзіндік құн бөлек есептеледі.',invalid:'Оң сан енгізіңіз.',empty:'Өнімдерді иесі әлі қоспаған.'},
} as const;
const RECEIPT_COPY={
 ru:{pending:'Приход требует подтверждения. Новая операция заблокирована.',retry:'Проверить / повторить тот же приход',error:'Не удалось подтвердить приход. Повторите сохранённую операцию.',unsupported:'Для безопасного прихода обновите сервер.'},
 kg:{pending:'Кабыл алууну ырастоо керек. Жаңы операция бөгөттөлдү.',retry:'Ошол эле кабыл алууну текшерүү / кайталоо',error:'Кабыл алуу ырасталган жок. Сакталган операцияны кайталаңыз.',unsupported:'Коопсуз кабыл алуу үчүн серверди жаңыртыңыз.'},
 en:{pending:'Receipt requires confirmation. New receipts are blocked.',retry:'Check / replay the same receipt',error:'Receipt not confirmed. Replay the saved operation.',unsupported:'Update the server to receive stock safely.'},
 kz:{pending:'Қабылдауды растау керек. Жаңа операция бұғатталған.',retry:'Сол қабылдауды тексеру / қайталау',error:'Қабылдау расталмады. Сақталған операцияны қайталаңыз.',unsupported:'Қауіпсіз қабылдау үшін серверді жаңартыңыз.'},
} as const;
export default function StoreWorkspace() {
 const {user,api,hotel,locale,serverAuthMode}=useSession();const live=useLiveModules();const {c}=useTheme();
 const allowed=!!user && api?.mode==='LIVE' && hasTabForSession(user.role,user.module_permissions,'LIVE','store',serverAuthMode);
 const t=COPY[locale];const [selected,setSelected]=useState('');const [quantity,setQuantity]=useState('');const [busy,setBusy]=useState(false);
 const {data,error,loading,reload}=useAsync(()=>allowed&&live?live.kitchenStock():Promise.resolve(null),[allowed,live,user?.id,hotel?.id]);
 const receiptCopy=RECEIPT_COPY[locale];const receiptLock=useRef(false);const [feedback,setFeedback]=useState('');
 const journal=useAsync(()=>allowed&&hotel&&user?readStockReceipt(hotel.id,user.id):Promise.resolve(null),[allowed,hotel?.id,user?.id]);
 const receiptBlocked=busy||journal.loading||!!journal.error||!!journal.data;
 const focused=useRef(false);useFocusEffect(useCallback(()=>{if(focused.current)void reload();else focused.current=true;},[reload]));
 const submit=async(resume:boolean,q?:string)=>{
  if(!allowed||!live||!hotel||!user||receiptLock.current||(!resume&&receiptBlocked))return;
  receiptLock.current=true;setBusy(true);setFeedback('');
  try{
   await executeStockReceipt(hotel.id,user.id,resume?null:async()=>{
    const fresh=await live.kitchenStock();
    if(!receiptUuid(fresh.new_receipt_movement_id))throw new Error(receiptCopy.unsupported);
    return {movement_id:fresh.new_receipt_movement_id,stock_item_id:selected,quantity:q!,notes:'Mobile inventory receipt'};
   },live.receiveKitchenStock);
   setQuantity('');setFeedback(t.success);await reload();
  }catch(e){setFeedback(receiptCopy.error+' '+(e instanceof Error?e.message:''));}
  finally{await journal.reload();receiptLock.current=false;setBusy(false);}
 };
 const save=()=>{
  let q:string;try{q=receiptQuantity(quantity.replace(',','.'));}catch{Alert.alert(t.invalid);return;}
  if(!selected||receiptBlocked)return;
  Alert.alert(t.receipt,`${q} · ${data?.items.find(i=>i.id===selected)?.name||''}`,[
   {text:locale==='en'?'Cancel':locale==='kg'?'Жокко чыгаруу':locale==='kz'?'Бас тарту':'Отмена',style:'cancel'},
   {text:t.save,onPress:()=>void submit(false,q)}]);
 };
 if(!allowed)return <FutureScreen><Empty text={t.title+' — access denied'}/></FutureScreen>;
 return <FutureScreen><PremiumHeader title={t.title} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
 {loading?<LoadingShimmer count={2}/>:null}{error?<ErrorState text={error.message} onRetry={reload} retry={locale==='en'?'Retry':'Повторить'}/>:null}
 {journal.error?<ErrorState text={journal.error.message} retry={locale==='en'?'Retry':'Повторить'} onRetry={journal.reload}/>:null}
 {journal.data?<GlassCard testID="stock-receipt-pending" style={{gap:space.sm}}>
  <Text style={[font.body,{color:c.warning}]}>{receiptCopy.pending}</Text>
  <Text selectable style={[font.small,{color:c.text}]}>{journal.data.movement_id} · {journal.data.quantity} · {journal.data.stock_item_id}</Text>
  <Button testID="stock-receipt-retry" label={receiptCopy.retry} disabled={busy} onPress={()=>void submit(true)}/>
 </GlassCard>:null}
 {feedback?<Text accessibilityRole="alert" style={[font.body,{color:c.text}]}>{feedback}</Text>:null}
 {data?<><GlassCard style={{gap:space.sm}}><SectionLabel>{t.title}</SectionLabel>
 {data.items.length?data.items.map(i=><Text key={i.id} style={[font.body,{color:c.text}]}>{i.name} · {i.balance} {i.unit}{i.is_sample?' · ТЕСТ':''}</Text>):<Text style={{color:c.textMuted}}>{t.empty}</Text>}
 <Text style={[font.small,{color:c.warning}]}>{t.warning}</Text><Text style={[font.small,{color:c.textMuted}]}>{t.noPayment}</Text>
 </GlassCard><GlassCard style={{gap:space.sm}}><SectionLabel>{t.receipt}</SectionLabel>
 {data.items.map(i=><Button key={i.id} variant={selected===i.id?'primary':'secondary'} label={i.name+' ('+i.unit+')'} disabled={receiptBlocked} onPress={()=>setSelected(i.id)} />)}
 <Field label={t.quantity} keyboardType="decimal-pad" value={quantity} onChangeText={setQuantity} editable={!receiptBlocked}/>
 <Button testID="stock-receipt-save" disabled={receiptBlocked||!data.new_receipt_movement_id||!selected||!quantity} label={t.save} onPress={save}/>
 {!data.new_receipt_movement_id?<Text style={{color:c.warning}}>{receiptCopy.unsupported}</Text>:null}
 </GlassCard>{live?<KitchenLosses live={live} stock={data} reload={reload}/>:null}
 {live?<KitchenProcurement live={live} stock={data} reloadStock={reload}/>:null}</>:null}
 </FutureScreen>;
}
