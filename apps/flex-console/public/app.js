/* MARINA SMART FLEX · role-bound read-only client. No browser access tokens. */
'use strict';
const translations = {
 ru:{commercial:'КОММЕРЧЕСКАЯ ПЛАТФОРМА',warning:'Нет реальных платежей и выплат. Доступ к гостиничной PMS не изменяется.',lang:'Язык',login:'Войти',logout:'Выйти',welcome:'Центр управления',overview:'Обзор',hotels:'Гостиницы',catalog:'Каталог функций',obligations:'Начисления партнёрам',subscription:'Моя подписка',earnings:'Мои начисления',notConfigured:'Отдельная QA-среда ещё не подключена',configHelp:'Для настоящих данных нужен отдельный FLEX API и платформенный OIDC/MFA. Пока здесь не показываются вымышленные финансы.',loginPrompt:'Для просмотра данных войдите через защищённый платформенный доступ.',hotelList:'Реестр гостиниц',search:'Поиск по названию',hotel:'Гостиница',status:'Статус',currency:'Валюта',actions:'Действия',open:'Открыть',noHotels:'Гостиницы ещё не зарегистрированы.',back:'Все гостиницы',invoices:'Счета',invoice:'Номер счёта',total:'Сумма',due:'Срок',noInvoices:'Счетов нет',noSubscription:'Активная подписка отсутствует.',planStatus:'Подписка',enforcement:'Режим контроля',periodStart:'Начало периода',periodEnd:'Конец периода',grace:'Льготный период',features:'Опубликованные функции',sku:'Код SKU',price:'Цена в месяц',noCatalog:'Опубликованных функций пока нет',accessDenied:'Нет доступа к этим данным',error:'Не удалось получить данные',retry:'Повторить',agent:'Агент продаж',investor:'Инвестор',net:'Начислено с учётом возвратов',gross:'Начислено',refunds:'Сторнировано',paid:'Фактически выплачено',events:'Операций',notImplemented:'Подтверждённые выплаты пока не подключены.',periodDay:'День',periodWeek:'Неделя',periodMonth:'Месяц',role:'Роль',billingHold:'Роль BILLING: управление платежами отключено до отдельного решения.',readOnly:'Только чтение',noData:'Данных за период нет',activeHotels:'Гостиниц в реестре',activeSku:'Опубликованных функций',groups:'Категория',sum:'Начисления',helpQa:'Все значения поступают исключительно из FLEX QA API, не из PMS и не из макетов.',ownerHotels:'Ваши отели',selected:'Карточка гостиницы',openBack:'Вернуться',noSelected:'Нет закреплённых гостиниц',go:'Перейти',period:'Период',expires:'Истекает',count:'Количество',noPartners:'Начислений нет',emptyTitle:'Данных нет',addHotel:'Добавить гостиницу',createHotel:'Создать тестовую гостиницу',registerHotel:'Зарегистрировать в QA',name:'Название гостиницы',cancel:'Отмена',refresh:'Обновить',export:'Экспорт CSV',onlyQa:'Регистрация создаёт только PENDING-запись в отдельном FLEX QA. Она не активирует подписку и не изменяет PMS.',notEnabled:'Создание гостиницы станет доступно после подключения изолированного FLEX QA и MFA.',created:'Гостиница зарегистрирована в QA',saving:'Сохранение...',allStatuses:'Все статусы',registered:'Регистрация',qaScope:'Только синтетические тестовые данные. Не используйте реальные имена, договоры и платежи.',linkHotel:'Связать с MARINA SMART',linkTitle:'Подтверждение связи гостиницы',linkHelp:'Подключение требует доверенной подписи MARINA SMART. Заявка сама не подключает и не активирует гостиницу.',linkDisabled:'Доверенное подключение доступно только в изолированной FLEX QA после настройки подписывающего сервера.',deployment:'ID проверенного развёртывания',property:'ID гостиницы в MARINA SMART',createChallenge:'Запросить проверку связи',challenge:'Подписываемое сообщение',expiresAt:'Действительно до',signature:'Подпись доверенного сервера (Base64)',confirmLink:'Подтвердить подпись',linked:'Связь криптографически подтверждена; подписка НЕ активирована.',challengeResult:'Запрос на подпись создан. Передайте сообщение доверенному серверу MARINA SMART.',linkError:'Проверка связи отклонена',badSignature:'Нужна подпись от доверенного сервера, нельзя вводить произвольную строку.',hotelError:'Регистрация отклонена сервером',searchHelp:'Фильтр по названию и статусу',adminCatalog:'Управление каталогом',createSku:'Добавить функцию (план)',newPrice:'Новая версия цены',priceHistory:'История цен',skuTitle:'Название функции',capability:'Серверная возможность',startPrice:'Дата начала действия цены',savePlanned:'Создать PLANNED SKU',savePrice:'Сохранить будущую цену',skuVersion:'Версия',sourceStatus:'Каталог',configure:'Черновик подписки',configurationDraft:'Новый черновик подписки',draftList:'История черновиков',draftTitle:'Название пакета',selectFunctions:'Функции для предложения',saveDraft:'Сохранить черновик',draftOnly:'Это коммерческий черновик без оплаты, активации подписки и изменения доступа. Не создаёт договор или счёт.',notPublished:'Созданная функция имеет статус PLANNED; нельзя считать её доступной гостиницам до отдельной публикации.',priceChanged:'Новая версия цены записана; прежняя история сохранена.',draftCreated:'Черновик сохранён. Доступ не изменён.',noDrafts:'Черновиков пока нет',noSelectable:'Сначала необходимо наличие утверждённых доступных SKU с ценами на дату начала.',draftSettings:'Параметры подписки',yearPrice:'Цена в KGS за месяц',operationBlocked:'Администрирование каталога доступно только в отдельной FLEX QA после настройки MFA.',adminError:'Сервер отклонил операцию',openHistory:'История',monthlyEstimate:'Предварительная стоимость за месяц',onlyFuture:'Стоимость вступит в силу только с указанной будущей даты.'},
 kg:{commercial:'КОММЕРЦИЯЛЫК ПЛАТФОРМА',warning:'Чыныгы төлөмдөр жана которуулар жок. Мейманкананын PMS тутуму өзгөрбөйт.',lang:'Тил',login:'Кирүү',logout:'Чыгуу',welcome:'Башкаруу борбору',overview:'Жалпы көрүнүш',hotels:'Мейманканалар',catalog:'Функциялар каталогу',obligations:'Өнөктөштөрдүн эсептөөлөрү',subscription:'Менин жазылуум',earnings:'Менин эсептөөлөрүм',notConfigured:'Өзүнчө QA чөйрөсү туташа элек',configHelp:'Чыныгы маалымат үчүн FLEX API жана OIDC/MFA керек. Бул жерде ойдон чыгарылган каржы маалыматтары жок.',loginPrompt:'Маалымат көрүү үчүн коопсуз каттоо аркылуу кириңиз.',hotelList:'Мейманканалар тизмеси',search:'Аты боюнча издөө',hotel:'Мейманкана',status:'Абалы',currency:'Валюта',actions:'Аракеттер',open:'Ачуу',noHotels:'Азырынча мейманканалар жок.',back:'Бардык мейманканалар',invoices:'Эсеп-фактуралар',invoice:'Эсеп номери',total:'Сумма',due:'Мөөнөт',noInvoices:'Эсептер жок',noSubscription:'Активдүү жазылуу жок.',planStatus:'Жазылуу',enforcement:'Көзөмөл режими',periodStart:'Мөөнөттүн башы',periodEnd:'Мөөнөттүн аягы',grace:'Жеңилдетилген мөөнөт',features:'Жарыяланган функциялар',sku:'SKU коду',price:'Айлык баа',noCatalog:'Азырынча функциялар жок',accessDenied:'Уруксат жок',error:'Маалымат алынбады',retry:'Кайра аракеттенүү',agent:'Сатуу агенти',investor:'Инвестор',net:'Кайтарууларды эске алган эсептөө',gross:'Эсептелди',refunds:'Жокко чыгарылды',paid:'Иш жүзүндө төлөндү',events:'Операциялар',notImplemented:'Ырасталган төлөмдөр туташа элек.',periodDay:'Күн',periodWeek:'Жума',periodMonth:'Ай',role:'Роль',billingHold:'BILLING ролу: төлөмдөрдү башкаруу өзүнчө чечимге чейин өчүрүлгөн.',readOnly:'Окуу гана',noData:'Бул мезгилге маалымат жок',activeHotels:'Мейманканалар',activeSku:'Жарыяланган функциялар',groups:'Топ',sum:'Эсептөөлөр',helpQa:'Баардык маалымат FLEX QA API аркылуу алынат.',ownerHotels:'Сиздин мейманканалар',selected:'Мейманкана картасы',openBack:'Артка',noSelected:'Бекитилген мейманкана жок',go:'Өтүү',period:'Мезгил',expires:'Бүтөт',count:'Саны',noPartners:'Эсептөөлөр жок',emptyTitle:'Маалымат жок',addHotel:'Мейманкана кошуу',createHotel:'QA мейманканасын түзүү',registerHotel:'QA каттоо',name:'Мейманкананын аталышы',cancel:'Жокко чыгаруу',refresh:'Жаңыртуу',export:'CSV чыгаруу',onlyQa:'QA ичинде PENDING гана түзүлөт. Жазылууга жана PMSке таасир этпейт.',notEnabled:'Жаңы мейманкана үчүн өзүнчө QA жана MFA керек.',created:'QA мейманкана катталды',saving:'Сакталууда...',allStatuses:'Бардык абалдар',registered:'Каттоо',qaScope:'Синтетикалык тесттик гана маалымат. Чыныгы келишимдерди колдонбоңуз.',linkHotel:'MARINA SMART менен туташтыруу',linkTitle:'Мейманкананы байланыштыруу',linkHelp:'MARINA SMART кол тамгасы керек. Суроо автоматтык кошпойт.',linkDisabled:'QA жана ишенимдүү кол тамга сервери керек.',deployment:'Текшерилген жайгаштыруу ID',property:'MARINA SMART ичиндеги мейманкана ID',createChallenge:'Байланышты текшерүү',challenge:'Кол коюлуучу билдирүү',expiresAt:'Мөөнөтү',signature:'Ишенимдүү сервердин кол тамгасы (Base64)',confirmLink:'Кол тамганы текшерүү',linked:'Байланыш ырасталды, жазылуу иштетилген жок.',challengeResult:'Суроо түзүлдү. Билдирүүнү ишенимдүү MARINA SMART серверине бериңиз.',linkError:'Байланыш четке кагылды',badSignature:'Ишенимдүү сервердин кол тамгасы керек.',hotelError:'Сервер каттоодон баш тартты',searchHelp:'Аты жана абалы боюнча чыпка',adminCatalog:'Каталогду башкаруу',createSku:'Функция кошуу (план)',newPrice:'Жаңы баа версиясы',priceHistory:'Баалардын тарыхы',skuTitle:'Функциянын аты',capability:'Сервер мүмкүнчүлүгү',startPrice:'Баанын башталышы',savePlanned:'PLANNED SKU түзүү',savePrice:'Келечектеги бааны сактоо',skuVersion:'Версия',sourceStatus:'Каталог',configure:'Жазылуунун долбоору',configurationDraft:'Жазылуунун долбоору',draftList:'Долбоорлор тарыхы',draftTitle:'Пакеттин аталышы',selectFunctions:'Сунуш функциялары',saveDraft:'Долбоорду сактоо',draftOnly:'Бул төлөмсүз жана активдешүүсүз коммерциялык долбоор. Келишим же эсеп түзбөйт.',notPublished:'Функция PLANNED абалында, мейманканаларга ачылбайт.',priceChanged:'Жаңы версия сакталды, мурунку баалар өзгөргөн жок.',draftCreated:'Долбоор сакталды, укуктар өзгөргөн жок.',noDrafts:'Долбоор жок',noSelectable:'Алгач жеткиликтүү SKU баалары керек.',draftSettings:'Жазылуу параметрлери',yearPrice:'Айына сом',operationBlocked:'Бул үчүн өзүнчө FLEX QA жана MFA керек.',adminError:'Сервер четке какты',openHistory:'Тарых',monthlyEstimate:'Айлык болжол',onlyFuture:'Баанын күчү көрсөтүлгөн күнү башталат.'},
 en:{commercial:'COMMERCIAL CONTROL PLANE',warning:'Live payments and payouts are disabled. Hotel PMS data remains untouched.',lang:'Language',login:'Sign in',logout:'Sign out',welcome:'Control center',overview:'Overview',hotels:'Hotels',catalog:'Feature catalog',obligations:'Partner earnings',subscription:'My subscription',earnings:'My earnings',notConfigured:'Isolated QA environment is not configured',configHelp:'Real data requires the dedicated FLEX API and OIDC/MFA. No fictional financial data is displayed.',loginPrompt:'Sign in through the separate platform identity provider to view data.',hotelList:'Hotel registry',search:'Search hotels',hotel:'Hotel',status:'Status',currency:'Currency',actions:'Actions',open:'Open',noHotels:'No hotels registered yet.',back:'All hotels',invoices:'Invoices',invoice:'Invoice number',total:'Amount',due:'Due date',noInvoices:'No invoices',noSubscription:'No active subscription.',planStatus:'Subscription',enforcement:'Enforcement',periodStart:'Period start',periodEnd:'Period end',grace:'Grace period',features:'Published features',sku:'SKU code',price:'Monthly price',noCatalog:'No published features yet',accessDenied:'Access denied',error:'Unable to load data',retry:'Retry',agent:'Sales agent',investor:'Investor',net:'Net earned after reversals',gross:'Gross earned',refunds:'Reversed',paid:'Actually paid out',events:'Entries',notImplemented:'Verified payouts are not yet implemented.',periodDay:'Day',periodWeek:'Week',periodMonth:'Month',role:'Role',billingHold:'BILLING role: payment management remains disabled until separately approved.',readOnly:'Read-only',noData:'No data this period',activeHotels:'Registered hotels',activeSku:'Published features',groups:'Group',sum:'Earnings',helpQa:'Figures come only from FLEX QA APIs—not from PMS or mockups.',ownerHotels:'Your hotels',selected:'Hotel details',openBack:'Back',noSelected:'No assigned hotels',go:'Go',period:'Period',expires:'Expires',count:'Count',noPartners:'No earnings entries',emptyTitle:'No data',addHotel:'Add hotel',createHotel:'Register QA hotel',registerHotel:'Register in QA',name:'Hotel name',cancel:'Cancel',refresh:'Refresh',export:'Export CSV',onlyQa:'Creates a PENDING record in separate FLEX QA only. Does not activate a subscription or modify PMS.',notEnabled:'Hotel onboarding requires isolated FLEX QA and MFA.',created:'Hotel registered in QA',saving:'Saving...',allStatuses:'All statuses',registered:'Registration',qaScope:'Synthetic test data only. Do not use real contracts or payments.',linkHotel:'Link to MARINA SMART',linkTitle:'Verify hotel ownership',linkHelp:'A trusted MARINA SMART deployment signature is required. Creating a challenge never links or activates a subscription.',linkDisabled:'Trusted linking requires isolated FLEX QA and an approved MARINA SMART signer.',deployment:'Trusted deployment ID',property:'Property ID in MARINA SMART',createChallenge:'Request link verification',challenge:'Message to be signed',expiresAt:'Expires',signature:'Trusted deployment signature (Base64)',confirmLink:'Verify signature',linked:'Trusted link verified; subscription remains inactive.',challengeResult:'Verification request created. Hand this message to the trusted MARINA SMART deployment signer.',linkError:'Link verification rejected',badSignature:'The signature must come from a trusted deployment, not a guessed value.',hotelError:'Hotel registration rejected by server',searchHelp:'Filter by name and status',adminCatalog:'Catalog administration',createSku:'Add planned feature',newPrice:'New price version',priceHistory:'Price history',skuTitle:'Feature title',capability:'Server capability',startPrice:'Price effective from',savePlanned:'Create PLANNED SKU',savePrice:'Save future price',skuVersion:'Version',sourceStatus:'Catalog',configure:'Subscription configuration draft',configurationDraft:'New subscription draft',draftList:'Draft version history',draftTitle:'Package title',selectFunctions:'Features to propose',saveDraft:'Save draft',draftOnly:'Commercial proposal only. No payment, subscription activation, entitlement or invoice. Not a signed contract.',notPublished:'New SKU remains PLANNED until separately reviewed and published. It is not available to hotels.',priceChanged:'A new price version was appended; prior history is retained.',draftCreated:'Draft saved. Hotel access remains unchanged.',noDrafts:'No drafts yet',noSelectable:'Approved AVAILABLE SKUs with effective prices are required first.',draftSettings:'Subscription configuration',yearPrice:'Monthly KGS',operationBlocked:'Catalog administration requires isolated FLEX QA and verified admin MFA.',adminError:'Backend rejected the request',openHistory:'History',monthlyEstimate:'Estimated monthly KGS',onlyFuture:'Price becomes effective only on the selected future date.'}
};
const main=document.getElementById('content'), nav=document.getElementById('nav');

