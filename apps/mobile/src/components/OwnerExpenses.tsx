import React, {useCallback, useState} from 'react';
import {Alert, Text, View} from 'react-native';
import type {createLiveModules, OwnerExpenseCategory, OwnerExpenseMethod} from '../api/liveModules';
import {useAsync} from '../lib/useAsync';
import {useSession} from '../state/session';
import {useTheme} from '../theme/ThemeProvider';
import {ErrorState, GlassCard, LoadingShimmer} from './Future';
import {Button, Field, SectionLabel} from './ui';

const COPY={
 ru:{title:'Хозяйственные расходы',post:'Записать расход',amount:'Сумма, сом',
  name:'Название расхода',supplier:'Поставщик',reference:'Документ или номер счёта',
  category:'Категория',notes:'Примечание',date:'Дата расхода (ГГГГ-ММ-ДД)',
  posted:'Расходы за период',paid:'Оплачено по расходам периода',
  outstanding:'Не оплачено',payments:'Ручные оплаты',newPayment:'Записать оплату',
  paidOn:'Дата оплаты (ГГГГ-ММ-ДД)',method:'Метод оплаты',submit:'Сохранить',
  cancel:'Отмена',retry:'Повторить ту же операцию',success:'Запись сохранена',refreshFailed:'Запись сохранена, но часть отчётов не обновилась. Обновите экран.',invalid:'Проверьте дату, сумму и название.',
  confirm:'Подтвердите ручную запись',unavailable:'Данные расходов не получены',
  notice:'Расход и его оплата — разные факты. Эта запись не переводит деньги и не создаёт платёж клиента. Прибыль здесь не рассчитывается.'},
 kg:{title:'Чарбалык чыгымдар',post:'Чыгымды каттоо',amount:'Сумма, сом',
  name:'Чыгымдын аты',supplier:'Жеткирүүчү',reference:'Документ',category:'Категория',
  notes:'Эскертүү',date:'Чыгым күнү (ЖЖЖЖ-АА-КК)',posted:'Мезгилдин чыгымдары',
  paid:'Төлөнгөнү',outstanding:'Төлөнө элек',payments:'Кол менен катталган төлөмдөр',
  newPayment:'Төлөмдү каттоо',paidOn:'Төлөм күнү (ЖЖЖЖ-АА-КК)',method:'Төлөм ыкмасы',
  submit:'Сактоо',cancel:'Жокко чыгаруу',retry:'Ошол операцияны кайра аткаруу',success:'Сакталды',refreshFailed:'Жазуу сакталды, бирок айрым отчёттор жаңырган жок. Экранды жаңыртыңыз.',
  invalid:'Күндү, сумманы жана атын текшериңиз.',confirm:'Кол менен каттоону ырастоо',
  unavailable:'Чыгымдар жеткиликтүү эмес',
  notice:'Чыгым менен төлөм эки башка факт. Акча которулбайт, кардар төлөмү түзүлбөйт. Пайда эсептелбейт.'},
 en:{title:'Operating expenses',post:'Record an expense',amount:'Amount, KGS',
  name:'Expense title',supplier:'Supplier',reference:'Invoice / document reference',
  category:'Category',notes:'Notes',date:'Expense date (YYYY-MM-DD)',
  posted:'Expenses in period',paid:'Settled against period expenses',outstanding:'Unpaid',
  payments:'Manually recorded payments',newPayment:'Record payment',paidOn:'Payment date (YYYY-MM-DD)',
  method:'Payment method',submit:'Save',cancel:'Cancel',retry:'Retry identical operation',
  success:'Saved',refreshFailed:'Saved, but some reports did not refresh. Refresh the screen.',invalid:'Check the date, amount and title.',confirm:'Confirm manual record',
  unavailable:'Expenses unavailable',
  notice:'Expense and payment are separate facts. This does not transfer money or create a customer payment. Profit is not calculated.'},
 kz:{title:'Шаруашылық шығындар',post:'Шығынды тіркеу',amount:'Сома, сом',
  name:'Шығын атауы',supplier:'Жеткізуші',reference:'Құжат нөмірі',category:'Санат',
  notes:'Ескерту',date:'Шығын күні (ЖЖЖЖ-АА-КК)',posted:'Кезең шығындары',
  paid:'Төленгені',outstanding:'Төленбеген',payments:'Қолмен тіркелген төлемдер',
  newPayment:'Төлемді тіркеу',paidOn:'Төлем күні (ЖЖЖЖ-АА-КК)',method:'Төлем тәсілі',
  submit:'Сақтау',cancel:'Бас тарту',retry:'Сол операцияны қайталау',success:'Сақталды',refreshFailed:'Жазба сақталды, бірақ кейбір есептер жаңартылмады. Бетті жаңартыңыз.',
  invalid:'Күнді, соманы және атауды тексеріңіз.',confirm:'Қолмен жазуды растау',
  unavailable:'Шығындар қолжетімсіз',
  notice:'Шығын мен төлем бөлек деректер. Ақша аударылмайды, клиент төлемі жасалмайды. Пайда есептелмейді.'},
} as const;
const CATEGORIES:OwnerExpenseCategory[]=['SUPPLIES','UTILITIES','PAYROLL','MAINTENANCE','RENT','MARKETING','OTHER'];
const METHODS:OwnerExpenseMethod[]=['CASH','BANK_TRANSFER','CARD','OTHER'];
const asMoney=(n:number)=>n.toLocaleString('ru-RU')+' KGS';
type Pending=
 | {type:'EXPENSE';data:{id:string;expense_date:string;category:OwnerExpenseCategory;
  title:string;amount_kgs:number;supplier_name:string|null;
  document_reference:string|null;notes:string|null}}
 | {type:'SETTLEMENT';expenseId:string;data:{id:string;amount_kgs:number;
  paid_on:string;method:OwnerExpenseMethod;reference:string|null}};
