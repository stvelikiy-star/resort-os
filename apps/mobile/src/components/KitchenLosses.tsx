import React, {useCallback, useState} from 'react';
import {Alert, Text, View} from 'react-native';
import type {createLiveModules, KitchenLossKind, KitchenLossMutation, KitchenStockSnapshot} from '../api/liveModules';
import {useAsync} from '../lib/useAsync';
import {useSession} from '../state/session';
import {useTheme} from '../theme/ThemeProvider';
import {ErrorState, GlassCard, LoadingShimmer} from './Future';
import {Button, Field, SectionLabel} from './ui';

const COPY={
  ru:{cancel:'Отмена',title:'Порча и потери',kindWaste:'Потери',kindSpoilage:'Порча',select:'Выбрать ингредиент',
    quantity:'Количество',reason:'Причина списания',save:'Списать со склада',retry:'Повторить ту же операцию',
    confirm:'Подтвердить списание?',done:'Списание сохранено',history:'Последние списания',
    notice:'Себестоимость — не платёж. При ошибке сети повторяйте только ту же операцию.',
    invalid:'Укажите продукт, положительное количество и причину минимум из 3 символов.',empty:'Списаний ещё нет'},
  kg:{cancel:'Жокко чыгаруу',title:'Бузулуу жана жоготуулар',kindWaste:'Жоготуулар',kindSpoilage:'Бузулуу',select:'Азык тандоо',
    quantity:'Саны',reason:'Эсептен чыгаруунун себеби',save:'Кампадан чыгаруу',retry:'Ошол эле операцияны кайталоо',
    confirm:'Чыгарууну ырастайсызбы?',done:'Чыгаруу сакталды',history:'Акыркы чыгаруулар',
    notice:'Өздүк нарк төлөм эмес. Тармак катасында ошол эле операцияны кайталаңыз.',
    invalid:'Азык, оң сан жана кеминде 3 тамгадан турган себеп керек.',empty:'Чыгаруу жок'},
  en:{cancel:'Cancel',title:'Waste & spoilage',kindWaste:'Waste',kindSpoilage:'Spoilage',select:'Select ingredient',
    quantity:'Quantity',reason:'Write-off reason',save:'Deduct inventory',retry:'Retry same operation',
    confirm:'Confirm this stock loss?',done:'Inventory loss recorded',history:'Recent write-offs',
    notice:'Cost is not a payment. After a network error retry only the same operation.',
    invalid:'Select stock, positive quantity and a reason of at least 3 characters.',empty:'No write-offs'},
  kz:{cancel:'Бас тарту',title:'Бүліну және шығындар',kindWaste:'Шығындар',kindSpoilage:'Бүліну',select:'Өнімді таңдау',
    quantity:'Саны',reason:'Есептен шығару себебі',save:'Қоймадан есептен шығару',retry:'Сол әрекетті қайталау',
    confirm:'Есептен шығаруды растау керек пе?',done:'Есептен шығарылды',history:'Соңғы есептен шығарулар',
    notice:'Өзіндік құн төлем емес. Желі қатесінде тек сол операцияны қайталаңыз.',
    invalid:'Өнім, оң сан және кемінде 3 таңбалы себеп қажет.',empty:'Есептен шығару жоқ'},
} as const;