/* Separate Better Auth identity sign-in. This never authorizes FLEX API,
 * assigns a role, produces a JWT or marks MFA complete based on browser state.
 */
const identityCopy={
 ru:{heading:'Вход в MARINA SMART FLEX',email:'Электронная почта',password:'Пароль',signIn:'Продолжить',mfa:'Код из приложения-аутентификатора',verify:'Подтвердить код',onlyIdentity:'Вход в учётную запись не предоставляет доступ SUPER ADMIN. Права откроются только после проверенного MFA и серверного подтверждения роли.',signedIn:'Учётная запись подключена. Коммерческий доступ ещё не активирован.',signOut:'Выйти из учётной записи',failed:'Не удалось подтвердить учётную запись',disabled:'Вход ещё не настроен',totpHint:'Введите шесть цифр из приложения-аутентификатора.'},
 kg:{heading:'MARINA SMART FLEX системасына кирүү',email:'Электрондук почта',password:'Сырсөз',signIn:'Улантуу',mfa:'Аутентификатор колдонмосундагы код',verify:'Кодду ырастоо',onlyIdentity:'Каттоо эсебине кирүү SUPER ADMIN укугун бербейт. Укук MFA жана серверде роль текшерилгенден кийин гана берилет.',signedIn:'Каттоо эсебине кирдиңиз. Коммерциялык мүмкүнчүлүктөр азырынча ачыла элек.',signOut:'Каттоо эсебинен чыгуу',failed:'Каттоо эсеби ырасталган жок',disabled:'Кирүү али жөндөлө элек',totpHint:'Аутентификатор колдонмосундагы алты орундуу кодду киргизиңиз.'},
 en:{heading:'Sign in to MARINA SMART FLEX',email:'Email',password:'Password',signIn:'Continue',mfa:'Authenticator code',verify:'Verify code',onlyIdentity:'Signing in does not grant SUPER ADMIN access. Commercial permissions require verified MFA and a server-authorized role.',signedIn:'Identity session active. Commercial access is not yet enabled.',signOut:'Sign out of identity',failed:'Unable to verify identity',disabled:'Identity sign-in is not configured yet',totpHint:'Enter the six-digit code from your authenticator app.'}
};
function identityText(key){return (identityCopy[state.lang]||identityCopy.ru)[key];}
async function identityRequest(endpoint,body){
 const response=await fetch('/api/identity/'+endpoint,{
   method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',
   headers:{'Content-Type':'application/json','Accept':'application/json'},
   body:JSON.stringify(body)
 });
 const payload=await response.json().catch(()=>({}));
 if(!response.ok)throw Error('IDENTITY_REJECTED');
 return payload;
}
async function identitySession(){
 try {
   const response=await fetch('/api/identity/get-session',{credentials:'same-origin',cache:'no-store'});
   return response.ok?await response.json():null;
 } catch{return null;}
}
async function submitIdentityForm(form){
 const btn=form.querySelector('button[type="submit"]');
 if(btn)btn.disabled=true;
 try{
   if(form.id==='flex-identity-signin'){
     const data=await identityRequest('sign-in/email',{
       email:String(form.elements.email.value||'').trim(),
       password:String(form.elements.password.value||'')
     });
     form.elements.password.value='';
     state.identityStep=data.twoFactorRedirect===true?'totp':'session';
   }else if(form.id==='flex-identity-totp'){
     const code=String(form.elements.code.value||'').trim();
     if(!/^\\d{6}$/.test(code))throw Error('INVALID_TOTP_CODE');
     await identityRequest('two-factor/verify-totp',{code,trustDevice:false});
     form.elements.code.value='';
     state.identityStep='session';
   }
   state.identityError='';
   state.identitySession=await identitySession();
   // Never set state.me: platform authorization is separate from identity.
   render();
 }catch{
   state.identityError=identityText('failed');
   if(btn)btn.disabled=false;
   render();
 }
}
function identityPanel(){
 const text=identityText;
 const note='<p class="muted">'+safe(text('onlyIdentity'))+'</p>';
 if(state.identitySession?.user)return '<section class="panel gold"><h2>'+safe(text('heading'))+'</h2>'+
   '<p>'+safe(text('signedIn'))+'</p>'+note+
   '<button type="button" class="outline" data-identity-logout="yes">'+safe(text('signOut'))+'</button></section>';
 if(state.identityStep==='totp')return '<section class="panel gold"><h2>'+safe(text('mfa'))+'</h2>'+
   '<p class="muted">'+safe(text('totpHint'))+'</p><form id="flex-identity-totp">'+
   '<label>'+safe(text('mfa'))+'<input name="code" type="text" inputmode="numeric" pattern="[0-9]{6}" minlength="6" maxlength="6" autocomplete="one-time-code" required></label>'+
   '<button class="primary" type="submit">'+safe(text('verify'))+'</button></form>'+
   (state.identityError?'<p role="alert">'+safe(state.identityError)+'</p>':'')+note+'</section>';
 return '<section class="panel gold"><h2>'+safe(text('heading'))+'</h2><form id="flex-identity-signin">'+
   '<label>'+safe(text('email'))+'<input name="email" type="email" autocomplete="username" required maxlength="254"></label>'+
   '<label>'+safe(text('password'))+'<input name="password" type="password" autocomplete="current-password" required minlength="12"></label>'+
   '<button class="primary" type="submit">'+safe(text('signIn'))+'</button></form>'+
   (state.identityError?'<p role="alert">'+safe(state.identityError)+'</p>':'')+note+'</section>';
}

