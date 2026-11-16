import React, {useRef, useState} from 'react';
import {Alert, Text, View} from 'react-native';
import type {createLiveModules, KitchenStockSnapshot} from '../api/liveModules';
import {useAsync} from '../lib/useAsync';
import {executeProcurement,readProcurement,PendingProcurement} from '../lib/pendingProcurement';
import {useSession} from '../state/session';
import {useTheme} from '../theme/ThemeProvider';
import {ErrorState, GlassCard, LoadingShimmer} from './Future';
import {Button, Field, SectionLabel} from './ui';

const COPY={
 ru:{cancel:'Отмена',title:'Закупки продуктов',needs:'Потребность по плану готовки',date:'Дата приготовления (ГГГГ-ММ-ДД)',
  check:'Рассчитать',shortage:'Нехватка',pipeline:'Всего в заявках',approvedInbound:'Утверждено к приходу',remaining:'После утверждённых поставок',
  noRecipe:'Не все рецептуры утверждены. Потребность неполная.',sample:'Тестовые рецептуры исключены.',
  request:'Новая заявка',select:'Продукт',quantity:'Количество',note:'Примечание',create:'Отправить заявку',
  approve:'Утвердить',receive:'Принять на склад',receiveQuantity:'Количество прихода',supplierSource:'Накладная поставщика',sourceMissing:'Сначала оформите накладную у владельца',
  requested:'Ожидает утверждения',approved:'Утверждена',partial:'Частичный приход',received:'Получена',
  history:'Заявки',retry:'Повторить ту же операцию',done:'Данные сохранены',
  invalid:'Укажите продукт, положительное количество и правильную дату.',
  confirm:'Подтвердить операцию?',warning:'Заявка и утверждение не меняют склад и не создают платёж. Только приход увеличивает остатки.'},
 kg:{cancel:'Жокко чыгаруу',title:'Азык-түлүк сатып алуу',needs:'Даярдоо планы боюнча керектөө',date:'Даярдоо күнү (ЖЖЖЖ-АА-КК)',
  check:'Эсептөө',shortage:'Жетишсиз',pipeline:'Өтүнмөлөрдө',approvedInbound:'Бекитилген жеткирүү',remaining:'Бекитилгенден кийин',
  noRecipe:'Бардык рецепттер бекитилген эмес.',sample:'Сыноо рецепттери кошулган жок.',
  request:'Жаңы өтүнмө',select:'Азык',quantity:'Саны',note:'Эскертүү',create:'Өтүнмө берүү',
  approve:'Бекитүү',receive:'Кампага кабыл алуу',receiveQuantity:'Кабыл алуу саны',supplierSource:'Жеткирүүчүнүн накладнойу',sourceMissing:'Адегенде ээси накладнойду каттасын',
  requested:'Бекитүүнү күтөт',approved:'Бекитилди',partial:'Жарым-жартылай алынды',received:'Алынды',
  history:'Өтүнмөлөр',retry:'Ошол эле операцияны кайталоо',done:'Сакталды',
  invalid:'Азык, оң сан жана туура күн керек.',confirm:'Операцияны ырастайсызбы?',
  warning:'Өтүнмө менен бекитүү кампаны жана төлөмдү өзгөртпөйт. Калдык кабыл алууда гана өсөт.'},
 en:{cancel:'Cancel',title:'Kitchen procurement',needs:'Ingredient demand by production plan',date:'Service date (YYYY-MM-DD)',
  check:'Calculate',shortage:'Shortage',pipeline:'All requested',approvedInbound:'Approved inbound',remaining:'After approved inbound',
  noRecipe:'Some recipes are not approved; the forecast is incomplete.',sample:'Sample recipes are excluded.',
  request:'New request',select:'Ingredient',quantity:'Quantity',note:'Notes',create:'Submit request',
  approve:'Approve',receive:'Receive stock',receiveQuantity:'Received quantity',supplierSource:'Supplier invoice',sourceMissing:'OWNER must register the invoice first',
  requested:'Awaiting approval',approved:'Approved',partial:'Partially received',received:'Received',
  history:'Requests',retry:'Retry same operation',done:'Recorded',
  invalid:'Select a product, positive quantity and valid date.',confirm:'Confirm operation?',
  warning:'Requests and approvals do not affect inventory or create payments. Only receipt increases stock.'},
 kz:{cancel:'Бас тарту',title:'Азық-түлік сатып алу',needs:'Дайындау жоспары бойынша қажеттілік',date:'Дайындау күні (ЖЖЖЖ-АА-КК)',
  check:'Есептеу',shortage:'Тапшылық',pipeline:'Барлық өтінімдер',approvedInbound:'Бекітілген жеткізу',remaining:'Бекітілгеннен кейін',
  noRecipe:'Барлық рецепттер бекітілмеген.',sample:'Сынақ рецепттері есептелмейді.',
  request:'Жаңа өтінім',select:'Өнім',quantity:'Саны',note:'Ескерту',create:'Өтінім беру',
  approve:'Бекіту',receive:'Қоймаға қабылдау',receiveQuantity:'Қабылдау саны',supplierSource:'Жеткізушінің жүкқұжаты',sourceMissing:'Алдымен иесі жүкқұжатты тіркеуі керек',
  requested:'Бекітуді күтеді',approved:'Бекітілді',partial:'Ішінара қабылданды',received:'Қабылданды',
  history:'Өтінімдер',retry:'Сол операцияны қайталау',done:'Сақталды',
  invalid:'Өнім, оң сан және дұрыс күн керек.',confirm:'Операцияны растау?',
  warning:'Өтінім мен бекіту қойманы өзгертпейді және төлем жасамайды. Қалдық қабылдау кезінде өседі.'},
} as const;