const validDate=(value:string)=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&
  !Number.isNaN(Date.parse(value))&&new Date(value).toISOString().slice(0,10)===value;
const integerAmount=(value:string)=>/^[1-9]\d*$/.test(value)&&
  Number.isSafeInteger(Number(value))&&Number(value)<=2_000_000_000;

export function OwnerExpenses({live,from,to,onCommitted}:{
 live:ReturnType<typeof createLiveModules>;from:string;to:string;
 /** Invalidate parent finance/cash/kitchen snapshots only after server confirms a write. */
 onCommitted?:()=>void|Promise<void>;
}){
 const {user,locale}=useSession();
 const {c}=useTheme();
 const t=COPY[locale];
 const [title,setTitle]=useState('');
 const [amount,setAmount]=useState('');
 const [date,setDate]=useState(to);
 const [supplier,setSupplier]=useState('');
 const [documentRef,setDocumentRef]=useState('');
 const [notes,setNotes]=useState('');
 const [category,setCategory]=useState<OwnerExpenseCategory>('SUPPLIES');
 const [settlementAmount,setSettlementAmount]=useState('');
 const [settlementDate,setSettlementDate]=useState(to);
 const [method,setMethod]=useState<OwnerExpenseMethod>('CASH');
 const [busy,setBusy]=useState(false);
 const [pending,setPending]=useState<Pending|null>(null);
 const [selectedExpense,setSelectedExpense]=useState<string|null>(null);
 const allowed=user?.role==='OWNER';
 const ledger=useAsync(()=>allowed?live.ownerExpenses(from,to):Promise.resolve(null),
   [live,user?.id,from,to,allowed]);
 const execute=useCallback(async(op:Pending)=>{
   if(busy||!allowed)return;
   setBusy(true);setPending(op);
   try{
     if(op.type==='EXPENSE')await live.postOwnerExpense(op.data);
     else await live.settleOwnerExpense(op.expenseId,op.data);
     // A successful server commit must never be presented as a failed write
     // because a subsequent report refresh fails. Do not offer a duplicate retry.
     setPending(null);setAmount('');setTitle('');setSupplier('');
     setDocumentRef('');setNotes('');setSettlementAmount('');
     const refresh=await Promise.allSettled([
       ledger.reload(),Promise.resolve().then(()=>onCommitted?.()),
     ]);
     const parentFailed=refresh.some(outcome=>outcome.status==='rejected');
     Alert.alert(t.success,parentFailed?t.refreshFailed:undefined);
   }catch(err){Alert.alert(t.title,err instanceof Error?err.message:String(err));}
   finally{setBusy(false);}
 },[allowed,busy,ledger,live,onCommitted,t]);
 if(!allowed)return null;
 const create=()=>{
   if(!ledger.data||!title.trim()||title.trim().length>150||!validDate(date)||
     !integerAmount(amount)||pending||busy){Alert.alert(t.invalid);return;}
   const op:Pending={type:'EXPENSE',data:{
     id:ledger.data.new_expense_id,expense_date:date,category,title:title.trim(),
     amount_kgs:Number(amount),supplier_name:supplier.trim()||null,
     document_reference:documentRef.trim()||null,notes:notes.trim()||null,
   }};
   Alert.alert(t.confirm,asMoney(op.data.amount_kgs),[
     {text:t.cancel,style:'cancel'},
     {text:t.submit,onPress:()=>void execute(op)}]);
 };
 const settle=(expenseId:string,remaining:number)=>{
   if(!ledger.data||!validDate(settlementDate)||!integerAmount(settlementAmount)||
     Number(settlementAmount)>remaining||pending||busy){Alert.alert(t.invalid);return;}
   const op:Pending={type:'SETTLEMENT',expenseId,data:{
     id:ledger.data.new_settlement_id,amount_kgs:Number(settlementAmount),
     paid_on:settlementDate,method,reference:null,
   }};
   Alert.alert(t.confirm,asMoney(op.data.amount_kgs),[
     {text:t.cancel,style:'cancel'},
     {text:t.submit,onPress:()=>void execute(op)}]);
 };
 return <GlassCard style={{gap:9}} testID="owner-expenses">
   <SectionLabel>{t.title}</SectionLabel>
   <Text style={{color:c.textMuted}}>{t.notice}</Text>
   {ledger.loading?<LoadingShimmer count={1}/>:null}
   {ledger.error?<ErrorState text={ledger.error.message} onRetry={ledger.reload}
     retry={t.retry}/>:null}
   {ledger.data?<View style={{gap:4}}>
     <Text style={{color:c.text}}>{t.posted}: {asMoney(ledger.data.totals.posted_expenses_kgs)}</Text>
     <Text style={{color:c.text}}>{t.paid}: {asMoney(ledger.data.totals.settled_against_period_expenses_kgs)}</Text>
     <Text style={{color:c.text}}>{t.outstanding}: {asMoney(ledger.data.totals.outstanding_kgs)}</Text>
   </View>:null}
   {ledger.data&&!pending?<View style={{gap:8}}>
     <SectionLabel>{t.post}</SectionLabel>
     <Field label={t.name} value={title} onChangeText={setTitle}/>
     <Field label={t.amount} value={amount} keyboardType="number-pad" onChangeText={setAmount}/>
     <Field label={t.date} value={date} onChangeText={setDate}/>
     <Text style={{color:c.textMuted}}>{t.category}</Text>
     <View style={{flexDirection:'row',flexWrap:'wrap',gap:6}}>
       {CATEGORIES.map(item=><Button key={item} label={item}
         variant={category===item?'primary':'secondary'} onPress={()=>setCategory(item)}/>)}
     </View>
     <Field label={t.supplier} value={supplier} onChangeText={setSupplier}/>
     <Field label={t.reference} value={documentRef} onChangeText={setDocumentRef}/>
     <Field label={t.notes} value={notes} onChangeText={setNotes}/>
     <Button label={t.submit} testID="owner-expense-save" disabled={busy||!title||!amount}
       onPress={create}/>
   </View>:null}
   {pending?<Button label={t.retry} disabled={busy} testID="owner-expense-retry"
     variant="secondary" onPress={()=>void execute(pending)}/>:null}
   <SectionLabel>{t.payments}</SectionLabel>
   {ledger.data?.items.slice(0,25).map(item=><View key={item.id} style={{gap:5,paddingVertical:5}}>
     <Text style={{color:c.text}}>{item.title} · {asMoney(item.amount_kgs)}</Text>
     <Text style={{color:c.textMuted}}>{item.category} · {item.expense_date}
       {' · '+t.outstanding+': '+asMoney(item.outstanding_kgs)}</Text>
     {item.status==='POSTED'&&item.outstanding_kgs>0&&!pending?<>
       <Button label={t.newPayment} variant="secondary"
         onPress={()=>setSelectedExpense(selectedExpense===item.id?null:item.id)}/>
       {selectedExpense===item.id?<View style={{gap:5}}>
         <Field label={t.amount} value={settlementAmount} keyboardType="number-pad"
           onChangeText={setSettlementAmount}/>
         <Field label={t.paidOn} value={settlementDate} onChangeText={setSettlementDate}/>
         <Text style={{color:c.textMuted}}>{t.method}</Text>
         <View style={{flexDirection:'row',flexWrap:'wrap',gap:6}}>
           {METHODS.map(option=><Button key={option} label={option}
             variant={method===option?'primary':'secondary'} onPress={()=>setMethod(option)}/>)}
         </View>
         <Button label={t.submit} disabled={busy||!settlementAmount}
           onPress={()=>settle(item.id,item.outstanding_kgs)}/>
       </View>:null}
     </>:null}
   </View>)}
 </GlassCard>;
}