const state={lang:localStorage.getItem('flex_lang')||'ru',theme:localStorage.getItem('flex_theme')||'dark',view:'overview',period:'month',me:null,status:null,hotelId:null,search:'',serial:0,hotelStatus:'',lastCreated:null,registerKey:null,registerName:null,linkChallenge:null,linkSuccess:false,catalogItems:[],priceSku:null,identityStep:'email',identityError:'',identitySession:null};
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
function csvCell(v){
 const raw=String(v??'');
 const protectedText=/^[\s]*[=+@-]/.test(raw)?"'"+raw:raw;
 return '"'+protectedText.replace(/"/g,'""')+'"';
}
function saveCsv(filename,columns,rows){
 const csv='\uFEFF'+[columns,...rows].map(row=>row.map(csvCell).join(';')).join('\r\n');
 const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download=filename.replace(/[^a-zA-Z0-9_.-]/g,'_')+'.csv';
 document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
}
async function exportVisible(){
 const role=state.me?.role, view=state.view;
 let headers=[],rows=[],name='marina_flex_QA_'+view;
 if(role==='SUPER_ADMIN'&&(view==='hotels'||view==='overview')){
   const records=await api('/v1/hotels');
   headers=['ID','Hotel','Status','Currency'];
   rows=records.map(h=>[h.id,h.name,h.status,h.currency]);
 }else if(['SUPER_ADMIN','HOTEL_OWNER'].includes(role)&&view==='catalog'){
   const records=await api('/v1/catalog');
   headers=['SKU','Name','Capability','Version','Monthly KGS'];
   rows=records.map(x=>[x.sku,x.name,x.capability,x.price_version,x.monthly_list_price]);
 }else if(['SUPER_ADMIN','HOTEL_OWNER'].includes(role)&&(view==='hotel'||view==='subscription')){
   const id=state.hotelId||state.me.hotels?.[0];if(!id)throw Error(t('noSelected'));
   const records=await api('/v1/hotels/'+id+'/invoices');
   headers=['Invoice ID','Number','Status','Total','Currency','Due'];
   rows=records.map(x=>[x.id,x.number,x.status,x.total,x.currency,x.due_at]);
 }else if(role==='SUPER_ADMIN'&&view==='obligations'){
   const records=await api('/v1/platform/partner-earnings-summary?period='+state.period);
   headers=['QA ONLY','Role','Gross','Reversals','Net','Events'];
   rows=(records.groups||[]).map(x=>['NOT BANK RECONCILED',x.role,x.accrued_gross_kg,x.reversed_kg,x.net_accrued_kg,x.events]);
 }else if(['INVESTOR','SALES_AGENT'].includes(role)&&view==='earnings'){
   const r=await api('/v1/partner/me/earnings?period='+state.period);
   headers=['QA ONLY','Period','Gross','Reversals','Net','Actual paid','Events'];
   rows=[['NOT BANK RECONCILED',r.period,r.accrued_gross_kg,r.reversed_kg,r.net_accrued_kg,r.actual_paid_kg??'',r.events]];
 }else return;
 saveCsv(name,headers,rows);
}
function toolbar(canExport=true){
 return '<div class="toolbar"><button type="button" class="outline" data-refresh="1">↻ '+safe(t('refresh'))+'</button>'+
 (canExport?'<button type="button" class="outline" data-export="1">⇩ '+safe(t('export'))+'</button>':'')+'</div>';
}
function registrationForm(){
 if(state.me?.role!=='SUPER_ADMIN')return heading(t('accessDenied'));
 if(!state.status?.qa_onboarding_enabled)return heading(t('createHotel'))+info(t('notEnabled'))+'<button class="outline" data-view="hotels">'+safe(t('back'))+'</button>';
 return heading(t('createHotel'),t('qaScope'))+info(t('onlyQa'))+
 '<section class="panel gold"><form id="hotel-registration">'+
 '<label for="registration-name">'+safe(t('name'))+'</label><br><input autocomplete="off" id="registration-name" name="display_name" maxlength="180" minlength="2" required placeholder="QA HOTEL 01"><br><br>'+
 '<div class="formbar"><button class="primary" type="submit">'+safe(t('registerHotel'))+'</button><button class="outline" type="button" data-view="hotels">'+safe(t('cancel'))+'</button></div>'+
 '<div id="registration-result" role="status" aria-live="polite"></div></form></section>';
}
async function submitRegistration(form){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_onboarding_enabled)return;
 const name=form.querySelector('[name="display_name"]').value.trim();
 if(name.length<2||name.length>180)return;
 const button=form.querySelector('[type="submit"]');button.disabled=true;button.textContent=t('saving');
 const output=document.getElementById('registration-result');
 try{
   const tokenReply=await fetch('/api/session',{cache:'no-store'});
   if(!tokenReply.ok)throw Error('Session expired. Please sign in again.');
   const session=await tokenReply.json();
   if(!session.csrf)throw Error('CSRF session missing; sign in again.');
   if(name!==state.registerName){state.registerName=name;state.registerKey=crypto.randomUUID();}
   const r=await fetch('/api/actions/hotels',{method:'POST',credentials:'same-origin',cache:'no-store',
     headers:{'Content-Type':'application/json','X-Flex-CSRF':session.csrf,'Idempotency-Key':state.registerKey},
     body:JSON.stringify({display_name:name,currency:'KGS'})});
   const data=await r.json();
   if(!r.ok)throw Error(data.detail||data.error||('HTTP '+r.status));
   state.lastCreated=data.hotel_id;
   state.registerName=null;state.registerKey=null;
   output.innerHTML=info(t('created')+': '+data.hotel_id+' — PENDING','info');
   form.reset();
 }catch(e){output.innerHTML=info(t('hotelError')+': '+e.message,'error')}
 finally{button.disabled=false;button.textContent=t('registerHotel')}
}