function localToday(){
  const now=new Date();
  return [now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),
          String(now.getDate()).padStart(2,'0')].join('-');
}
const validQuantity=(value:string)=>/^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(value)&&Number(value)>0;

type Props={live:ReturnType<typeof createLiveModules>;stock:KitchenStockSnapshot;reloadStock:()=>Promise<unknown>};
export function KitchenProcurement(props:Props){
 const {hotel,user}=useSession();
 return <ProcurementForm key={[hotel?.id,user?.id,user?.role,user?.module_permissions?.join(',')].join('.')} {...props}/>;
}
function ProcurementForm({live,stock,reloadStock}:{
  live:ReturnType<typeof createLiveModules>;
  stock:KitchenStockSnapshot;
  reloadStock:()=>Promise<unknown>;
}){
  const {user,hotel,locale}=useSession();
  const {c}=useTheme();
  const t=COPY[locale];
  const [serviceDate,setServiceDate]=useState(localToday);
  const [targetDate,setTargetDate]=useState(localToday);
  const [selected,setSelected]=useState('');
  const [quantity,setQuantity]=useState('');
  const [notes,setNotes]=useState('');
  const [receiveQuantity,setReceiveQuantity]=useState('');
  const [selectedSource,setSelectedSource]=useState('');
  const [busy,setBusy]=useState(false);
  const lock=useRef(false);
  const journal=useAsync(()=>hotel&&user?readProcurement(hotel.id,user.id):Promise.resolve(null),[hotel?.id,user?.id]);
  const pending=journal.data;
  const ready=!!hotel&&!!user&&!journal.loading&&!journal.error;
  const list=useAsync(()=>live.procurementRequests(),[live,user?.id]);
  const needs=useAsync(()=>live.procurementNeeds(targetDate),[live,user?.id,targetDate]);
  const canRequest=['OWNER','MANAGER','COOK','STORE_STAFF'].includes(user?.role||'');
  const canApprove=['OWNER','MANAGER'].includes(user?.role||'');
  const canReceive=['OWNER','MANAGER','STORE_STAFF'].includes(user?.role||'');
  const sourceEnabled=typeof live.procurementSupplierLines==='function';
  const sources=useAsync(()=>sourceEnabled?live.procurementSupplierLines():Promise.resolve([]),[live,user?.id]);

  const execute=async(op:PendingProcurement|null)=>{
    const action=op??pending;
    if(lock.current||!ready||!hotel||!user||!action||
       (action.kind==='REQUEST'?!canRequest:!canReceive))return;
    lock.current=true;setBusy(true);
    try{
      await executeProcurement(hotel.id,user.id,op?async()=>{
        // A new action gets a fresh server UUID; explicit replay retains the saved one.
        const fresh=await live.procurementRequests();
        return op.kind==='REQUEST'?{...op,request_id:fresh.new_request_id}:{...op,receipt_id:fresh.new_receipt_id};
      }:null,async saved=>{
        if(saved.kind==='REQUEST'){
          if(!canRequest)throw new Error('Procurement request forbidden');
          const {kind:_,...payload}=saved;
          return live.requestKitchenProcurement(payload);
        }
        if(!canReceive)throw new Error('Procurement receipt forbidden');
        return live.receiveKitchenProcurement(saved.requestId,{receipt_id:saved.receipt_id,quantity:saved.quantity,
          ...(saved.document_line_id?{document_line_id:saved.document_line_id}:{})});
      });
      setQuantity('');setReceiveQuantity('');setNotes('');setSelectedSource('');
      await Promise.all([list.reload(),needs.reload(),reloadStock()]);
      Alert.alert(t.done);
    }catch(e){Alert.alert(t.title,e instanceof Error?e.message:String(e));}
    finally{await journal.reload();lock.current=false;setBusy(false);}
  };

  const requestProduct=()=>{
    const q=quantity.replace(',','.');
    if(!canRequest||!ready||!list.data||pending||busy||!selected||!validQuantity(q)||
       !/^\d{4}-\d{2}-\d{2}$/.test(serviceDate)){
      Alert.alert(t.invalid);return;
    }
    const op:PendingProcurement={kind:'REQUEST',request_id:list.data.new_request_id,
      stock_item_id:selected,quantity:q,service_date:serviceDate,
      notes:notes.trim()||null};
    Alert.alert(t.confirm,stock.items.find(x=>x.id===selected)?.name||'',
      [{text:t.cancel,style:'cancel'},
       {text:t.create,onPress:()=>void execute(op)}]);
  };
  const receiveProduct=(id:string)=>{
    const q=receiveQuantity.replace(',','.');
    const row=list.data?.items.find(x=>x.id===id);
    const source=sources.data?.find(x=>x.id===selectedSource&&x.stock_item_id===row?.stock_item_id);
    if(!canReceive||!ready||!list.data||pending||busy||!validQuantity(q)||
       (sourceEnabled&&(!source||sources.loading||!!sources.error||Number(source.remaining_quantity)<Number(q)))){
      Alert.alert(t.invalid);return;
    }
    const op:PendingProcurement={kind:'RECEIVE',requestId:id,receipt_id:list.data.new_receipt_id,quantity:q,
      ...(sourceEnabled?{document_line_id:source!.id}:{})};
    Alert.alert(t.confirm,q,[{text:t.cancel,style:'cancel'},
      {text:t.receive,onPress:()=>void execute(op)}]);
  };
  const approve=async(id:string)=>{
    if(!canApprove||!ready||lock.current||busy||pending)return;
    lock.current=true;setBusy(true);
    try{await live.approveKitchenProcurement(id);await list.reload();await needs.reload();Alert.alert(t.done);}
    catch(e){Alert.alert(t.title,e instanceof Error?e.message:String(e));}
    finally{lock.current=false;setBusy(false);}
  };
  const pendingItem=pending?.kind==='REQUEST'?stock.items.find(x=>x.id===pending.stock_item_id):list.data?.items.find(x=>x.id===pending?.requestId);
  const pendingName=pendingItem?('stock_name' in pendingItem?pendingItem.stock_name:pendingItem.name):t.request;
  const statuses={REQUESTED:t.requested,APPROVED:t.approved,PARTIAL:t.partial,RECEIVED:t.received};
  return <GlassCard testID="kitchen-procurement" style={{gap:9}}>
    <SectionLabel>{t.title}</SectionLabel>
    <Text style={{color:c.textMuted}}>{t.warning}</Text>
    <SectionLabel>{t.needs}</SectionLabel>
    <Field label={t.date} value={serviceDate} onChangeText={setServiceDate}/>
    <Button label={t.check} variant="secondary" onPress={()=>{
      if(!/^\d{4}-\d{2}-\d{2}$/.test(serviceDate)){Alert.alert(t.invalid);return;}
      setTargetDate(serviceDate);
      if(targetDate===serviceDate)void needs.reload();
    }}/>
    {needs.loading?<LoadingShimmer count={1}/>:null}
    {needs.error?<ErrorState text={needs.error.message} onRetry={needs.reload} retry={t.retry}/>:null}
    {needs.data?.items.map(row=><View key={row.name+row.unit} style={{gap:3,paddingVertical:4}}>
      <Text style={{color:c.text}}>{row.name} · {row.remaining_needed} {row.unit}</Text>
      <Text style={{color:c.textMuted}}>{t.shortage}: {row.shortage} · {t.pipeline}: {row.pending_requests}
        {' · '+t.approvedInbound+': '+row.approved_inbound+' · '+t.remaining+': '+row.shortage_after_pipeline}</Text>
    </View>)}
    {needs.data&&!needs.data.is_complete?<Text style={{color:c.warning}}>
      {t.noRecipe}{needs.data.excluded_sample_targets?' '+t.sample:''}
    </Text>:null}
    <SectionLabel>{t.request}</SectionLabel>
    {list.loading?<LoadingShimmer count={1}/>:null}
    {list.error?<ErrorState text={list.error.message} onRetry={list.reload} retry={t.retry}/>:null}
    {journal.loading?<LoadingShimmer count={1}/>:null}
    {journal.error?<ErrorState text={journal.error.message} onRetry={journal.reload} retry={t.retry}/>:null}
    {canRequest&&ready&&!pending&&list.data?<View style={{gap:8}}>
      {stock.items.filter(item=>!item.is_sample).map(item=><Button key={item.id}
        label={item.name+' · '+item.unit+(item.is_sample?' · ТЕСТ':'')}
        variant={selected===item.id?'primary':'secondary'} onPress={()=>setSelected(item.id)}/>)}
      <Field label={t.quantity} keyboardType="decimal-pad" value={quantity} onChangeText={setQuantity}/>
      <Field label={t.note} value={notes} onChangeText={setNotes}/>
      <Button disabled={busy||!selected||!quantity} testID="procurement-create"
        label={t.create} onPress={requestProduct}/>
    </View>:null}
    {pending?<View testID="procurement-pending" style={{gap:6}}>
      <Text style={{color:c.warning}}>{pending.kind==='REQUEST'?t.create:t.receive} · {pendingName} · {pending.quantity} {pendingItem?.unit}</Text>
      <Button disabled={busy||!ready||(pending.kind==='REQUEST'?!canRequest:!canReceive)} label={t.retry} testID="procurement-retry"
        variant="secondary" onPress={()=>void execute(null)}/>
    </View>:null}
    <SectionLabel>{t.history}</SectionLabel>
    {list.data?.items.slice(0,20).map(row=><View key={row.id} style={{gap:6,paddingVertical:5}}>
      <Text style={{color:c.text}}>{row.stock_name} · {row.quantity} {row.unit}</Text>
      <Text style={{color:c.textMuted}}>{statuses[row.status]}
        {' · '+row.received_quantity+'/'+row.quantity+' '+row.unit}</Text>
      {canApprove&&row.status==='REQUESTED'?<Button disabled={busy||!ready||!!pending}
        label={t.approve} onPress={()=>void approve(row.id)}/>:null}
      {canReceive&&ready&&!pending&&['APPROVED','PARTIAL'].includes(row.status)?<View style={{gap:5}}>
        {sourceEnabled?<View style={{gap:4}}>
          <Text style={{color:c.textMuted}}>{t.supplierSource}</Text>
          {sources.error?<ErrorState text={sources.error.message} onRetry={sources.reload} retry={t.retry}/>:null}
          {sources.data?.filter(x=>x.stock_item_id===row.stock_item_id&&Number(x.remaining_quantity)>0).map(x=><Button
            key={x.id} variant={selectedSource===x.id?'primary':'secondary'}
            label={x.supplier_name+' · '+x.document_reference+' · '+x.remaining_quantity+' '+row.unit}
            onPress={()=>setSelectedSource(x.id)}/>)}
          {sources.data&&!sources.data.some(x=>x.stock_item_id===row.stock_item_id&&Number(x.remaining_quantity)>0)?
            <Text style={{color:c.warning}}>{t.sourceMissing}</Text>:null}
        </View>:null}
        <Field label={t.receiveQuantity} keyboardType="decimal-pad"
          value={receiveQuantity} onChangeText={setReceiveQuantity}/>
        <Button disabled={busy||!receiveQuantity||(sourceEnabled&&(!selectedSource||sources.loading||!!sources.error))} label={t.receive}
          onPress={()=>receiveProduct(row.id)}/>
      </View>:null}
    </View>)}
  </GlassCard>;
}
