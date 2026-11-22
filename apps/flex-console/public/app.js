/* MARINA SMART FLEX · role-bound read-only client. No browser access tokens. */
'use strict';
const translations = {
 ru:{commercial:'КОММЕРЧЕСКАЯ ПЛАТФОРМА',warning:'Нет реальных платежей и выплат. Доступ к гостиничной PMS не изменяется.',lang:'Язык',login:'Войти',logout:'Выйти',welcome:'Центр управления',overview:'Обзор',hotels:'Гостиницы',catalog:'Каталог функций',obligations:'Начисления партнёрам',subscription:'Моя подписка',earnings:'Мои начисления',notConfigured:'Отдельная QA-среда ещё не подключена',configHelp:'Для настоящих данных нужен отдельный FLEX API и платформенный OIDC/MFA. Пока здесь не показываются вымышленные финансы.',loginPrompt:'Для просмотра данных войдите через защищённый платформенный доступ.',hotelList:'Реестр гостиниц',search:'Поиск по названию',hotel:'Гостиница',status:'Статус',currency:'Валюта',actions:'Действия',open:'Открыть',noHotels:'Гостиницы ещё не зарегистрированы.',back:'Все гостиницы',invoices:'Счета',invoice:'Номер счёта',total:'Сумма',due:'Срок',noInvoices:'Счетов нет',noSubscription:'Активная подписка отсутствует.',planStatus:'Подписка',enforcement:'Режим контроля',periodStart:'Начало периода',periodEnd:'Конец периода',grace:'Льготный период',features:'Опубликованные функции',sku:'Код SKU',price:'Цена в месяц',noCatalog:'Опубликованных функций пока нет',accessDenied:'Нет доступа к этим данным',error:'Не удалось получить данные',retry:'Повторить',agent:'Агент продаж',investor:'Инвестор',net:'Начислено с учётом возвратов',gross:'Начислено',refunds:'Сторнировано',paid:'Фактически выплачено',events:'Операций',notImplemented:'Подтверждённые выплаты пока не подключены.',periodDay:'День',periodWeek:'Неделя',periodMonth:'Месяц',role:'Роль',readOnly:'Только чтение',noData:'Данных за период нет',activeHotels:'Гостиниц в реестре',activeSku:'Опубликованных функций',groups:'Категория',sum:'Начисления',helpQa:'Все значения поступают исключительно из FLEX QA API, не из PMS и не из макетов.',ownerHotels:'Ваши отели',selected:'Карточка гостиницы',openBack:'Вернуться',noSelected:'Нет закреплённых гостиниц',go:'Перейти',period:'Период',expires:'Истекает',count:'Количество',noPartners:'Начислений нет',emptyTitle:'Данных нет'},
 kg:{commercial:'КОММЕРЦИЯЛЫК ПЛАТФОРМА',warning:'Чыныгы төлөмдөр жана которуулар жок. Мейманкананын PMS тутуму өзгөрбөйт.',lang:'Тил',login:'Кирүү',logout:'Чыгуу',welcome:'Башкаруу борбору',overview:'Жалпы көрүнүш',hotels:'Мейманканалар',catalog:'Функциялар каталогу',obligations:'Өнөктөштөрдүн эсептөөлөрү',subscription:'Менин жазылуум',earnings:'Менин эсептөөлөрүм',notConfigured:'Өзүнчө QA чөйрөсү туташа элек',configHelp:'Чыныгы маалымат үчүн FLEX API жана OIDC/MFA керек. Бул жерде ойдон чыгарылган каржы маалыматтары жок.',loginPrompt:'Маалымат көрүү үчүн коопсуз каттоо аркылуу кириңиз.',hotelList:'Мейманканалар тизмеси',search:'Аты боюнча издөө',hotel:'Мейманкана',status:'Абалы',currency:'Валюта',actions:'Аракеттер',open:'Ачуу',noHotels:'Азырынча мейманканалар жок.',back:'Бардык мейманканалар',invoices:'Эсеп-фактуралар',invoice:'Эсеп номери',total:'Сумма',due:'Мөөнөт',noInvoices:'Эсептер жок',noSubscription:'Активдүү жазылуу жок.',planStatus:'Жазылуу',enforcement:'Көзөмөл режими',periodStart:'Мөөнөттүн башы',periodEnd:'Мөөнөттүн аягы',grace:'Жеңилдетилген мөөнөт',features:'Жарыяланган функциялар',sku:'SKU коду',price:'Айлык баа',noCatalog:'Азырынча функциялар жок',accessDenied:'Уруксат жок',error:'Маалымат алынбады',retry:'Кайра аракеттенүү',agent:'Сатуу агенти',investor:'Инвестор',net:'Кайтарууларды эске алган эсептөө',gross:'Эсептелди',refunds:'Жокко чыгарылды',paid:'Иш жүзүндө төлөндү',events:'Операциялар',notImplemented:'Ырасталган төлөмдөр туташа элек.',periodDay:'Күн',periodWeek:'Жума',periodMonth:'Ай',role:'Роль',readOnly:'Окуу гана',noData:'Бул мезгилге маалымат жок',activeHotels:'Мейманканалар',activeSku:'Жарыяланган функциялар',groups:'Топ',sum:'Эсептөөлөр',helpQa:'Баардык маалымат FLEX QA API аркылуу алынат.',ownerHotels:'Сиздин мейманканалар',selected:'Мейманкана картасы',openBack:'Артка',noSelected:'Бекитилген мейманкана жок',go:'Өтүү',period:'Мезгил',expires:'Бүтөт',count:'Саны',noPartners:'Эсептөөлөр жок',emptyTitle:'Маалымат жок'},
 en:{commercial:'COMMERCIAL CONTROL PLANE',warning:'Live payments and payouts are disabled. Hotel PMS data remains untouched.',lang:'Language',login:'Sign in',logout:'Sign out',welcome:'Control center',overview:'Overview',hotels:'Hotels',catalog:'Feature catalog',obligations:'Partner earnings',subscription:'My subscription',earnings:'My earnings',notConfigured:'Isolated QA environment is not configured',configHelp:'Real data requires the dedicated FLEX API and OIDC/MFA. No fictional financial data is displayed.',loginPrompt:'Sign in through the separate platform identity provider to view data.',hotelList:'Hotel registry',search:'Search hotels',hotel:'Hotel',status:'Status',currency:'Currency',actions:'Actions',open:'Open',noHotels:'No hotels registered yet.',back:'All hotels',invoices:'Invoices',invoice:'Invoice number',total:'Amount',due:'Due date',noInvoices:'No invoices',noSubscription:'No active subscription.',planStatus:'Subscription',enforcement:'Enforcement',periodStart:'Period start',periodEnd:'Period end',grace:'Grace period',features:'Published features',sku:'SKU code',price:'Monthly price',noCatalog:'No published features yet',accessDenied:'Access denied',error:'Unable to load data',retry:'Retry',agent:'Sales agent',investor:'Investor',net:'Net earned after reversals',gross:'Gross earned',refunds:'Reversed',paid:'Actually paid out',events:'Entries',notImplemented:'Verified payouts are not yet implemented.',periodDay:'Day',periodWeek:'Week',periodMonth:'Month',role:'Role',readOnly:'Read-only',noData:'No data this period',activeHotels:'Registered hotels',activeSku:'Published features',groups:'Group',sum:'Earnings',helpQa:'Figures come only from FLEX QA APIs—not from PMS or mockups.',ownerHotels:'Your hotels',selected:'Hotel details',openBack:'Back',noSelected:'No assigned hotels',go:'Go',period:'Period',expires:'Expires',count:'Count',noPartners:'No earnings entries',emptyTitle:'No data'}
};
const main=document.getElementById('content'), nav=document.getElementById('nav');
const state={lang:localStorage.getItem('flex_lang')||'ru',theme:localStorage.getItem('flex_theme')||'dark',view:'overview',period:'month',me:null,status:null,hotelId:null,search:'',serial:0};
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const t=k=>(translations[state.lang]||translations.ru)[k]||translations.ru[k]||k;
const fmt=v=>v===null||v===undefined?'—':new Intl.NumberFormat(state.lang==='kg'?'ky-KG':state.lang==='en'?'en-US':'ru-RU',{maximumFractionDigits:2}).format(Number(v));
const date=v=>v?new Date(/^\d{4}-\d{2}-\d{2}$/.test(String(v))?String(v)+'T12:00:00Z':v).toLocaleDateString(state.lang==='en'?'en-US':'ru-RU',{timeZone:/^\d{4}-\d{2}-\d{2}$/.test(String(v))?'UTC':'Asia/Bishkek'}):'—';
const heading=(title,subtitle='')=>'<div class="page-header"><div><div class="eyebrow">MARINA SMART FLEX / '+safe(t('readOnly'))+'</div><h1>'+safe(title)+'</h1><div class="muted">'+safe(subtitle)+'</div></div><span class="role-mark">'+safe(state.me?.role||'QA')+'</span></div>';
const metric=(label,value,klass='')=>'<div class="panel metric"><small>'+safe(label)+'</small><strong class="'+klass+'">'+safe(value)+'</strong></div>';
const info=(message,type='info')=>'<div class="notice '+type+'">'+safe(message)+'</div>';
const empty=(message)=>'<div class="empty"><strong>'+safe(t('emptyTitle'))+'</strong>'+safe(message)+'</div>';
const kv=(title,value)=>'<div class="metric"><small>'+safe(title)+'</small><strong>'+safe(value??'—')+'</strong></div>';
const table=(columns,rows)=>'<div class="table-wrap"><table class="table"><thead><tr>'+columns.map(c=>'<th>'+safe(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table></div>';
const money=(v,currency='KGS')=>v===null||v===undefined?'—':fmt(v)+' '+safe(currency);
async function api(path){const r=await fetch('/api/data'+path,{credentials:'same-origin',cache:'no-store'});let data={};try{data=await r.json()}catch{}if(!r.ok){const e=new Error(data.error||('HTTP '+r.status));e.status=r.status;throw e}return data}
function renderNav(){
 const r=state.me?.role;
 const choices=r==='SUPER_ADMIN'?[['overview','overview','◈'],['hotels','hotels','⌂'],['catalog','catalog','◇'],['obligations','obligations','↗']]:
 r==='HOTEL_OWNER'?[['subscription','subscription','⌂'],['catalog','catalog','◇']]:
 r==='SALES_AGENT'||r==='INVESTOR'?[['earnings','earnings','↗']]:[];
 nav.innerHTML=choices.map(([id,label,icon])=>'<button type="button" data-view="'+id+'" class="'+(state.view===id?'active':'')+'"><span>'+icon+'</span>'+safe(t(label))+'</button>').join('');
 document.getElementById('session-button').textContent=t(state.me?'logout':'login');
 document.querySelectorAll('[data-i18n]').forEach(x=>x.textContent=t(x.dataset.i18n));
}
function showLogin(){
 nav.innerHTML='';
 document.getElementById('session-button').textContent=t('login');
 const configured=state.status?.configured;
 main.innerHTML=heading(configured?t('loginPrompt'):t('notConfigured'))+
 '<div class="panel gold"><h2>MARINA FLEX · CONTROL PLANE</h2><p class="muted">'+safe(configured?t('loginPrompt'):t('configHelp'))+'</p>'+
 (configured?'<button class="primary" type="button" data-login="yes">'+safe(t('login'))+'</button>':'')+'</div>'+
 info('DATA STATUS: '+(configured?'AUTH REQUIRED':'NO QA ISSUER / NO LIVE DATA'),'info');
}
function periodButtons(){return '<div class="period" role="group" aria-label="'+safe(t('period'))+'">'+[['day','periodDay'],['week','periodWeek'],['month','periodMonth']].map(([p,k])=>'<button type="button" data-period="'+p+'" class="'+(state.period===p?'active':'')+'">'+safe(t(k))+'</button>').join('')+'</div>'}
function errorPage(err){const msg=err?.status===403?t('accessDenied'):t('error');main.innerHTML=heading(msg)+info(err.message||msg,'error')+'<button class="outline" type="button" data-retry="1">'+safe(t('retry'))+'</button>';}
async function overview(){
 const results=await Promise.allSettled([api('/v1/hotels'),api('/v1/catalog'),api('/v1/platform/partner-earnings-summary?period='+state.period)]);
 const h=results[0].status==='fulfilled'?results[0].value:null;
 const c=results[1].status==='fulfilled'?results[1].value:null;
 const e=results[2].status==='fulfilled'?results[2].value:null;
 if(!h&&!c&&!e) throw results[0].reason;
 return heading(t('welcome'),t('helpQa'))+periodButtons()+'<div class="grid spacing-top">'+metric(t('activeHotels'),h?.length??'—','cyan-text')+
 metric(t('activeSku'),c?.length??'—','gold-text')+metric(t('groups'),e?.groups?.length??'—')+metric(t('readOnly'),'QA')+'</div>'+
 '<div class="grid two"><section class="panel"><h2>'+safe(t('hotels'))+'</h2>'+(h?.length?hotelTable(h.slice(0,5)):empty(t('noHotels')))+
 '<button class="subtle" type="button" data-view="hotels">'+safe(t('back'))+' →</button></section><section class="panel"><h2>'+safe(t('obligations'))+'</h2>'+
 (e?earningsSummary(e):empty(t('noPartners')))+'<button class="subtle" type="button" data-view="obligations">'+safe(t('go'))+' →</button></section></div>'+
 info(t('warning'),'info');
}
function hotelTable(items){return table([t('hotel'),t('status'),t('currency'),t('actions')],items.map(h=>'<tr><td>'+safe(h.name)+'</td><td><span class="chip">'+safe(h.status)+'</span></td><td>'+safe(h.currency)+'</td><td><button class="subtle" type="button" data-hotel="'+safe(h.id)+'">'+safe(t('open'))+' →</button></td></tr>'))}
async function hotelList(){
 const hotels=await api('/v1/hotels');
 const filtered=hotels.filter(h=>h.name?.toLocaleLowerCase().includes(state.search.toLocaleLowerCase()));
 return heading(t('hotelList'),t('helpQa'))+'<div class="formbar"><input id="hotel-search" type="search" placeholder="'+safe(t('search'))+'" value="'+safe(state.search)+'"><span class="role-mark">'+safe(hotels.length)+' '+safe(t('count'))+'</span></div><section class="panel">'+(filtered.length?hotelTable(filtered):empty(t('noHotels')))+'</section>';
}
async function hotelDetail(){
 const id=state.hotelId;
 if(!/^[0-9a-fA-F-]{36}$/.test(id||'')) return heading(t('noSelected'))+empty(t('noSelected'));
 const [sub,inv]=await Promise.allSettled([api('/v1/hotels/'+id+'/subscription'),api('/v1/hotels/'+id+'/invoices')]);
 const subscription=sub.status==='fulfilled'?sub.value:null;
 const invoices=inv.status==='fulfilled'?inv.value:null;
 if(sub.status==='rejected'&&sub.reason.status===403)throw sub.reason;
 if(inv.status==='rejected'&&inv.reason.status===403)throw inv.reason;
 return heading(t('selected'),id)+'<button type="button" class="subtle" data-view="'+(state.me?.role==='SUPER_ADMIN'?'hotels':'subscription')+'">← '+safe(t('openBack'))+'</button>'+
 '<div class="grid three spacing-top">'+metric(t('planStatus'),subscription?.status??'—')+metric(t('enforcement'),subscription?.enforcement??'—')+metric(t('expires'),date(subscription?.period_end))+'</div>'+
 '<section class="panel"><h2>'+safe(t('subscription'))+'</h2>'+(subscription?'<div class="grid three">'+kv(t('periodStart'),date(subscription.period_start))+kv(t('periodEnd'),date(subscription.period_end))+kv(t('grace'),date(subscription.grace_until))+'</div>':empty(t('noSubscription')))+'</section>'+
 '<section class="panel"><h2>'+safe(t('invoices'))+'</h2>'+(invoices?.length?table([t('invoice'),t('status'),t('total'),t('due')],invoices.map(i=>'<tr><td>'+safe(i.number||i.id)+'</td><td><span class="chip">'+safe(i.status)+'</span></td><td>'+money(i.total,i.currency)+'</td><td>'+safe(date(i.due_at))+'</td></tr>')):empty(t('noInvoices')))+'</section>'+info(t('warning'),'info');
}
async function catalog(){
 const items=await api('/v1/catalog');
 return heading(t('features'),t('helpQa'))+'<div class="grid three">'+metric(t('activeSku'),items.length,'cyan-text')+metric(t('currency'),'KGS')+metric(t('readOnly'),'ON')+'</div>'+
 '<section class="panel">'+(items.length?table([t('sku'),t('features'),t('price'),t('status')],items.map(i=>'<tr><td>'+safe(i.sku)+'</td><td>'+safe(i.name)+'</td><td>'+money(i.monthly_list_price,i.currency)+'</td><td><span class="chip">v'+safe(i.price_version)+'</span></td></tr>')):empty(t('noCatalog')))+'</section>';
}
function earningsSummary(o){return (o.groups?.length?table([t('groups'),t('gross'),t('refunds'),t('net')],o.groups.map(g=>'<tr><td>'+safe(g.role)+'</td><td>'+money(g.accrued_gross_kg)+'</td><td>'+money(g.reversed_kg)+'</td><td>'+money(g.net_accrued_kg)+'</td></tr>')):empty(t('noPartners')))+info('QA_ONLY_NOT_BANK_RECONCILED','info')}
async function obligations(){const r=await api('/v1/platform/partner-earnings-summary?period='+state.period);return heading(t('obligations'),t('helpQa'))+periodButtons()+'<section class="panel spacing-top">'+earningsSummary(r)+'</section>'+info(t('notImplemented'))}
async function earnings(){
 const r=await api('/v1/partner/me/earnings?period='+state.period);
 return heading(state.me.role==='INVESTOR'?t('investor'):t('agent'),t('helpQa'))+periodButtons()+'<div class="grid spacing-top">'+
 metric(t('gross'),money(r.accrued_gross_kg),'cyan-text')+metric(t('refunds'),money(r.reversed_kg))+
 metric(t('net'),money(r.net_accrued_kg),'gold-text')+metric(t('paid'),money(r.actual_paid_kg))+'</div>'+
 '<section class="panel"><h2>'+safe(t('earnings'))+'</h2><div class="grid two">'+kv(t('events'),r.events)+kv(t('role'),r.role)+'</div></section>'+info(t('notImplemented'))+info(safe(r.data_provenance||'QA_ONLY'),'info');
}
async function subscription(){
 const hotels=state.me?.hotels||[];
 if(!hotels.length)return heading(t('subscription'))+empty(t('noSelected'));
 if(!state.hotelId||!hotels.includes(state.hotelId))state.hotelId=hotels[0];
 const buttons=hotels.length>1?'<div class="formbar">'+hotels.map(id=>'<button class="outline" data-hotel="'+safe(id)+'" type="button">'+safe(id.slice(0,8))+'</button>').join('')+'</div>':'';
 const details=await hotelDetail();return buttons+details;
}
async function render(){
 const serial=++state.serial;
 renderNav();
 if(!state.me){showLogin();return;}
 main.innerHTML='<div class="skeleton" aria-label="Loading"></div>';
 try{const views={overview,hotels:hotelList,catalog,obligations,hotel:hotelDetail,subscription,earnings};const html=await (views[state.view]||overview)();if(serial!==state.serial)return;main.innerHTML=html;}
 catch(err){if(serial===state.serial)errorPage(err);}
}
async function start(){
 document.documentElement.lang=state.lang==='kg'?'ky':state.lang;
 document.getElementById('lang').value=state.lang;
 document.body.classList.toggle('light',state.theme==='light');
 try {const r=await fetch('/api/status',{cache:'no-store'});state.status=await r.json();}catch{state.status={configured:false};}
 if(state.status.configured){try{state.me=await api('/v1/me');}catch(e){if(e.status!==401)state.error=e;}}
 if(state.me){const role=state.me.role;state.view=role==='SUPER_ADMIN'?'overview':role==='HOTEL_OWNER'?'subscription':'earnings';}
 render();
}
nav.addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b){state.view=b.dataset.view;state.hotelId=null;state.search='';render();}});
main.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.view){state.view=b.dataset.view;state.hotelId=null;render();}
 if(b.dataset.hotel){state.hotelId=b.dataset.hotel;state.view=state.me.role==='SUPER_ADMIN'?'hotel':'subscription';render();}
 if(b.dataset.period){state.period=b.dataset.period;render();}
 if(b.dataset.retry)render();
 if(b.dataset.login)location.assign('/api/auth/login');
});
main.addEventListener('input',e=>{if(e.target.id==='hotel-search'){state.search=e.target.value;const rows=main.querySelectorAll('tbody tr');rows.forEach(tr=>tr.hidden=!tr.textContent.toLocaleLowerCase().includes(state.search.toLocaleLowerCase()));}});
document.getElementById('lang').addEventListener('change',e=>{state.lang=e.target.value;localStorage.setItem('flex_lang',state.lang);document.documentElement.lang=state.lang==='kg'?'ky':state.lang;render()});
document.getElementById('theme').addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';localStorage.setItem('flex_theme',state.theme);document.body.classList.toggle('light',state.theme==='light')});
document.getElementById('session-button').addEventListener('click',()=>location.assign(state.me?'/api/auth/logout':'/api/auth/login'));
start();