async function postQaLink(path,payload) {
 const sessionResponse=await fetch('/api/session',{cache:'no-store',credentials:'same-origin'});
 if(!sessionResponse.ok)throw Error('Session expired; please sign in again.');
 const session=await sessionResponse.json();
 if(!session.csrf)throw Error('Missing CSRF session');
 const res=await fetch('/api/actions/'+path,{method:'POST',cache:'no-store',credentials:'same-origin',
   headers:{'Content-Type':'application/json','X-Flex-CSRF':session.csrf},
   body:JSON.stringify(payload)});
 const data=await res.json();
 if(!res.ok)throw Error(data.code||data.error||('HTTP '+res.status));
 return data;
}
function linkWizard(){
 if(state.me?.role!=='SUPER_ADMIN')return heading(t('accessDenied'))+info(t('accessDenied'),'error');
 const id=state.hotelId;
 if(!/^[0-9a-fA-F-]{36}$/.test(id||''))return heading(t('noSelected'))+empty(t('noSelected'));
 if(!state.status?.qa_linking_enabled)return heading(t('linkTitle'))+info(t('linkDisabled'))+
   '<button class="outline" type="button" data-view="hotel">'+safe(t('openBack'))+'</button>';
 let html=heading(t('linkTitle'),id)+
   '<button class="subtle" type="button" data-view="hotel">← '+safe(t('openBack'))+'</button>'+info(t('linkHelp'),'info');
 if(state.linkSuccess)return html+info(t('linked'),'info');
 if(!state.linkChallenge) {
   html+='<section class="panel gold"><form id="link-challenge-form">'+
    '<label for="deployment-id">'+safe(t('deployment'))+'</label><input id="deployment-id" name="deployment_id" required maxlength="100" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{3,99}">'+
    '<label for="property-id">'+safe(t('property'))+'</label><input id="property-id" name="property_external_id" required maxlength="180">'+
    '<button class="primary" type="submit">'+safe(t('createChallenge'))+'</button>'+
    '<div id="link-result" role="status" aria-live="polite"></div></form></section>';
 } else {
   const x=state.linkChallenge;
   html+='<section class="panel"><h2>'+safe(t('challenge'))+'</h2>'+
    '<div class="muted">'+safe(t('expiresAt'))+': '+safe(x.expires_at?new Date(x.expires_at).toLocaleString(state.lang==='en'?'en-US':'ru-RU',{timeZone:'Asia/Bishkek',hour12:false}):'—')+'</div>'+
    '<pre class="signed-message" id="message-to-sign">'+safe(x.signed_message)+'</pre>'+
    '<div class="notice info">'+safe(t('challengeResult'))+'</div>'+
    '<form id="link-confirm-form">'+
    '<label for="trusted-signature">'+safe(t('signature'))+'</label>'+
    '<textarea id="trusted-signature" required name="signature_b64" minlength="64" maxlength="256" rows="3" autocomplete="off"></textarea>'+
    '<button class="primary" type="submit">'+safe(t('confirmLink'))+'</button>'+
    '<div id="link-result" role="status" aria-live="polite"></div></form></section>';
 }
 return html;
}
async function handleLinkForm(form,kind){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_linking_enabled)return;
 const button=form.querySelector('[type=submit]');button.disabled=true;
 const output=document.getElementById('link-result');
 try{
  const id=state.hotelId;
  let data;
  if(kind==='challenge') {
   const deployment=form.querySelector('[name=deployment_id]').value.trim();
   const property=form.querySelector('[name=property_external_id]').value.trim();
   if(!/^[A-Za-z0-9][A-Za-z0-9_.-]{3,99}$/.test(deployment)||!property||property.length>180)throw Error('Invalid deployment or property');
   data=await postQaLink('hotels/'+id+'/challenge',{deployment_id:deployment,property_external_id:property});
   state.linkChallenge=data;
  }else{
   if(!state.linkChallenge)throw Error('No active challenge');
   const sig=form.querySelector('[name=signature_b64]').value.trim();
   if(!/^[A-Za-z0-9_\-+/=]{64,256}$/.test(sig))throw Error(t('badSignature'));
   data=await postQaLink('challenges/'+state.linkChallenge.challenge_id+'/confirm',{signature_b64:sig});
   if(data.link_status!=='VERIFIED'||data.subscription_activated!==false)throw Error('Unexpected link state');
   state.linkSuccess=true;
   state.linkChallenge=null;
  }
  await render();
 }catch(e){if(output)output.textContent=t('linkError')+': '+e.message}
 finally{button.disabled=false}
}