export function KitchenLosses({live,stock,reload}:{
  live:ReturnType<typeof createLiveModules>;
  stock:KitchenStockSnapshot;
  reload:()=>Promise<unknown>;
}){
  const {user,locale}=useSession();
  const {c}=useTheme();
  const t=COPY[locale];
  const [selected,setSelected]=useState('');
  const [kind,setKind]=useState<KitchenLossKind>('SPOILAGE');
  const [quantity,setQuantity]=useState('');
  const [reason,setReason]=useState('');
  const [busy,setBusy]=useState(false);
  const [pending,setPending]=useState<KitchenLossMutation|null>(null);
  const journal=useAsync(()=>live.kitchenLosses(),[live,user?.id]);
  const canWrite=user?.role==='COOK'||user?.role==='STORE_STAFF';
  const execute=useCallback(async(op:KitchenLossMutation)=>{
    if(busy||!canWrite)return;
    setBusy(true);
    setPending(op); // Persist the same mutation ID for any uncertain result.
    try{
      await live.reportKitchenLoss(op);
      await reload();
      await journal.reload();
      setPending(null);
      setQuantity('');setReason('');
      Alert.alert(t.done);
    }catch(e){
      Alert.alert(t.title,e instanceof Error?e.message:String(e));
    }finally{setBusy(false);}
  },[busy,canWrite,live,reload,journal,t]);
  const create=()=>{
    if(!canWrite||busy||pending)return;
    const q=quantity.replace(',','.');
    if(!selected||!stock.new_loss_movement_id||
      !/^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(q)||Number(q)<=0||
      reason.trim().length<3||reason.trim().length>500){
      Alert.alert(t.invalid);return;
    }
    const operation:KitchenLossMutation={
      movement_id:stock.new_loss_movement_id,stock_item_id:selected,
      kind,quantity:q,reason:reason.trim(),
    };
    Alert.alert(t.confirm,stock.items.find(x=>x.id===selected)?.name||'',[
      {text:t.cancel,style:'cancel'},
      {text:t.save,onPress:()=>void execute(operation)},
    ]);
  };
  return <GlassCard testID="kitchen-losses" style={{gap:9}}>
    <SectionLabel>{t.title}</SectionLabel>
    <Text style={{color:c.textMuted}}>{t.notice}</Text>
    {canWrite&&!pending?<View style={{gap:8}}>
      <View style={{flexDirection:'row',gap:8}}>
        <View style={{flex:1}}><Button variant={kind==='SPOILAGE'?'primary':'secondary'}
          label={t.kindSpoilage} onPress={()=>setKind('SPOILAGE')}/></View>
        <View style={{flex:1}}><Button variant={kind==='WASTE'?'primary':'secondary'}
          label={t.kindWaste} onPress={()=>setKind('WASTE')}/></View>
      </View>
      {stock.items.map(item=><Button key={item.id}
        variant={selected===item.id?'primary':'secondary'}
        label={item.name+' · '+item.balance+' '+item.unit+(item.is_sample?' · ТЕСТ':'')}
        onPress={()=>setSelected(item.id)}/>)}
      <Field label={t.quantity} keyboardType="decimal-pad" value={quantity} onChangeText={setQuantity}/>
      <Field label={t.reason} value={reason} onChangeText={setReason}/>
      <Button testID="kitchen-create-loss" disabled={busy||!stock.new_loss_movement_id}
        label={t.save} onPress={create}/>
    </View>:null}
    {pending?<Button testID="kitchen-retry-loss" disabled={busy} variant="secondary"
      label={t.retry} onPress={()=>void execute(pending)}/>:null}
    <SectionLabel>{t.history}</SectionLabel>
    {journal.loading?<LoadingShimmer count={1}/>:null}
    {journal.error?<ErrorState text={journal.error.message} retry={t.retry} onRetry={journal.reload}/>:null}
    {journal.data?.slice(0,15).map(row=><View key={row.id} style={{gap:3,paddingVertical:4}}>
      <Text style={{color:c.text}}>{row.stock_name} · {row.quantity} {row.unit}</Text>
      <Text style={{color:c.textMuted}}>{row.kind==='WASTE'?t.kindWaste:t.kindSpoilage}
        {' · '+row.cost_kgs+' KGS · '+row.reason}</Text>
      <Text style={{color:c.textMuted}}>{row.created_by_id||''}</Text>
    </View>)}
    {journal.data?.length===0?<Text style={{color:c.textMuted}}>{t.empty}</Text>:null}
  </GlassCard>;
}