async function saveQaCatalogAction(path, body) {
 const tokenReply=await fetch('/api/session',{credentials:'same-origin',cache:'no-store'});
 if(!tokenReply.ok)throw Error('QA session expired');
 const session=await tokenReply.json();
 if(!session.csrf)throw Error('CSRF verification unavailable');
 const r=await fetch('/api/actions/'+path,{method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json','X-Flex-CSRF':session.csrf},body:JSON.stringify(body)});
 const data=await r.json();
 if(!r.ok)throw Error(data.detail||data.error||'Request rejected');
 return data;
}
function adminCatalogButtons(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)return '';
 return '<div class="toolbar"><button type="button" class="primary" data-view="catalog-new">+ '+safe(t('createSku'))+'</button></div>';
}
function skuForm(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)
   return heading(t('createSku'))+info(t('operationBlocked'));
 return heading(t('createSku'),t('notPublished'))+
 '<section class="panel gold"><form id="catalog-sku-form" class="admin-form">'+
 '<label>'+safe(t('sku'))+'<input name="sku" required maxlength="80" placeholder="EXTRA_FEATURE"></label>'+
 '<label>'+safe(t('skuTitle'))+'<input name="title" required maxlength="160" placeholder="Extended analytics"></label>'+
 '<label>'+safe(t('capability'))+'<input name="capability_key" required maxlength="120" placeholder="analytics.extra"></label>'+
 '<div class="formbar"><button class="primary" type="submit">'+safe(t('savePlanned'))+'</button><button class="outline" data-view="catalog" type="button">'+safe(t('cancel'))+'</button></div>'+
 '<div id="admin-action-status" role="status" aria-live="polite"></div></form></section>';
}
function futurePriceForm(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)
   return heading(t('newPrice'))+info(t('operationBlocked'));
 const sku=state.priceSku;
 if(!sku||!/^[A-Z][A-Z0-9_]{1,79}$/.test(sku))return heading(t('newPrice'))+empty(t('noSelected'));
 const future=new Date(Date.now()+3*86400000);
 const localDatetime=(new Date(future.getTime()-future.getTimezoneOffset()*60000)).toISOString().slice(0,16);
 return heading(t('newPrice'),sku)+info(t('onlyFuture'),'info')+
 '<section class="panel gold"><form id="catalog-price-form" class="admin-form">'+
 '<label>'+safe(t('yearPrice'))+'<input required name="monthly_price" inputmode="decimal" pattern="(?:0|[1-9][0-9]{0,11})(?:[.][0-9]{1,2})?" placeholder="10000.00"></label>'+
 '<label>'+safe(t('startPrice'))+'<input name="valid_from" required type="datetime-local" value="'+safe(localDatetime)+'"></label>'+
 '<div class="formbar"><button class="primary" type="submit">'+safe(t('savePrice'))+'</button><button type="button" class="outline" data-view="catalog">'+safe(t('cancel'))+'</button></div>'+
 '<div id="admin-action-status" role="status" aria-live="polite"></div></form></section>';
}
async function versionsPage(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)
   return heading(t('priceHistory'))+info(t('operationBlocked'));
 const sku=state.priceSku;
 if(!sku||!/^[A-Z][A-Z0-9_]{1,79}$/.test(sku))return heading(t('priceHistory'))+empty(t('noSelected'));
 const r=await api('/v1/platform/catalog/skus/'+sku+'/versions');
 return heading(t('priceHistory'),sku)+toolbar(false)+'<button type="button" data-view="catalog" class="subtle">← '+safe(t('openBack'))+'</button>'+
 '<div class="panel">'+(r.versions?.length?table([t('skuVersion'),t('yearPrice'),t('startPrice'),t('expires')],
 r.versions.map(v=>'<tr><td>'+safe(v.version)+'</td><td>'+money(v.monthly_price,v.currency)+'</td><td>'+safe(v.valid_from)+'</td><td>'+safe(v.valid_to||'—')+'</td></tr>')):empty(t('noData')))+'</div>';
}
function dateValue(offsetDays){
 const now=new Date(Date.now()+offsetDays*86400000);
 return now.toISOString().slice(0,10);
}
async function subscriptionDraftForm(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)
   return heading(t('configurationDraft'))+info(t('operationBlocked'));
 const hotel=state.hotelId;
 if(!hotel)return heading(t('configurationDraft'))+empty(t('noSelected'));
 const skuRows=await api('/v1/platform/catalog');
 const allowed=skuRows.filter(r=>r.status==='AVAILABLE'&&!r.is_core&&r.latest_price);
 if(!allowed.length)return heading(t('configurationDraft'))+info(t('noSelectable'))+
   '<button type="button" class="outline" data-view="hotel">'+safe(t('cancel'))+'</button>';
 const checkboxes=allowed.map(r=>'<label class="check-row"><input type="checkbox" name="skus" value="'+safe(r.sku)+'"><span>'+safe(r.name)+' — '+safe(r.sku)+'</span></label>').join('');
 return heading(t('configurationDraft'),hotel)+info(t('draftOnly'),'info')+
 '<section class="panel gold"><form id="subscription-draft-form" class="admin-form">'+
 '<label>'+safe(t('draftTitle'))+'<input name="title" required maxlength="120" placeholder="QA standard configuration"></label>'+
 '<label>'+safe(t('periodStart'))+'<input type="date" name="period_start" required value="'+safe(dateValue(2))+'"></label>'+
 '<label>'+safe(t('periodEnd'))+'<input type="date" name="period_end" required value="'+safe(dateValue(32))+'"></label>'+
 '<fieldset><legend>'+safe(t('selectFunctions'))+'</legend>'+checkboxes+'</fieldset>'+
 '<div class="formbar"><button class="primary" type="submit">'+safe(t('saveDraft'))+'</button>'+
 '<button class="outline" type="button" data-view="hotel">'+safe(t('cancel'))+'</button></div>'+
 '<div id="admin-action-status" role="status" aria-live="polite"></div></form></section>';
}
async function submitAdminForm(form,kind){
 const button=form.querySelector('[type=submit]');button.disabled=true;
 const result=document.getElementById('admin-action-status');
 try {
  let data;
  if(kind==='sku'){
   data=await saveQaCatalogAction('catalog/skus',{
     sku:form.elements.sku.value.trim(),title:form.elements.title.value.trim(),
     capability_key:form.elements.capability_key.value.trim()});
   if(data.status!=='PLANNED')throw Error('Unexpected catalog state');
  } else if(kind==='price'){
   const dt=new Date(form.elements.valid_from.value);
   if(!Number.isFinite(dt.getTime()))throw Error('Invalid date');
   data=await saveQaCatalogAction('catalog/skus/'+state.priceSku+'/prices',{
     monthly_price:form.elements.monthly_price.value.trim(),currency:'KGS',
     valid_from:dt.toISOString()});
   if(data.entitlement_changed!==false)throw Error('Unexpected entitlement state');
  }else if(kind==='draft'){
   const checked=[...form.querySelectorAll('input[name=skus]:checked')].map(x=>x.value);
   if(!checked.length)throw Error(t('noSelectable'));
   data=await saveQaCatalogAction('subscription-drafts',{
     hotel_id:state.hotelId,title:form.elements.title.value.trim(),
     period_start:form.elements.period_start.value,period_end:form.elements.period_end.value,
     skus:checked});
   if(data.state!=='DRAFT'||data.subscription_activated!==false)throw Error('Unexpected configuration state');
  }
  result.innerHTML=info(t(kind==='sku'?'notPublished':kind==='price'?'priceChanged':'draftCreated'),'info');
  button.disabled=true;form.reset();
 } catch(e){result.textContent=t('adminError')+': '+e.message;button.disabled=false}
}

function billingHold(){
 return heading('BILLING',t('billingHold'))+info(t('billingHold'),'info');
}
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
 if(state.status?.identity_ready) {
   main.innerHTML=heading(identityText('heading'))+identityPanel()+
     info(safe(configured?t('loginPrompt'):t('configHelp')),'info');
   return;
 }
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
 const filtered=hotels.filter(h=>h.name?.toLocaleLowerCase().includes(state.search.toLocaleLowerCase())&&(!state.hotelStatus||h.status===state.hotelStatus));
 const statuses=[...new Set(hotels.map(h=>h.status))].sort();
 const searchbar='<div class="formbar"><div class="formbar"><input id="hotel-search" type="search" placeholder="'+safe(t('search'))+'" value="'+safe(state.search)+'"><select id="hotel-status"><option value="">'+safe(t('allStatuses'))+'</option>'+
 statuses.map(s=>'<option value="'+safe(s)+'" '+(state.hotelStatus===s?'selected':'')+'>'+safe(s)+'</option>').join('')+'</select></div><span class="role-mark">'+safe(filtered.length)+' / '+safe(hotels.length)+'</span></div>';
 const create=state.status?.qa_onboarding_enabled?'<button class="primary" type="button" data-view="hotel-new">+ '+safe(t('addHotel'))+'</button>':
 '<button class="outline" type="button" disabled title="'+safe(t('notEnabled'))+'">+ '+safe(t('addHotel'))+'</button>';
 return heading(t('hotelList'),t('helpQa'))+'<div class="formbar">'+create+toolbar()+'</div>'+searchbar+
 (state.lastCreated?info(t('created')+': '+state.lastCreated,'info'):'')+
 '<section class="panel">'+(filtered.length?hotelTable(filtered):empty(t('noHotels')))+'</section>';
}
async function hotelDetail(){
 const id=state.hotelId;
 if(!/^[0-9a-fA-F-]{36}$/.test(id||'')) return heading(t('noSelected'))+empty(t('noSelected'));
 const [sub,inv]=await Promise.allSettled([api('/v1/hotels/'+id+'/subscription'),api('/v1/hotels/'+id+'/invoices')]);
 const subscription=sub.status==='fulfilled'?sub.value:null;
 const invoices=inv.status==='fulfilled'?inv.value:null;
 if(sub.status==='rejected'&&sub.reason.status===403)throw sub.reason;
 if(inv.status==='rejected'&&inv.reason.status===403)throw inv.reason;
 let draftHistory='';
 if(state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled){
  try {
   const drafts=await api('/v1/platform/subscription-drafts?hotel_id='+id);
   draftHistory='<section class="panel"><h2>'+safe(t('draftList'))+'</h2>'+
   (drafts.length?table([t('skuVersion'),t('draftTitle'),t('period'),t('status'),t('monthlyEstimate')],
   drafts.map(d=>'<tr><td>v'+safe(d.version)+'</td><td>'+safe(d.title)+'</td>'+
   '<td>'+safe(d.period_start)+' — '+safe(d.period_end)+'</td><td><span class="chip">'+safe(d.state)+' · OFF</span></td>'+
   '<td>'+money(d.proposed_monthly_total,d.currency)+'</td></tr>')):empty(t('noDrafts')))+
   '</section>'+info(t('draftOnly'),'info');
  } catch(e){ draftHistory=info(t('error')+': '+e.message,'error'); }
 }
 return heading(t('selected'),id)+toolbar()+ (state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled?'<button type="button" class="outline" data-view="subscription-draft">'+safe(t('configure'))+'</button>':'')+ (state.me?.role==='SUPER_ADMIN'?'<button type="button" class="outline" data-link="'+safe(id)+'">'+safe(t('linkHotel'))+'</button>':'')+'<button type="button" class="subtle" data-view="'+(state.me?.role==='SUPER_ADMIN'?'hotels':'subscription')+'">← '+safe(t('openBack'))+'</button>'+
 '<div class="grid three spacing-top">'+metric(t('planStatus'),subscription?.status??'—')+metric(t('enforcement'),subscription?.enforcement??'—')+metric(t('expires'),date(subscription?.period_end))+'</div>'+
 '<section class="panel"><h2>'+safe(t('subscription'))+'</h2>'+(subscription?'<div class="grid three">'+kv(t('periodStart'),date(subscription.period_start))+kv(t('periodEnd'),date(subscription.period_end))+kv(t('grace'),date(subscription.grace_until))+'</div>':empty(t('noSubscription')))+'</section>'+
 '<section class="panel"><h2>'+safe(t('invoices'))+'</h2>'+(invoices?.length?table([t('invoice'),t('status'),t('total'),t('due')],invoices.map(i=>'<tr><td>'+safe(i.number||i.id)+'</td><td><span class="chip">'+safe(i.status)+'</span></td><td>'+money(i.total,i.currency)+'</td><td>'+safe(date(i.due_at))+'</td></tr>')):empty(t('noInvoices')))+'</section>'+draftHistory+info(t('warning'),'info');
}
async function catalog(){
 if(state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled){
  const items=await api('/v1/platform/catalog');
  state.catalogItems=items;
  return heading(t('adminCatalog'),t('helpQa'))+toolbar()+adminCatalogButtons()+
    '<div class="grid three">'+metric(t('activeSku'),items.length,'cyan-text')+
    metric(t('currency'),'KGS')+metric(t('readOnly'),'QA')+'</div>'+
    '<section class="panel">'+(items.length?table([t('sku'),t('skuTitle'),t('status'),t('price'),t('actions')],
      items.map(i=>'<tr><td>'+safe(i.sku)+'</td><td>'+safe(i.name)+'</td>'+
       '<td><span class="chip">'+safe(i.status)+'</span></td>'+
       '<td>'+safe(i.latest_price?money(i.latest_price.monthly_price,i.latest_price.currency):'—')+'</td>'+
       '<td><button type="button" class="subtle" data-sku-price="'+safe(i.sku)+'">'+safe(t('newPrice'))+'</button> / '+
       '<button type="button" class="subtle" data-sku-versions="'+safe(i.sku)+'">'+safe(t('openHistory'))+'</button></td></tr>'
      )):empty(t('noCatalog')))+'</section>'+info(t('notPublished'),'info');
 }
 const items=await api('/v1/catalog');
 return heading(t('features'),t('helpQa'))+toolbar()+'<div class="grid three">'+metric(t('activeSku'),items.length,'cyan-text')+metric(t('currency'),'KGS')+metric(t('readOnly'),'ON')+'</div>'+
 '<section class="panel">'+(items.length?table([t('sku'),t('features'),t('price'),t('status')],items.map(i=>'<tr><td>'+safe(i.sku)+'</td><td>'+safe(i.name)+'</td><td>'+money(i.monthly_list_price,i.currency)+'</td><td><span class="chip">v'+safe(i.price_version)+'</span></td></tr>')):empty(t('noCatalog')))+'</section>';
}
function earningsSummary(o){return (o.groups?.length?table([t('groups'),t('gross'),t('refunds'),t('net')],o.groups.map(g=>'<tr><td>'+safe(g.role)+'</td><td>'+money(g.accrued_gross_kg)+'</td><td>'+money(g.reversed_kg)+'</td><td>'+money(g.net_accrued_kg)+'</td></tr>')):empty(t('noPartners')))+info('QA_ONLY_NOT_BANK_RECONCILED','info')}
async function obligations(){const r=await api('/v1/platform/partner-earnings-summary?period='+state.period);return heading(t('obligations'),t('helpQa'))+toolbar()+periodButtons()+'<section class="panel spacing-top">'+earningsSummary(r)+'</section>'+info(t('notImplemented'))}
async function earnings(){
 const r=await api('/v1/partner/me/earnings?period='+state.period);
 return heading(state.me.role==='INVESTOR'?t('investor'):t('agent'),t('helpQa'))+toolbar()+periodButtons()+'<div class="grid spacing-top">'+
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
 try{const views={overview,'billing-hold':billingHold,hotels:hotelList,catalog,'catalog-new':skuForm,'catalog-price':futurePriceForm,'catalog-versions':versionsPage,'subscription-draft':subscriptionDraftForm,obligations,hotel:hotelDetail,'hotel-new':registrationForm,'hotel-link':linkWizard,subscription,earnings};const html=await (views[state.view]||overview)();if(serial!==state.serial)return;main.innerHTML=html;}
 catch(err){if(serial===state.serial)errorPage(err);}
}
async function start(){
 document.documentElement.lang=state.lang==='kg'?'ky':state.lang;
 document.getElementById('lang').value=state.lang;
 document.body.classList.toggle('light',state.theme==='light');
 try {const r=await fetch('/api/status',{cache:'no-store'});state.status=await r.json();}catch{state.status={configured:false};}
 if(state.status.configured){try{state.me=await api('/v1/me');}catch(e){if(e.status!==401)state.error=e;}}
 if(state.status.identity_ready)state.identitySession=await identitySession();
 if(state.me){const role=state.me.role;state.view=role==='SUPER_ADMIN'?'overview':role==='HOTEL_OWNER'?'subscription':role==='BILLING'?'billing-hold':'earnings';}
 render();
}
nav.addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b){state.view=b.dataset.view;state.hotelId=null;state.search='';render();}});
main.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.view){const target=b.dataset.view;if(!['hotel','hotel-link','subscription-draft','subscription'].includes(target))state.hotelId=null;state.view=target;render();}
 if(b.dataset.hotel){state.hotelId=b.dataset.hotel;state.view=state.me.role==='SUPER_ADMIN'?'hotel':'subscription';state.linkChallenge=null;state.linkSuccess=false;render();}
 if(b.dataset.link){state.hotelId=b.dataset.link;state.view='hotel-link';state.linkChallenge=null;state.linkSuccess=false;render();}
 if(b.dataset.period){state.period=b.dataset.period;render();}
 if(b.dataset.skuPrice){state.priceSku=b.dataset.skuPrice;state.view='catalog-price';render();}
 if(b.dataset.skuVersions){state.priceSku=b.dataset.skuVersions;state.view='catalog-versions';render();}
 if(b.dataset.retry)render();
 if(b.dataset.refresh)render();
 if(b.dataset.export){b.disabled=true;exportVisible().catch(err=>{main.insertAdjacentHTML('afterbegin',info(t('error')+': '+err.message,'error'))}).finally(()=>{b.disabled=false})}
 if(b.dataset.login)location.assign('/api/auth/login');
 if(b.dataset.identityLogout){
   identityRequest('sign-out',{}).then(()=>{
     state.identitySession=null;state.identityStep='email';state.identityError='';render();
   }).catch(()=>{state.identityError=identityText('failed');render()});
 }
});
main.addEventListener('input',e=>{if(e.target.id==='hotel-search'){state.search=e.target.value;const rows=main.querySelectorAll('tbody tr');rows.forEach(tr=>tr.hidden=!tr.querySelector('td')?.textContent.toLocaleLowerCase().includes(state.search.toLocaleLowerCase()));}});
main.addEventListener('change',e=>{if(e.target.id==='hotel-status'){state.hotelStatus=e.target.value;render()}});
main.addEventListener('submit',e=>{
 if(e.target.id==='flex-identity-signin'||e.target.id==='flex-identity-totp'){e.preventDefault();submitIdentityForm(e.target)}
 if(e.target.id==='hotel-registration'){e.preventDefault();submitRegistration(e.target)}
 if(e.target.id==='link-challenge-form'){e.preventDefault();handleLinkForm(e.target,'challenge')}
 if(e.target.id==='link-confirm-form'){e.preventDefault();handleLinkForm(e.target,'confirm')}
 if(e.target.id==='catalog-sku-form'){e.preventDefault();submitAdminForm(e.target,'sku')}
 if(e.target.id==='catalog-price-form'){e.preventDefault();submitAdminForm(e.target,'price')}
 if(e.target.id==='subscription-draft-form'){e.preventDefault();submitAdminForm(e.target,'draft')}
});

document.getElementById('lang').addEventListener('change',e=>{state.lang=e.target.value;localStorage.setItem('flex_lang',state.lang);document.documentElement.lang=state.lang==='kg'?'ky':state.lang;render()});
document.getElementById('theme').addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';localStorage.setItem('flex_theme',state.theme);document.body.classList.toggle('light',state.theme==='light')});
document.getElementById('session-button').addEventListener('click',()=>location.assign(state.me?'/api/auth/logout':'/api/auth/login'));
start();
