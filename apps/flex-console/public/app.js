/* MARINA SMART FLEX · role-bound read-only client. No browser access tokens. */
'use strict';
const translations = {
 ru:{frozen:'Заморожено',commercial:'КОММЕРЧЕСКАЯ ПЛАТФОРМА',warning:'Нет реальных платежей и выплат. Доступ к гостиничной PMS не изменяется.',lang:'Язык',login:'Войти',logout:'Выйти',welcome:'Центр управления',overview:'Обзор',hotels:'Гостиницы',catalog:'Каталог функций',obligations:'Начисления партнёрам',subscription:'Моя подписка',earnings:'Мои начисления',notConfigured:'Отдельная QA-среда ещё не подключена',configHelp:'Для настоящих данных нужен отдельный FLEX API и платформенный OIDC/MFA. Пока здесь не показываются вымышленные финансы.',loginPrompt:'Для просмотра данных войдите через защищённый платформенный доступ.',hotelList:'Реестр гостиниц',search:'Поиск по названию',hotel:'Гостиница',status:'Статус',currency:'Валюта',actions:'Действия',open:'Открыть',noHotels:'Гостиницы ещё не зарегистрированы.',back:'Все гостиницы',invoices:'Счета',invoice:'Номер счёта',total:'Сумма',due:'Срок',noInvoices:'Счетов нет',noSubscription:'Активная подписка отсутствует.',planStatus:'Подписка',enforcement:'Режим контроля',periodStart:'Начало периода',periodEnd:'Конец периода',grace:'Льготный период',features:'Опубликованные функции',sku:'Код SKU',price:'Цена в месяц',noCatalog:'Опубликованных функций пока нет',accessDenied:'Нет доступа к этим данным',error:'Не удалось получить данные',retry:'Повторить',agent:'Агент продаж',investor:'Инвестор',net:'Начислено с учётом возвратов',gross:'Начислено',refunds:'Сторнировано',paid:'Фактически выплачено',events:'Операций',notImplemented:'Подтверждённые выплаты пока не подключены.',periodDay:'День',periodWeek:'Неделя',periodMonth:'Месяц',role:'Роль',billingHold:'Роль BILLING: управление платежами отключено до отдельного решения.',readOnly:'Только чтение',noData:'Данных за период нет',activeHotels:'Гостиниц в реестре',activeSku:'Опубликованных функций',groups:'Категория',sum:'Начисления',helpQa:'Все значения поступают исключительно из FLEX QA API, не из PMS и не из макетов.',ownerHotels:'Ваши отели',selected:'Карточка гостиницы',openBack:'Вернуться',noSelected:'Нет закреплённых гостиниц',go:'Перейти',period:'Период',expires:'Истекает',count:'Количество',noPartners:'Начислений нет',emptyTitle:'Данных нет',addHotel:'Добавить гостиницу',createHotel:'Создать тестовую гостиницу',registerHotel:'Зарегистрировать в QA',name:'Название гостиницы',cancel:'Отмена',refresh:'Обновить',export:'Экспорт CSV',onlyQa:'Регистрация создаёт только PENDING-запись в отдельном FLEX QA. Она не активирует подписку и не изменяет PMS.',notEnabled:'Создание гостиницы станет доступно после подключения изолированного FLEX QA и MFA.',created:'Гостиница зарегистрирована в QA',saving:'Сохранение...',allStatuses:'Все статусы',registered:'Регистрация',qaScope:'Только синтетические тестовые данные. Не используйте реальные имена, договоры и платежи.',linkHotel:'Связать с MARINA SMART',linkTitle:'Подтверждение связи гостиницы',linkHelp:'Подключение требует доверенной подписи MARINA SMART. Заявка сама не подключает и не активирует гостиницу.',linkDisabled:'Доверенное подключение доступно только в изолированной FLEX QA после настройки подписывающего сервера.',deployment:'ID проверенного развёртывания',property:'ID гостиницы в MARINA SMART',createChallenge:'Запросить проверку связи',challenge:'Подписываемое сообщение',expiresAt:'Действительно до',signature:'Подпись доверенного сервера (Base64)',confirmLink:'Подтвердить подпись',linked:'Связь криптографически подтверждена; подписка НЕ активирована.',challengeResult:'Запрос на подпись создан. Передайте сообщение доверенному серверу MARINA SMART.',linkError:'Проверка связи отклонена',badSignature:'Нужна подпись от доверенного сервера, нельзя вводить произвольную строку.',hotelError:'Регистрация отклонена сервером',searchHelp:'Фильтр по названию и статусу',adminCatalog:'Управление каталогом',createSku:'Добавить функцию (план)',newPrice:'Новая версия цены',priceHistory:'История цен',skuTitle:'Название функции',capability:'Серверная возможность',startPrice:'Дата начала действия цены',savePlanned:'Создать PLANNED SKU',savePrice:'Сохранить будущую цену',skuVersion:'Версия',sourceStatus:'Каталог',configure:'Черновик подписки',configurationDraft:'Новый черновик подписки',draftList:'История черновиков',draftTitle:'Название пакета',selectFunctions:'Функции для предложения',saveDraft:'Сохранить черновик',draftOnly:'Это коммерческий черновик без оплаты, активации подписки и изменения доступа. Не создаёт договор или счёт.',notPublished:'Созданная функция имеет статус PLANNED; нельзя считать её доступной гостиницам до отдельной публикации.',priceChanged:'Новая версия цены записана; прежняя история сохранена.',draftCreated:'Черновик сохранён. Доступ не изменён.',noDrafts:'Черновиков пока нет',noSelectable:'Сначала необходимо наличие утверждённых доступных SKU с ценами на дату начала.',draftSettings:'Параметры подписки',yearPrice:'Цена в KGS за месяц',operationBlocked:'Администрирование каталога доступно только в отдельной FLEX QA после настройки MFA.',adminError:'Сервер отклонил операцию',openHistory:'История',monthlyEstimate:'Предварительная стоимость за месяц',draftDatesError:'Проверьте даты черновика: начало не раньше вчерашнего дня и не дальше года; окончание не раньше начала и не более чем через 366 дней.',hotelTabOverview:'Обзор',hotelTabFinance:'Финансы',hotelTabUsage:'Использование',hotelTabRelations:'Агенты и партнёры',hotelTabHistory:'История',hotelTabPending:'Источник данных ещё не подключён к FLEX QA. Здесь нет вымышленных показателей.',draftEstimate:'Предварительная сумма за месяц (KGS)',draftEstimateDisclaimer:'Предварительная сумма по доступным ценам на дату начала. Не счёт, не договор и не подтверждённая выручка.',draftPriceUnavailable:'Для выбранной даты нет подтверждённой цены. Измените дату или состав модулей.',draftSelectModules:'Выберите дополнительные модули.',packageType:'Тип тарифного предложения',packageCustom:'Индивидуальный',sharedTemplate:'Общий шаблон модулей',manualSelection:'Выбрать модули вручную',publishTemplate:'Сохранить состав как общий шаблон',templateSaved:'Шаблон сохранён',packageNote:'BASE, BUSINESS и PREMIUM — названия предложений. Состав, цены и подключение модулей не назначаются автоматически.',packageLabel:'Название предложения',packageTitleRequired:'Укажите название предложения.',packageDiscount:'Скидка (%)',packageTrial:'Пробный период (дней)',packageCustomPrice:'Индивидуальная цена за месяц (сом)',packageSave:'Сохранить версию тарифа',packageSaved:'Версия тарифного предложения сохранена. Подписка не активирована.',packageHistory:'История версий тарифов',packagePriceOverride:'Индивидуальная цена допустима только в CUSTOM без процентной скидки.',onlyFuture:'Стоимость вступит в силу только с указанной будущей даты.'},
 kg:{frozen:'Токтотулган',commercial:'КОММЕРЦИЯЛЫК ПЛАТФОРМА',warning:'Чыныгы төлөмдөр жана которуулар жок. Мейманкананын PMS тутуму өзгөрбөйт.',lang:'Тил',login:'Кирүү',logout:'Чыгуу',welcome:'Башкаруу борбору',overview:'Жалпы көрүнүш',hotels:'Мейманканалар',catalog:'Функциялар каталогу',obligations:'Өнөктөштөрдүн эсептөөлөрү',subscription:'Менин жазылуум',earnings:'Менин эсептөөлөрүм',notConfigured:'Өзүнчө QA чөйрөсү туташа элек',configHelp:'Чыныгы маалымат үчүн FLEX API жана OIDC/MFA керек. Бул жерде ойдон чыгарылган каржы маалыматтары жок.',loginPrompt:'Маалымат көрүү үчүн коопсуз каттоо аркылуу кириңиз.',hotelList:'Мейманканалар тизмеси',search:'Аты боюнча издөө',hotel:'Мейманкана',status:'Абалы',currency:'Валюта',actions:'Аракеттер',open:'Ачуу',noHotels:'Азырынча мейманканалар жок.',back:'Бардык мейманканалар',invoices:'Эсеп-фактуралар',invoice:'Эсеп номери',total:'Сумма',due:'Мөөнөт',noInvoices:'Эсептер жок',noSubscription:'Активдүү жазылуу жок.',planStatus:'Жазылуу',enforcement:'Көзөмөл режими',periodStart:'Мөөнөттүн башы',periodEnd:'Мөөнөттүн аягы',grace:'Жеңилдетилген мөөнөт',features:'Жарыяланган функциялар',sku:'SKU коду',price:'Айлык баа',noCatalog:'Азырынча функциялар жок',accessDenied:'Уруксат жок',error:'Маалымат алынбады',retry:'Кайра аракеттенүү',agent:'Сатуу агенти',investor:'Инвестор',net:'Кайтарууларды эске алган эсептөө',gross:'Эсептелди',refunds:'Жокко чыгарылды',paid:'Иш жүзүндө төлөндү',events:'Операциялар',notImplemented:'Ырасталган төлөмдөр туташа элек.',periodDay:'Күн',periodWeek:'Жума',periodMonth:'Ай',role:'Роль',billingHold:'BILLING ролу: төлөмдөрдү башкаруу өзүнчө чечимге чейин өчүрүлгөн.',readOnly:'Окуу гана',noData:'Бул мезгилге маалымат жок',activeHotels:'Мейманканалар',activeSku:'Жарыяланган функциялар',groups:'Топ',sum:'Эсептөөлөр',helpQa:'Баардык маалымат FLEX QA API аркылуу алынат.',ownerHotels:'Сиздин мейманканалар',selected:'Мейманкана картасы',openBack:'Артка',noSelected:'Бекитилген мейманкана жок',go:'Өтүү',period:'Мезгил',expires:'Бүтөт',count:'Саны',noPartners:'Эсептөөлөр жок',emptyTitle:'Маалымат жок',addHotel:'Мейманкана кошуу',createHotel:'QA мейманканасын түзүү',registerHotel:'QA каттоо',name:'Мейманкананын аталышы',cancel:'Жокко чыгаруу',refresh:'Жаңыртуу',export:'CSV чыгаруу',onlyQa:'QA ичинде PENDING гана түзүлөт. Жазылууга жана PMSке таасир этпейт.',notEnabled:'Жаңы мейманкана үчүн өзүнчө QA жана MFA керек.',created:'QA мейманкана катталды',saving:'Сакталууда...',allStatuses:'Бардык абалдар',registered:'Каттоо',qaScope:'Синтетикалык тесттик гана маалымат. Чыныгы келишимдерди колдонбоңуз.',linkHotel:'MARINA SMART менен туташтыруу',linkTitle:'Мейманкананы байланыштыруу',linkHelp:'MARINA SMART кол тамгасы керек. Суроо автоматтык кошпойт.',linkDisabled:'QA жана ишенимдүү кол тамга сервери керек.',deployment:'Текшерилген жайгаштыруу ID',property:'MARINA SMART ичиндеги мейманкана ID',createChallenge:'Байланышты текшерүү',challenge:'Кол коюлуучу билдирүү',expiresAt:'Мөөнөтү',signature:'Ишенимдүү сервердин кол тамгасы (Base64)',confirmLink:'Кол тамганы текшерүү',linked:'Байланыш ырасталды, жазылуу иштетилген жок.',challengeResult:'Суроо түзүлдү. Билдирүүнү ишенимдүү MARINA SMART серверине бериңиз.',linkError:'Байланыш четке кагылды',badSignature:'Ишенимдүү сервердин кол тамгасы керек.',hotelError:'Сервер каттоодон баш тартты',searchHelp:'Аты жана абалы боюнча чыпка',adminCatalog:'Каталогду башкаруу',createSku:'Функция кошуу (план)',newPrice:'Жаңы баа версиясы',priceHistory:'Баалардын тарыхы',skuTitle:'Функциянын аты',capability:'Сервер мүмкүнчүлүгү',startPrice:'Баанын башталышы',savePlanned:'PLANNED SKU түзүү',savePrice:'Келечектеги бааны сактоо',skuVersion:'Версия',sourceStatus:'Каталог',configure:'Жазылуунун долбоору',configurationDraft:'Жазылуунун долбоору',draftList:'Долбоорлор тарыхы',draftTitle:'Пакеттин аталышы',selectFunctions:'Сунуш функциялары',saveDraft:'Долбоорду сактоо',draftOnly:'Бул төлөмсүз жана активдешүүсүз коммерциялык долбоор. Келишим же эсеп түзбөйт.',notPublished:'Функция PLANNED абалында, мейманканаларга ачылбайт.',priceChanged:'Жаңы версия сакталды, мурунку баалар өзгөргөн жок.',draftCreated:'Долбоор сакталды, укуктар өзгөргөн жок.',noDrafts:'Долбоор жок',noSelectable:'Алгач жеткиликтүү SKU баалары керек.',draftSettings:'Жазылуу параметрлери',yearPrice:'Айына сом',operationBlocked:'Бул үчүн өзүнчө FLEX QA жана MFA керек.',adminError:'Сервер четке какты',openHistory:'Тарых',monthlyEstimate:'Айлык болжол',draftDatesError:'Долбоордун күндөрүн текшериңиз: башталышы кечээки күндөн эрте эмес, бир жылдан кеч эмес; аягы башталыштан эрте эмес жана 366 күндөн ашпайт.',hotelTabOverview:'Жалпы маалымат',hotelTabFinance:'Каржы',hotelTabUsage:'Колдонуу',hotelTabRelations:'Агенттер жана өнөктөштөр',hotelTabHistory:'Тарых',hotelTabPending:'FLEX QA үчүн маалымат булагы азырынча кошула элек. Бул жерде жасалма көрсөткүчтөр жок.',draftEstimate:'Айына алдын ала сумма (сом)',draftEstimateDisclaimer:'Башталган күнгө карата баалар боюнча болжол. Эсеп, келишим же ырасталган киреше эмес.',draftPriceUnavailable:'Тандалган күнгө ырасталган баа жок. Күндү же модулдарды өзгөртүңүз.',draftSelectModules:'Кошумча модулдарды тандаңыз.',packageType:'Тарифтик сунуштун түрү',packageCustom:'Жеке тариф',sharedTemplate:'Жалпы модулдар шаблону',manualSelection:'Модулдарды кол менен тандоо',publishTemplate:'Курамды жалпы шаблон катары сактоо',templateSaved:'Шаблон сакталды',packageNote:'BASE, BUSINESS жана PREMIUM — сунуштардын аталыштары гана. Модулдар, баалар жана туташтыруу автоматтык дайындалбайт.',packageLabel:'Сунуштун аталышы',packageTitleRequired:'Сунуштун аталышын киргизиңиз.',packageDiscount:'Арзандатуу (%)',packageTrial:'Сыноо мезгили (күн)',packageCustomPrice:'Жеке айлык баа (сом)',packageSave:'Тарифтин версиясын сактоо',packageSaved:'Тарифтик сунуштун версиясы сакталды. Жазылуу иштетилген жок.',packageHistory:'Тарифтердин версияларынын тарыхы',packagePriceOverride:'Жеке баа арзандатуусуз CUSTOM үчүн гана.',onlyFuture:'Баанын күчү көрсөтүлгөн күнү башталат.'},
 en:{frozen:'Frozen',commercial:'COMMERCIAL CONTROL PLANE',warning:'Live payments and payouts are disabled. Hotel PMS data remains untouched.',lang:'Language',login:'Sign in',logout:'Sign out',welcome:'Control center',overview:'Overview',hotels:'Hotels',catalog:'Feature catalog',obligations:'Partner earnings',subscription:'My subscription',earnings:'My earnings',notConfigured:'Isolated QA environment is not configured',configHelp:'Real data requires the dedicated FLEX API and OIDC/MFA. No fictional financial data is displayed.',loginPrompt:'Sign in through the separate platform identity provider to view data.',hotelList:'Hotel registry',search:'Search hotels',hotel:'Hotel',status:'Status',currency:'Currency',actions:'Actions',open:'Open',noHotels:'No hotels registered yet.',back:'All hotels',invoices:'Invoices',invoice:'Invoice number',total:'Amount',due:'Due date',noInvoices:'No invoices',noSubscription:'No active subscription.',planStatus:'Subscription',enforcement:'Enforcement',periodStart:'Period start',periodEnd:'Period end',grace:'Grace period',features:'Published features',sku:'SKU code',price:'Monthly price',noCatalog:'No published features yet',accessDenied:'Access denied',error:'Unable to load data',retry:'Retry',agent:'Sales agent',investor:'Investor',net:'Net earned after reversals',gross:'Gross earned',refunds:'Reversed',paid:'Actually paid out',events:'Entries',notImplemented:'Verified payouts are not yet implemented.',periodDay:'Day',periodWeek:'Week',periodMonth:'Month',role:'Role',billingHold:'BILLING role: payment management remains disabled until separately approved.',readOnly:'Read-only',noData:'No data this period',activeHotels:'Registered hotels',activeSku:'Published features',groups:'Group',sum:'Earnings',helpQa:'Figures come only from FLEX QA APIs—not from PMS or mockups.',ownerHotels:'Your hotels',selected:'Hotel details',openBack:'Back',noSelected:'No assigned hotels',go:'Go',period:'Period',expires:'Expires',count:'Count',noPartners:'No earnings entries',emptyTitle:'No data',addHotel:'Add hotel',createHotel:'Register QA hotel',registerHotel:'Register in QA',name:'Hotel name',cancel:'Cancel',refresh:'Refresh',export:'Export CSV',onlyQa:'Creates a PENDING record in separate FLEX QA only. Does not activate a subscription or modify PMS.',notEnabled:'Hotel onboarding requires isolated FLEX QA and MFA.',created:'Hotel registered in QA',saving:'Saving...',allStatuses:'All statuses',registered:'Registration',qaScope:'Synthetic test data only. Do not use real contracts or payments.',linkHotel:'Link to MARINA SMART',linkTitle:'Verify hotel ownership',linkHelp:'A trusted MARINA SMART deployment signature is required. Creating a challenge never links or activates a subscription.',linkDisabled:'Trusted linking requires isolated FLEX QA and an approved MARINA SMART signer.',deployment:'Trusted deployment ID',property:'Property ID in MARINA SMART',createChallenge:'Request link verification',challenge:'Message to be signed',expiresAt:'Expires',signature:'Trusted deployment signature (Base64)',confirmLink:'Verify signature',linked:'Trusted link verified; subscription remains inactive.',challengeResult:'Verification request created. Hand this message to the trusted MARINA SMART deployment signer.',linkError:'Link verification rejected',badSignature:'The signature must come from a trusted deployment, not a guessed value.',hotelError:'Hotel registration rejected by server',searchHelp:'Filter by name and status',adminCatalog:'Catalog administration',createSku:'Add planned feature',newPrice:'New price version',priceHistory:'Price history',skuTitle:'Feature title',capability:'Server capability',startPrice:'Price effective from',savePlanned:'Create PLANNED SKU',savePrice:'Save future price',skuVersion:'Version',sourceStatus:'Catalog',configure:'Subscription configuration draft',configurationDraft:'New subscription draft',draftList:'Draft version history',draftTitle:'Package title',selectFunctions:'Features to propose',saveDraft:'Save draft',draftOnly:'Commercial proposal only. No payment, subscription activation, entitlement or invoice. Not a signed contract.',notPublished:'New SKU remains PLANNED until separately reviewed and published. It is not available to hotels.',priceChanged:'A new price version was appended; prior history is retained.',draftCreated:'Draft saved. Hotel access remains unchanged.',noDrafts:'No drafts yet',noSelectable:'Approved AVAILABLE SKUs with effective prices are required first.',draftSettings:'Subscription configuration',yearPrice:'Monthly KGS',operationBlocked:'Catalog administration requires isolated FLEX QA and verified admin MFA.',adminError:'Backend rejected the request',openHistory:'History',monthlyEstimate:'Estimated monthly KGS',draftDatesError:'Check draft dates: start no earlier than yesterday and within a year; end no earlier than start and at most 366 days later.',hotelTabOverview:'Overview',hotelTabFinance:'Finances',hotelTabUsage:'Usage',hotelTabRelations:'Agents and partners',hotelTabHistory:'History',hotelTabPending:'This data source is not connected to FLEX QA yet. No figures are fabricated.',draftEstimate:'Estimated monthly total (KGS)',draftEstimateDisclaimer:'Estimate from available prices effective on start date; not an invoice, contract, or received revenue.',draftPriceUnavailable:'No verified effective price for the selected date. Change the date or selected modules.',draftSelectModules:'Select additional modules.',packageType:'Tariff proposal type',packageCustom:'Custom',sharedTemplate:'Shared module template',manualSelection:'Select modules manually',publishTemplate:'Save modules as shared template',templateSaved:'Template saved',packageNote:'BASE, BUSINESS and PREMIUM are proposal labels only. No modules, prices or activation are automatically assigned.',packageLabel:'Proposal title',packageTitleRequired:'Enter a proposal title.',packageDiscount:'Discount (%)',packageTrial:'Trial period (days)',packageCustomPrice:'Custom monthly price (KGS)',packageSave:'Save tariff version',packageSaved:'Tariff proposal version saved. Subscription not activated.',packageHistory:'Tariff version history',packagePriceOverride:'A custom price is permitted only for CUSTOM without a percentage discount.',onlyFuture:'Price becomes effective only on the selected future date.'}
};
const main=document.getElementById('content'), nav=document.getElementById('nav');

/* Separate Better Auth identity sign-in. This never authorizes FLEX API,
 * assigns a role, produces a JWT or marks MFA complete based on browser state.
 */
for(const [locale,copy] of Object.entries({"ru":{"qaDemo":"Тестовая среда","qaReadonly":"Только чтение","footerBrand":"MARINA SMART FLEX · Коммерческое управление","footerFrozen":"Платежи, QR и выплаты отключены","theme":"Переключить тему","loading":"Загрузка","navigation":"Навигация","controlPlane":"Центр коммерческого управления","authRequired":"Требуется вход","noLiveData":"Тестовая среда не подключена"},"kg":{"qaDemo":"Сыноо чөйрөсү","qaReadonly":"Окуу гана","footerBrand":"MARINA SMART FLEX · Коммерциялык башкаруу","footerFrozen":"Төлөмдөр, QR жана которуулар өчүрүлгөн","theme":"Теманы алмаштыруу","loading":"Жүктөлүүдө","navigation":"Навигация","controlPlane":"Коммерциялык башкаруу борбору","authRequired":"Кирүү талап кылынат","noLiveData":"Сыноо чөйрөсү туташкан эмес"},"en":{"qaDemo":"Test environment","qaReadonly":"Read only","footerBrand":"MARINA SMART FLEX · Commercial management","footerFrozen":"Payments, QR and payouts disabled","theme":"Switch theme","loading":"Loading","navigation":"Navigation","controlPlane":"Commercial management center","authRequired":"Sign-in required","noLiveData":"Test environment not connected"}})) Object.assign(translations[locale],copy);
const identityCopy={
 ru:{heading:'Вход в MARINA SMART FLEX',email:'Электронная почта',password:'Пароль',signIn:'Продолжить',mfa:'Код из приложения-аутентификатора',verify:'Подтвердить код',onlyIdentity:'Вход в учётную запись не предоставляет доступ SUPER ADMIN. Права откроются только после проверенного MFA и серверного подтверждения роли.',signedIn:'Почта подтверждена, но доступ к кабинету ещё не выдан сервером. Выйдите и войдите снова, если сессия устарела.',signOut:'Выйти из учётной записи',failed:'Не удалось подтвердить учётную запись',disabled:'Вход ещё не настроен',totpHint:'Введите шесть цифр из приложения-аутентификатора.'},
 kg:{heading:'MARINA SMART FLEX системасына кирүү',email:'Электрондук почта',password:'Сырсөз',signIn:'Улантуу',mfa:'Аутентификатор колдонмосундагы код',verify:'Кодду ырастоо',onlyIdentity:'Каттоо эсебине кирүү SUPER ADMIN укугун бербейт. Укук MFA жана серверде роль текшерилгенден кийин гана берилет.',signedIn:'Каттоо эсебиңиз ырасталды, бирок кабинетке кирүүгө сервер али уруксат берген жок. Сессия эскирсе, чыгып кайра кириңиз.',signOut:'Каттоо эсебинен чыгуу',failed:'Каттоо эсеби ырасталган жок',disabled:'Кирүү али жөндөлө элек',totpHint:'Аутентификатор колдонмосундагы алты орундуу кодду киргизиңиз.'},
 en:{heading:'Sign in to MARINA SMART FLEX',email:'Email',password:'Password',signIn:'Continue',mfa:'Authenticator code',verify:'Verify code',onlyIdentity:'Signing in does not grant SUPER ADMIN access. Commercial permissions require verified MFA and a server-authorized role.',signedIn:'Identity verified, but the server has not granted dashboard access. Sign out and sign in again if the session is stale.',signOut:'Sign out of identity',failed:'Unable to verify identity',disabled:'Identity sign-in is not configured yet',totpHint:'Enter the six-digit code from your authenticator app.'}
};
const recoveryCopy={"ru":{"forgot":"Забыли пароль?","resetTitle":"Восстановление пароля","send":"Отправить ссылку","sent":"Если аккаунт существует, письмо с инструкцией будет отправлено.","back":"Вернуться ко входу","newPassword":"Новый пароль","confirm":"Повторите пароль","save":"Сохранить пароль","done":"Пароль изменён. Войдите снова.","mismatch":"Пароли не совпадают.","error":"Не удалось выполнить операцию. Повторите попытку или обратитесь в поддержку."},"kg":{"forgot":"Сырсөздү унуттуңузбу?","resetTitle":"Сырсөздү калыбына келтирүү","send":"Шилтемени жөнөтүү","sent":"Каттоо эсеби бар болсо, нускама электрондук почтага жөнөтүлөт.","back":"Кирүү бетине кайтуу","newPassword":"Жаңы сырсөз","confirm":"Сырсөздү кайталаңыз","save":"Сырсөздү сактоо","done":"Сырсөз өзгөртүлдү. Кайра кириңиз.","mismatch":"Сырсөздөр дал келбейт.","error":"Аракет аткарылган жок. Кайра аракет кылыңыз же колдоо кызматына кайрылыңыз."},"en":{"forgot":"Forgot password?","resetTitle":"Reset password","send":"Send reset link","sent":"If the account exists, recovery instructions will be sent.","back":"Back to sign in","newPassword":"New password","confirm":"Confirm password","save":"Save password","done":"Password changed. Please sign in again.","mismatch":"Passwords do not match.","error":"Unable to complete the request. Try again or contact support."}};
const recoveryText=k=>(recoveryCopy[state.lang]||recoveryCopy.ru)[k];
let recoveryToken=new URLSearchParams(location.hash.slice(1)).get('reset');
if(recoveryToken)history.replaceState(null,'',location.pathname+location.search);
function recoveryPanel(){
 const t=recoveryText;
 const resetting=state.identityStep==='reset';
 const field=(name,label,type,attrs='')=>'<label>'+safe(label)+'<input name="'+name+'" type="'+type+'" '+attrs+' required></label>';
 return '<section class="panel gold identity-card"><h2>'+safe(t('resetTitle'))+'</h2><form id="flex-recovery-form">'+(resetting?field('password',t('newPassword'),'password','minlength="12" maxlength="128" autocomplete="new-password"')+field('confirm',t('confirm'),'password','minlength="12" maxlength="128" autocomplete="new-password"'):field('email',identityText('email'),'email','maxlength="254" autocomplete="email"'))+'<button class="primary" type="submit">'+safe(t(resetting?'save':'send'))+'</button></form>'+(state.recoveryMessage?'<p role="status">'+safe(t(state.recoveryMessage))+'</p>':'')+'<button class="subtle" type="button" data-recovery-back="1">'+safe(t('back'))+'</button></section>';
}
async function submitRecovery(form){
 const btn=form.querySelector('button[type=submit]');btn.disabled=true;
 try{
  if(state.identityStep==='reset'){
   if(form.elements.password.value!==form.elements.confirm.value){state.recoveryMessage='mismatch';render();return;}
   await identityRequest('reset-password',{token:recoveryToken,newPassword:form.elements.password.value});
   recoveryToken=null;state.identityStep='email';state.recoveryMessage='done';
  }else{await identityRequest('request-password-reset',{email:form.elements.email.value.trim(),redirectTo:location.origin+'/'});state.recoveryMessage='sent';}
 }catch{state.recoveryMessage='error';}finally{btn.disabled=false;render();}
}
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
     if(data.platform_session){location.replace('/');return;}
     state.identityStep=data.twoFactorRedirect===true?'totp':'session';
   }else if(form.id==='flex-identity-totp'){
     const code=String(form.elements.code.value||'').trim();
     if(!/^\d{6}$/.test(code))throw Error('INVALID_TOTP_CODE');
     const result=await identityRequest('two-factor/verify-totp',{code,trustDevice:false});
     if(result.platform_session===true){location.replace('/');return;}
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
 if(state.identityStep==='forgot'||state.identityStep==='reset')return recoveryPanel();
 const text=identityText;
 const note=state.status?.password_login?'':'<p class="muted">'+safe(text('onlyIdentity'))+'</p>';
 // A verified identity cookie is not a platform session. Never show another
 // password form over an existing identity session: offer a safe sign-out.
 if(state.identitySession?.user)return '<section class="panel gold identity-card"><h2>'+safe(text('heading'))+'</h2>'+
   '<p>'+safe(text('signedIn'))+'</p>'+note+
   '<button type="button" class="outline" data-identity-logout="yes">'+safe(text('signOut'))+'</button></section>';
 if(state.identityStep==='totp')return '<section class="panel gold identity-card"><h2>'+safe(text('mfa'))+'</h2>'+
   '<p class="muted">'+safe(text('totpHint'))+'</p><form id="flex-identity-totp">'+
   '<label>'+safe(text('mfa'))+'<input name="code" type="text" inputmode="numeric" pattern="[0-9]{6}" minlength="6" maxlength="6" autocomplete="one-time-code" required></label>'+
   '<button class="primary" type="submit">'+safe(text('verify'))+'</button></form>'+
   (state.identityError?'<p role="alert">'+safe(state.identityError)+'</p>':'')+note+'</section>';
 return '<section class="panel gold identity-card"><h2>'+safe(text('heading'))+'</h2><form id="flex-identity-signin">'+
   '<label>'+safe(text('email'))+'<input name="email" type="email" autocomplete="username" required maxlength="254"></label>'+
   '<label>'+safe(text('password'))+'<input name="password" type="password" autocomplete="current-password" required minlength="12"></label>'+
   '<button class="primary" type="submit">'+safe(text('signIn'))+'</button></form><button class="subtle" type="button" data-recovery-open="1">'+safe(recoveryText('forgot'))+'</button>'+(state.recoveryMessage?'<p role="status">'+safe(recoveryText(state.recoveryMessage))+'</p>':'')+
   (state.identityError?'<p role="alert">'+safe(state.identityError)+'</p>':'')+note+'</section>';
}

const state={lang:localStorage.getItem('flex_lang')||'ru',theme:localStorage.getItem('flex_theme')||'dark',view:'overview',period:'month',me:null,status:null,hotelId:null,search:'',serial:0,hotelStatus:'',lastCreated:null,registerKey:null,registerName:null,linkChallenge:null,linkSuccess:false,catalogItems:[],priceSku:null,identityStep:recoveryToken?'reset':'email',recoveryMessage:'',identityError:'',identitySession:null,hotelTab:'overview',draftPriceRows:[]};
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
 const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{
   timeZone:'Asia/Bishkek',year:'numeric',month:'2-digit',day:'2-digit'
 }).formatToParts(now).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return parts.year+'-'+parts.month+'-'+parts.day;
}
// Matches date-only limits of the isolated FLEX API. Server checks remain mandatory.
function validDraftPeriod(start,end,today=dateValue(0)){
 const parse=v=>{
   if(!/^\d{4}-\d{2}-\d{2}$/.test(v||''))return NaN;
   const d=Date.parse(v+'T00:00:00Z');
   return Number.isFinite(d)&&new Date(d).toISOString().slice(0,10)===v?d:NaN;
 };
 const a=parse(start),b=parse(end),now=parse(today),day=86400000;
 return Number.isFinite(a)&&Number.isFinite(b)&&Number.isFinite(now)&&
   a>=now-day&&a<=now+366*day&&b>=a&&b-a<=366*day;
}
// Browser price estimate only; the server snapshots the approved amount.
// A newer scheduled version does not prove what was effective on an earlier day.
function draftEstimate(rows,selected,start){
 if(!selected.length||!/^\d{4}-\d{2}-\d{2}$/.test(start||''))return null;
 const effective=Date.parse(start+'T00:00:00+06:00');
 if(!Number.isFinite(effective))return null;
 let cents=0n;
 for(const sku of selected){
  const item=rows.find(row=>row.sku===sku && row.status==='AVAILABLE' && !row.is_core);
  const price=item?.latest_price;
  if(!price||price.currency!=='KGS')return null;
  const from=Date.parse(price.valid_from),to=price.valid_to?Date.parse(price.valid_to):Infinity;
  if(!Number.isFinite(from)||!(effective>=from&&effective<to))return null;
  const amount=String(price.monthly_price);
  if(!/^(?:0|[1-9]\d{0,11})(?:\.\d{1,2})?$/.test(amount))return null;
  const [whole,fraction='']=amount.split('.');
  cents+=BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'));
 }
 return (cents/100n).toString()+'.'+(cents%100n).toString().padStart(2,'0');
}
function refreshDraftEstimate(form){
 const output=form.querySelector('#draft-estimate');
 const button=form.querySelector('button[type=submit]');
 const packageButton=form.querySelector('[data-package-save]');
 if(!output||!button)return;
 const checked=[...form.querySelectorAll('input[name=skus]:checked')].map(x=>x.value);
 const datesValid=validDraftPeriod(form.elements.period_start.value,form.elements.period_end.value);
 const price=datesValid?draftEstimate(state.draftPriceRows,checked,form.elements.period_start.value):null;
 output.textContent=!datesValid?t('draftDatesError'):!checked.length?t('draftSelectModules'):price===null?t('draftPriceUnavailable'):t('draftEstimate')+': '+price+' KGS · '+t('draftEstimateDisclaimer');
 button.disabled=price===null;
 if(packageButton)packageButton.disabled=price===null;
}
// UI-only package classification; the API still stores a versioned DRAFT title
// and explicit verified SKU IDs, never a made-up tariff entitlement.
function packageProposalTitle(kind,custom){
 if(!['BASE','BUSINESS','PREMIUM','CUSTOM'].includes(kind))return null;
 const title=String(custom||'').trim();
 if(kind==='CUSTOM')return title.length>=2&&title.length<=120?title:null;
 const result=!title||title===kind?kind:kind+' — '+title;
 return result.length<=120?result:null;
}
function applyPackageProposal(form){
 if(!form?.elements?.package_kind)return;
 const kind=form.elements.package_kind.value;
 const title=form.elements.title;
 if(!title)return;
 if(['BASE','BUSINESS','PREMIUM'].includes(title.value.trim())){
  title.value=kind==='CUSTOM'?'':kind;
 }else if(kind!=='CUSTOM' && !title.value.trim())title.value=kind;
 // Preserve explicitly entered custom names when switching package kind.
}
async function installationTrialPanel(){
 const labels={ru:{title:'Установка и пробный период',confirm:'Подтвердить завершение установки и настройки',from:'Начало пробного периода',until:'Окончание (не включительно)'},kg:{title:'Орнотуу жана сыноо мөөнөтү',confirm:'Орнотуу жана жөндөө аяктаганын ырастоо',from:'Сыноонун башталышы',until:'Аяктоо (бул күн кирбейт)'},en:{title:'Installation and trial',confirm:'Confirm installation and configuration complete',from:'Trial start',until:'End (exclusive)'}};
 const l=labels[state.lang]||labels.ru;
 const hotel=state.hotelId,r=await api('/v1/platform/installation-trial?hotel_id='+hotel);
 return '<section class="panel"><h2>'+safe(l.title)+'</h2>'+(r?'<div class="grid two">'+kv(l.from,r.trial_start)+kv(l.until,r.trial_end_exclusive)+'</div>':'<form id="hotel-installation-trial"><input type="hidden" name="hotel_id" value="'+safe(hotel)+'"><label class="check-row"><input type="checkbox" required>'+safe(l.confirm)+'</label><button class="primary" type="submit">'+safe(t('packageSave'))+'</button><div role="status" aria-live="polite"></div></form>')+'</section>';
}
async function saveInstallationTrial(form){
 const button=form.querySelector('button'),status=form.querySelector('[role=status]');
 button.disabled=true;
 try{await saveQaCatalogAction('installation-trial',{hotel_id:String(new FormData(form).get('hotel_id'))});await render();}
 catch(e){status.textContent=e.message;button.disabled=false;}
}
async function launchOfferPanel(){
 const l=({ru:{title:'Стартовая акция',reserved:'Зарезервировано',available:'Свободно',slot:'Место',hotel:'Гостиница',note:'Резервация не подтверждает оплату или активацию.',annual:'Подписка за год',setup:'Внедрение'},kg:{title:'Баштапкы акция',reserved:'Ээлеген орундар',available:'Бош орундар',slot:'Орун',hotel:'Мейманкана',note:'Орун ээлөө төлөмдү же активдештирүүнү ырастабайт.',annual:'Жылдык жазылуу',setup:'Орнотуу'},en:{title:'Launch offer',reserved:'Reserved',available:'Available',slot:'Slot',hotel:'Hotel',note:'Reservation does not confirm payment or activation.',annual:'Annual subscription',setup:'Implementation'}})[state.lang];
 const r=await api('/v1/platform/launch-offer');
 return '<section class="panel"><h2>'+safe(l.title)+'</h2><div class="grid two">'+kv(l.reserved,r.reserved+' / '+r.capacity)+kv(l.available,r.available)+'</div>'+info(l.note,'info')+(r.reservations.length?table([l.slot,l.hotel,t('packageType'),l.annual,l.setup,t('periodStart')],r.reservations.map(x=>'<tr><td>'+safe(x.slot)+'</td><td>'+safe(x.display_name)+'</td><td>'+safe(x.package_kind)+'</td><td>'+money(x.subscription_term_total,'KGS')+'</td><td>'+money(x.implementation_total,'KGS')+'</td><td>'+safe(date(x.created_at))+'</td></tr>')):empty(t('noData')))+'</section>';
}
async function commercialHotelOfferForm(){
 const r=await api('/v1/platform/commercial-policy'), p=r.policy;
 const labels={ru:{title:'Коммерческий тариф',note:'Предложение без активации подписки',extras:'Дополнительные модули'},kg:{title:'Коммерциялык тариф',note:'Жазылууну активдештирбеген сунуш',extras:'Кошумча модулдар'},en:{title:'Commercial tariff',note:'Offer without subscription activation',extras:'Additional modules'}};
 const l=labels[state.lang]||labels.ru;
 return '<section class="panel gold"><h2>'+safe(l.title)+'</h2>'+info(l.note,'info')+
 '<form id="hotel-commercial-offer" class="admin-form"><input type="hidden" name="policy_version" value="'+safe(r.version)+'"><label>'+safe(t('packageType'))+'<select name="package_kind">'+Object.entries(p.monthly_packages).map(([k,v])=>'<option value="'+safe(k)+'">'+safe(k)+' · '+money(v.price??v.base_price,p.currency)+'</option>').join('')+'</select></label>'+
 '<label>'+safe(t('periodStart'))+'<input type="date" name="period_start" required value="'+safe(dateValue(2))+'"></label>'+
 '<fieldset><legend>'+safe(l.extras)+'</legend>'+Object.entries(p.module_monthly_prices).map(([k,v])=>'<label class="check-row"><input type="checkbox" name="extras" value="'+safe(k)+'"><span>'+safe(k)+' · '+money(v,p.currency)+'</span></label>').join('')+'</fieldset>'+
 '<label>'+safe(t('packageDiscount'))+'<input name="discount_pct" type="number" min="0" max="100" step="0.01" value="0" required></label>'+
 '<label>'+safe({ru:'Месяцев',kg:'Ай',en:'Months'}[state.lang]||'Месяцев')+'<select name="term_months">'+[1,3,6,12].map(n=>'<option value="'+n+'">'+n+'</option>').join('')+'</select></label><label class="check-row"><input type="checkbox" name="standard_term_discount">'+safe({ru:'Стандартная скидка за срок',kg:'Мөөнөт үчүн стандарттык арзандатуу',en:'Standard term discount'}[state.lang]||'Стандартная скидка')+'</label><label class="check-row"><input type="checkbox" name="launch_offer">'+safe({ru:'Стартовая акция: 40% на первый год (резервация)',kg:'Баштапкы акция: биринчи жылга 40% (орун ээлөө)',en:'Launch offer: 40% off first year (reservation)'}[state.lang]||'Launch offer')+'</label><label class="check-row"><input type="checkbox" name="include_implementation">'+safe({ru:'Включить внедрение',kg:'Орнотууну кошуу',en:'Include implementation'}[state.lang]||'Включить внедрение')+'</label><button class="primary" type="submit">'+safe(t('packageSave'))+'</button><div role="status" aria-live="polite"></div></form></section>';
}
async function saveCommercialHotelOffer(form){
 const d=new FormData(form),button=form.querySelector('button[type=submit]'),status=form.querySelector('[role=status]');
 button.disabled=true;
 try{
 const kind=String(d.get('package_kind'));
 await saveQaCatalogAction('tariff-packages',{hotel_id:state.hotelId,package_kind:kind,title:kind,period_start:String(d.get('period_start')),skus:d.getAll('extras'),discount_pct:String(d.get('discount_pct')),trial_days:5,custom_monthly_price:null,commercial_policy_version:Number(d.get('policy_version')),term_months:Number(d.get('term_months')),launch_offer:d.has('launch_offer'),standard_term_discount:d.has('standard_term_discount'),include_implementation:d.has('include_implementation')});
 await render();
 }catch(e){status.textContent=e.message;button.disabled=false;}
}
async function subscriptionDraftForm(){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_catalog_admin_enabled)
   return heading(t('configurationDraft'))+info(t('operationBlocked'));
 const hotel=state.hotelId;
 if(!hotel)return heading(t('configurationDraft'))+empty(t('noSelected'));
 const skuRows=await api('/v1/platform/catalog');
 const allowed=skuRows.filter(r=>r.status==='AVAILABLE'&&!r.is_core&&r.latest_price);
 state.draftPriceRows=allowed;
 if(!allowed.length)return heading(t('configurationDraft'))+info(t('noSelectable'))+
   '<button type="button" class="outline" data-view="hotel">'+safe(t('cancel'))+'</button>';
 const templates=await api('/v1/platform/tariff-templates');
 const available=new Set(allowed.map(row=>row.sku));
 const templateOptions=templates.map(row=>'<option value="'+safe(row.id)+'" data-kind="'+safe(row.package_kind)+
   '" data-skus="'+safe(JSON.stringify(row.skus))+'"'+(row.skus.every(s=>available.has(s))?'':' disabled')+'>'+
   safe(row.package_kind)+' v'+safe(row.revision)+' · '+safe(row.skus.join(', '))+'</option>').join('');
 const checkboxes=allowed.map(r=>'<label class="check-row"><input type="checkbox" name="skus" value="'+safe(r.sku)+'"><span>'+safe(r.name)+' — '+safe(r.sku)+'</span></label>').join('');
 return heading(t('configurationDraft'),hotel)+info(t('draftOnly'),'info')+
 '<section class="panel gold"><form id="subscription-draft-form" class="admin-form">'+
 '<label>'+safe(t('sharedTemplate'))+'<select name="source_template_id"><option value="">'+safe(t('manualSelection'))+'</option>'+templateOptions+'</select></label>'+
 '<label>'+safe(t('packageType'))+'<select name="package_kind" required>'+
 '<option value="BASE">BASE</option><option value="BUSINESS">BUSINESS</option>'+
 '<option value="PREMIUM">PREMIUM</option><option value="CUSTOM">'+safe(t('packageCustom'))+'</option></select></label>'+
 '<p class="muted">'+safe(t('packageNote'))+'</p>'+
 '<label>'+safe(t('packageLabel'))+'<input name="title" required maxlength="120" value="BASE"></label>'+
 '<label>'+safe(t('periodStart'))+'<input type="date" name="period_start" required value="'+safe(dateValue(2))+'"></label>'+
 '<label>'+safe(t('periodEnd'))+'<input type="date" name="period_end" required value="'+safe(dateValue(32))+'"></label>'+
 '<fieldset><legend>'+safe(t('selectFunctions'))+'</legend>'+checkboxes+'</fieldset>'+
 '<label>'+safe(t('packageDiscount'))+'<input name="discount_pct" inputmode="decimal" pattern="(?:0|[1-9][0-9]{0,2})(?:[.][0-9]{1,2})?" value="0" required></label>'+
 '<label>'+safe(t('packageTrial'))+'<input name="trial_days" type="number" min="0" max="90" step="1" value="0" required></label>'+
 '<label>'+safe(t('packageCustomPrice'))+'<input name="custom_monthly_price" inputmode="decimal" pattern="(?:0|[1-9][0-9]{0,11})(?:[.][0-9]{1,2})?" placeholder="CUSTOM"></label>'+
 '<div id="draft-estimate" role="status" aria-live="polite">'+safe(t('draftSelectModules'))+'</div>'+
 '<div class="formbar"><button class="primary" type="submit" disabled>'+safe(t('saveDraft'))+'</button>'+
 '<button class="outline" type="button" data-package-save="yes" disabled>'+safe(t('packageSave'))+'</button>'+
 '<button class="outline" type="button" data-view="hotel">'+safe(t('cancel'))+'</button></div>'+
 '<div id="admin-action-status" role="status" aria-live="polite"></div></form></section>';
}
async function submitAdminForm(form,kind){
 const button=kind==='package'?form.querySelector('[data-package-save]'):form.querySelector('[type=submit]');
 if(!button)return;
 button.disabled=true;
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
  }else if(kind==='draft'||kind==='package'){
   const checked=[...form.querySelectorAll('input[name=skus]:checked')].map(x=>x.value);
   if(!checked.length)throw Error(t('draftSelectModules'));
   if(!validDraftPeriod(form.elements.period_start.value,form.elements.period_end.value))
     throw Error(t('draftDatesError'));
   if(draftEstimate(state.draftPriceRows,checked,form.elements.period_start.value)===null)
     throw Error(t('draftPriceUnavailable'));
   const proposalTitle=packageProposalTitle(form.elements.package_kind.value,form.elements.title.value);
   if(!proposalTitle)throw Error(t('packageTitleRequired'));
   if(kind==='package'){
     const discount=form.elements.discount_pct.value.trim();
     const trial=Number(form.elements.trial_days.value);
     const custom=form.elements.custom_monthly_price.value.trim()||null;
     if(!/^(?:0|[1-9][0-9]{0,2})(?:[.][0-9]{1,2})?$/.test(discount)||Number(discount)>100||
        !Number.isInteger(trial)||trial<0||trial>90||
        (custom!==null&&(form.elements.package_kind.value!=='CUSTOM'||Number(discount)!==0)))
       throw Error(t('packagePriceOverride'));
     data=await saveQaCatalogAction('tariff-packages',{
       hotel_id:state.hotelId,package_kind:form.elements.package_kind.value,
       title:proposalTitle,period_start:form.elements.period_start.value,
       skus:checked,discount_pct:discount,trial_days:trial,
       ...(form.elements.source_template_id.value?{source_template_id:form.elements.source_template_id.value}:{}),
       custom_monthly_price:custom
     });
   } else {
     data=await saveQaCatalogAction('subscription-drafts',{
       hotel_id:state.hotelId,title:proposalTitle,
       period_start:form.elements.period_start.value,period_end:form.elements.period_end.value,
       skus:checked});
   }
   if(data.state!=='DRAFT'||data.enforcement!=='OFF'||data.subscription_activated!==false)
     throw Error('Unexpected configuration state');
  }
  result.innerHTML=info(t(kind==='sku'?'notPublished':kind==='price'?'priceChanged':
    kind==='package'?'packageSaved':'draftCreated'),'info');
  button.disabled=true;form.reset();
  const packageBtn=form.querySelector('[data-package-save]');
  if(packageBtn)packageBtn.disabled=true;
 } catch(e){result.textContent=t('adminError')+': '+e.message;button.disabled=false}
}

function billingHold(){
 return heading('BILLING',t('billingHold'))+info(t('billingHold'),'info');
}
const profileCopy={
 ru:{title:'Мой профиль',name:'Имя и фамилия',email:'Электронная почта',role:'Роль',save:'Сохранить имя',saved:'Имя сохранено',failed:'Не удалось сохранить имя',unavailable:'Сессия недоступна. Войдите снова.',security:'Безопасность аккаунта',"newEmail": "Новая почта", "changeEmail": "Изменить почту", "checkInbox": "Проверьте новый почтовый ящик для подтверждения.", "currentPassword": "Текущий пароль", "newPassword": "Новый пароль", "changePassword": "Изменить пароль", "accountError": "Не удалось сохранить изменение. Проверьте данные."},
 kg:{title:'Менин профилим',name:'Аты-жөнү',email:'Электрондук почта',role:'Роль',save:'Атты сактоо',saved:'Аты сакталды',failed:'Атты сактоо мүмкүн болгон жок',unavailable:'Сессия жеткиликсиз. Кайра кириңиз.',security:'Аккаунттун коопсуздугу',"newEmail": "Жаңы электрондук почта", "changeEmail": "Почтаны өзгөртүү", "checkInbox": "Ырастоо үчүн жаңы почтаңызды текшериңиз.", "currentPassword": "Учурдагы сырсөз", "newPassword": "Жаңы сырсөз", "changePassword": "Сырсөздү өзгөртүү", "accountError": "Өзгөртүү сакталган жок. Маалыматтарды текшериңиз."},
 en:{title:'My profile',name:'Full name',email:'Email',role:'Role',save:'Save name',saved:'Name saved',failed:'Unable to save name',unavailable:'Session unavailable. Sign in again.',security:'Account security',"newEmail": "New email address", "changeEmail": "Change email", "checkInbox": "Check the new inbox to confirm your address.", "currentPassword": "Current password", "newPassword": "New password", "changePassword": "Change password", "accountError": "The change could not be saved. Check your details."}
};
const profileText=k=>(profileCopy[state.lang]||profileCopy.ru)[k];
async function profile(){
 const session=await identitySession();
 const p=profileText;
 if(!session?.user)return heading(p('title'))+info(p('unavailable'));
 return heading(p('title'))+'<section class="panel"><form id="flex-profile-form"><label>'+safe(p('name'))+'<input name="name" required maxlength="120" autocomplete="name" value="'+safe(session.user.name)+'"></label><label>'+safe(p('email'))+'<input type="email" readonly value="'+safe(session.user.email)+'"></label><p>'+safe(p('role'))+': '+safe(state.me.role)+'</p><button class="primary" type="submit">'+safe(p('save'))+'</button><p role="status" id="flex-profile-result"></p></form></section><section class="panel"><h2>'+safe(p('security'))+'</h2><form id="profile-email"><label>'+safe(p('newEmail'))+'<input required type="email" name="newEmail" autocomplete="email"></label><button type="submit">'+safe(p('changeEmail'))+'</button><p role="status"></p></form><form id="profile-password"><label>'+safe(p('currentPassword'))+'<input required type="password" name="currentPassword" autocomplete="current-password"></label><label>'+safe(p('newPassword'))+'<input required type="password" name="newPassword" minlength="12" maxlength="128" autocomplete="new-password"></label><button type="submit">'+safe(p('changePassword'))+'</button><p role="status"></p></form></section>';
}
async function saveProfile(form){
 const button=form.querySelector('button[type="submit"]'), result=form.querySelector('[role="status"]');
 button.disabled=true;
 try{const name=form.elements.name.value.trim();if(!name)throw Error('EMPTY_NAME');await identityRequest('update-user',{name});state.identitySession=await identitySession();result.textContent=profileText('saved');}catch{result.textContent=profileText('failed');}finally{button.disabled=false;}
}
async function saveAccountSettings(form) {
 const button=form.querySelector('button');
 const status=form.querySelector('[role="status"]');
 button.disabled=true;
 try {
   if(form.id==='profile-email') {
     await identityRequest('change-email',{newEmail:form.elements.newEmail.value.trim(),callbackURL:'/'});
     form.reset();
     status.textContent=profileText('checkInbox');
   } else {
     await identityRequest('change-password',{currentPassword:form.elements.currentPassword.value,
       newPassword:form.elements.newPassword.value,revokeOtherSessions:true});
     form.reset();
     await identityRequest('sign-out',{});
     location.replace('/api/auth/logout');
   }
 } catch {
   status.textContent=profileText('accountError');
 } finally {
   button.disabled=false;
 }
}
function renderNav(){
 const r=state.me?.role;
 const choices=r==='SUPER_ADMIN'?[['overview','overview','◈'],['hotels','hotels','⌂'],['catalog','catalog','◇'],['obligations','obligations','↗']]:
 r==='HOTEL_OWNER'?[['subscription','subscription','⌂'],['catalog','catalog','◇']]:
 r==='SALES_AGENT'||r==='INVESTOR'?[['earnings','earnings','↗']]:[];
 if(state.me&&state.status?.identity_ready)choices.push(['profile','profile','◎']);
 nav.innerHTML=choices.map(([id,label,icon])=>'<button type="button" data-view="'+id+'" class="'+(state.view===id?'active':'')+'"><span>'+icon+'</span>'+safe(label==='profile'?profileText('title'):t(label))+'</button>').join('');
 document.getElementById('session-button').textContent=t(state.me?'logout':'login');
 document.querySelectorAll('[data-i18n]').forEach(x=>x.textContent=t(x.dataset.i18n));
 const themeButton=document.getElementById('theme');themeButton.title=t('theme');themeButton.setAttribute('aria-label',t('theme'));document.getElementById('lang').setAttribute('aria-label',t('lang'));nav.setAttribute('aria-label',t('navigation'));document.title=t('footerBrand');
}
function showLogin(){
 nav.innerHTML='';
 document.getElementById('session-button').textContent=t('login');
 const configured=state.status?.configured;
 if(state.status?.identity_ready) {
   if(state.status.password_login){main.innerHTML=identityPanel();return;}
   main.innerHTML=heading(identityText('heading'))+identityPanel()+
     info(safe(configured?t('loginPrompt'):t('configHelp')),'info');
   return;
 }
 main.innerHTML=heading(configured?t('loginPrompt'):t('notConfigured'))+
 '<div class="panel gold"><h2>'+safe(t('controlPlane'))+'</h2><p class="muted">'+safe(configured?t('loginPrompt'):t('configHelp'))+'</p>'+
 (configured?'<button class="primary" type="button" data-login="yes">'+safe(t('login'))+'</button>':'')+'</div>'+
 info(t(configured?'authRequired':'noLiveData'),'info');
}
function periodButtons(){return '<div class="period" role="group" aria-label="'+safe(t('period'))+'">'+[['day','periodDay'],['week','periodWeek'],['month','periodMonth']].map(([p,k])=>'<button type="button" data-period="'+p+'" class="'+(state.period===p?'active':'')+'">'+safe(t(k))+'</button>').join('')+'</div>'}
function errorPage(err){const msg=err?.status===403?t('accessDenied'):t('error');main.innerHTML=heading(msg)+info(err.message||msg,'error')+'<button class="outline" type="button" data-retry="1">'+safe(t('retry'))+'</button>';}
async function overview(){
 const results=await Promise.allSettled([api('/v1/hotels'),api('/v1/catalog'),api('/v1/platform/partner-earnings-summary?period='+state.period)]);
 const h=results[0].status==='fulfilled'?results[0].value:null;
 const c=results[1].status==='fulfilled'?results[1].value:null;
 const e=results[2].status==='fulfilled'?results[2].value:null;
 if(!h&&!c&&!e) throw results[0].reason;
 const sectionNames=[t('hotels'),t('features'),t('obligations')];
 const degraded=results.map((r,i)=>r.status==='rejected'
   ?info(t('error')+': '+sectionNames[i]+' (HTTP '+safe(r.reason?.status||'—')+')','error'):'').join('');
 return heading(t('welcome'),t('helpQa'))+degraded+periodButtons()+'<div class="grid spacing-top">'+metric(t('activeHotels'),h?.length??'—','cyan-text')+
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
// Read-only hotel cards must not report outages as missing commercial data.
// Only an explicit 404 on the subscription GET is a legitimate empty state.
function hotelReadResult(result,allowNotFound=false){
 if(result.status==='fulfilled')return result.value;
 if(allowNotFound&&result.reason?.status===404)return null;
 throw result.reason||Error('HOTEL_READ_FAILED');
}
function hotelEditText(key){
 const labels={ru:{edit:'Редактировать гостиницу',save:'Сохранить',saved:'Название сохранено'},kg:{edit:'Мейманкананы түзөтүү',save:'Сактоо',saved:'Аталышы сакталды'},en:{edit:'Edit hotel',save:'Save',saved:'Hotel name saved'}};
 return (labels[state.lang]||labels.ru)[key];
}
async function hotelNameForm(id){
 if(state.me?.role!=='SUPER_ADMIN'||!state.status?.qa_onboarding_enabled)return '';
 const hotels=await api('/v1/hotels');
 const hotel=hotels.find(h=>h.id===id);
 if(!hotel||!['PENDING','ACTIVE'].includes(hotel.status))return '';
 return '<section class="panel spacing-top"><h2>'+safe(hotelEditText('edit'))+'</h2><form id="hotel-name-form" data-id="'+safe(id)+'">'+
 '<label for="hotel-edit-name">'+safe(t('name'))+'</label><br><input id="hotel-edit-name" name="display_name" required minlength="2" maxlength="180" value="'+safe(hotel.name)+'">'+
 '<input type="hidden" name="expected_name" value="'+safe(hotel.name)+'"><div class="formbar"><button class="primary" type="submit">'+safe(hotelEditText('save'))+'</button></div>'+
 '<div role="status" aria-live="polite"></div></form></section>';
}
async function submitHotelName(form){
 const button=form.querySelector('button[type=submit]'),output=form.querySelector('[role=status]');
 button.disabled=true;
 try{
  const result=await postQaLink('hotels/'+form.dataset.id+'/name',{display_name:form.elements.display_name.value.trim(),expected_name:form.elements.expected_name.value});
  form.elements.expected_name.value=result.name;form.elements.display_name.value=result.name;
  output.textContent=hotelEditText('saved');
 }catch(e){output.textContent=t('error')+': '+e.message;}
 finally{button.disabled=false;}
}

function customerLabels(){
 return ({ru:{profile:'Контакты гостиницы',contact_name:'Контактное лицо',contact_email:'Email',contact_phone:'Телефон',responsible_name:'Ответственный',save:'Сохранить изменения',history:'История контактов',agreements:'Договоры',draft:'Создать черновик договора',preview:'Создать предварительный счёт',previews:'Предварительные счета',note:'Черновики не подписаны. Налоги не рассчитаны. Оплата и активация отключены.',offer:'Тарифное предложение'},kg:{profile:'Мейманкананын байланыштары',contact_name:'Байланыш адамы',contact_email:'Email',contact_phone:'Телефон',responsible_name:'Жооптуу адам',save:'Өзгөртүүлөрдү сактоо',history:'Байланыштардын тарыхы',agreements:'Келишимдер',draft:'Келишимдин долбоорун түзүү',preview:'Алдын ала эсеп түзүү',previews:'Алдын ала эсептер',note:'Долбоорлорго кол коюлган эмес. Салыктар эсептелген жок. Төлөм жана активдештирүү өчүрүлгөн.',offer:'Тарифтик сунуш'},en:{profile:'Hotel contacts',contact_name:'Contact person',contact_email:'Email',contact_phone:'Phone',responsible_name:'Responsible person',save:'Save changes',history:'Contact history',agreements:'Agreements',draft:'Create agreement draft',preview:'Create invoice preview',previews:'Invoice previews',note:'Drafts are unsigned. Taxes are not calculated. Payments and activation are disabled.',offer:'Tariff offer'}})[state.lang];
}
async function customerProfilePanel(historyOnly=false){
 const l=customerLabels(),r=await api('/v1/platform/customer-profile?hotel_id='+state.hotelId),p=r.current||{};
 const fields=['contact_name','contact_email','contact_phone','responsible_name'];
 return '<section class="panel"><h2>'+safe(historyOnly?l.history:l.profile)+'</h2>'+
 (historyOnly?(r.history.length?table([t('skuVersion'),...fields.map(k=>l[k]),t('periodStart')],r.history.map(x=>'<tr><td>'+safe(x.version)+'</td>'+fields.map(k=>'<td>'+safe(x[k]||'—')+'</td>').join('')+'<td>'+safe(date(x.created_at))+'</td></tr>')):empty(t('noData'))):
 '<form id="customer-profile-form" class="admin-form"><input type="hidden" name="expected_version" value="'+safe(p.version||0)+'">'+fields.map(k=>'<label>'+safe(l[k])+'<input name="'+k+'" type="'+(k==='contact_email'?'email':k==='contact_phone'?'tel':'text')+'" maxlength="'+({contact_name:180,contact_email:254,contact_phone:40,responsible_name:180}[k])+'" value="'+safe(p[k]||'')+'"></label>').join('')+'<button class="primary" type="submit">'+safe(l.save)+'</button><div role="status" aria-live="polite"></div></form>')+'</section>';
}
async function agreementPanel(){
 const l=customerLabels(),id=state.hotelId;
 const [r,offers]=await Promise.all([api('/v1/platform/agreement-drafts?hotel_id='+id),api('/v1/platform/tariff-packages?hotel_id='+id)]);
 const usable=offers.filter(x=>x.commercial_policy_version&&x.term_months&&!r.agreements.some(a=>a.source_offer_id===x.id));
 return '<section class="panel"><h2>'+safe(l.agreements)+'</h2>'+info(l.note,'info')+
 (usable.length?'<form id="agreement-draft-form" class="admin-form"><label>'+safe(l.offer)+'<select name="offer_id">'+usable.map(x=>'<option value="'+safe(x.id)+'">'+safe(x.package_kind)+' · v'+safe(x.version)+' · '+money(x.subscription_term_total,'KGS')+'</option>').join('')+'</select></label><button type="submit" class="primary">'+safe(l.draft)+'</button><div role="status" aria-live="polite"></div></form>':'')+
 (r.agreements.length?table([t('skuVersion'),t('packageType'),t('status'),t('total'),t('actions')],r.agreements.map(a=>'<tr><td>'+safe(a.version)+'</td><td>'+safe(a.terms?.package_kind||'—')+'</td><td>'+safe(a.state)+'</td><td>'+money(a.terms?.subscription_term_total||0,'KGS')+'</td><td>'+(a.state==='DRAFT'&&a.source_offer_id&&!r.previews.some(p=>p.agreement_version_id===a.id)?'<form class="invoice-preview-form"><input type="hidden" name="agreement_id" value="'+safe(a.id)+'"><button type="submit" class="outline">'+safe(l.preview)+'</button><div role="status"></div></form>':'—')+'</td></tr>')):empty(t('noData')))+
 '<h3>'+safe(l.previews)+'</h3>'+(r.previews.length?table([t('period'),t('total'),t('status')],r.previews.map(x=>'<tr><td>'+safe(x.period_start)+' — '+safe(x.period_end)+'</td><td>'+money(x.amount_before_unresolved_taxes,'KGS')+'</td><td>'+safe(x.status)+'</td></tr>')):empty(t('noData')))+'</section>';
}
async function submitCustomerOperation(form,kind){
 const d=new FormData(form),button=form.querySelector('button[type=submit]'),status=form.querySelector('[role=status]');
 button.disabled=true;
 try{
  const payload={hotel_id:state.hotelId,...Object.fromEntries(d)};
  if(kind==='customer-profile')payload.expected_version=Number(payload.expected_version);
  await saveQaCatalogAction(kind,payload);
  await render();
 }catch(e){status.textContent=e.message;button.disabled=false;}
}

function hotelCardTabs(){
 const admin=state.me?.role==='SUPER_ADMIN';
 const sections=[['overview','hotelTabOverview'],['subscription','subscription'],['finance','hotelTabFinance'],['usage','hotelTabUsage']];
 if(admin)sections.push(['relations','hotelTabRelations'],['history','hotelTabHistory']);
 const valid=sections.some(x=>x[0]===state.hotelTab);
 if(!valid)state.hotelTab='overview';
 return '<nav class="toolbar" aria-label="'+safe(t('selected'))+'">'+sections.map(([key,label])=>
   '<button type="button" data-hotel-tab="'+key+'" class="'+(state.hotelTab===key?'primary':'outline')+'" aria-current="'+(state.hotelTab===key?'page':'false')+'">'+safe(t(label))+'</button>').join('')+'</nav>';
}

async function hotelDetail(){
 const id=state.hotelId;
 if(!/^[0-9a-fA-F-]{36}$/.test(id||'')) return heading(t('noSelected'))+empty(t('noSelected'));
 const tabBar=hotelCardTabs();
 const metadata=heading(t('selected'),id)+tabBar+toolbar()+
  (state.me?.role==='SUPER_ADMIN'&&state.hotelTab==='subscription'&&state.status?.qa_catalog_admin_enabled?'<button type="button" class="outline" data-view="subscription-draft">'+safe(t('configure'))+'</button>':'')+
  (state.me?.role==='SUPER_ADMIN'&&state.hotelTab==='overview'?'<button type="button" class="outline" data-link="'+safe(id)+'">'+safe(t('linkHotel'))+'</button>':'')+
  '<button type="button" class="subtle" data-view="'+(state.me?.role==='SUPER_ADMIN'?'hotels':'subscription')+'">← '+safe(t('openBack'))+'</button>';
 if(state.hotelTab==='history'&&state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled)return metadata+await customerProfilePanel(true).catch(e=>info(e.message,'error'))+await agreementPanel().catch(e=>info(e.message,'error'));
 if(['usage','relations','history'].includes(state.hotelTab)){
  return metadata+'<section class="panel spacing-top"><h2>'+
   safe(t(state.hotelTab==='usage'?'hotelTabUsage':state.hotelTab==='relations'?'hotelTabRelations':'hotelTabHistory'))+
   '</h2>'+info(t('hotelTabPending'),'info')+'</section>';
 }
 const [sub,inv]=await Promise.allSettled([api('/v1/hotels/'+id+'/subscription'),api('/v1/hotels/'+id+'/invoices')]);
 const subscription=hotelReadResult(sub,true);
 const invoices=hotelReadResult(inv);
 let draftHistory='';
 if(state.hotelTab==='subscription'&&state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled){
  try {
   const drafts=await api('/v1/platform/subscription-drafts?hotel_id='+id);
   draftHistory='<section class="panel"><h2>'+safe(t('draftList'))+'</h2>'+
   (drafts.length?table([t('skuVersion'),t('draftTitle'),t('period'),t('status'),t('monthlyEstimate')],
   drafts.map(d=>'<tr><td>v'+safe(d.version)+'</td><td>'+safe(d.title)+'</td>'+
   '<td>'+safe(d.period_start)+' — '+safe(d.period_end)+'</td><td><span class="chip">'+safe(d.state)+' · OFF</span></td>'+
   '<td>'+money(d.proposed_monthly_total,d.currency)+'</td></tr>')):empty(t('noDrafts')))+
   '</section>'+info(t('draftOnly'),'info');
   const packages=await api('/v1/platform/tariff-packages?hotel_id='+id);
   draftHistory+='<section class="panel"><h2>'+safe(t('packageHistory'))+'</h2>'+
    (packages.length?table([t('packageType'),t('skuVersion'),t('draftTitle'),
     t('packageDiscount'),t('packageTrial'),t('monthlyEstimate'),t('status')],
     packages.map(d=>'<tr><td>'+safe(d.package_kind)+'</td><td>v'+safe(d.version)+'</td>'+
     '<td>'+safe(d.title)+'</td><td>'+safe(d.discount_pct)+'%</td>'+
     '<td>'+safe(d.trial_days)+'</td><td>'+money(d.proposed_monthly_total,d.currency)+
     '</td><td>'+safe(d.state)+' · OFF'+(d.package_kind==='CUSTOM'?'':' <button type="button" data-publish-template="'+safe(d.id)+'">'+safe(t('publishTemplate'))+'</button>')+'</td></tr>')):empty(t('noDrafts')))+
    '</section>';
  } catch(e){ draftHistory+=info(t('error')+': '+e.message,'error'); }
 }

 const summary='<div class="grid three spacing-top">'+metric(t('planStatus'),subscription?.status??'—')+
  metric(t('enforcement'),subscription?.enforcement??'—')+
  metric(t('expires'),date(subscription?.period_end))+'</div>';
 const subscriptionInfo='<section class="panel"><h2>'+safe(t('subscription'))+'</h2>'+
  (subscription?'<div class="grid three">'+kv(t('periodStart'),date(subscription.period_start))+
  kv(t('periodEnd'),date(subscription.period_end))+kv(t('grace'),date(subscription.grace_until))+
  '</div>':empty(t('noSubscription')))+'</section>';
 const invoicesInfo='<section class="panel"><h2>'+safe(t('invoices'))+'</h2>'+
  (invoices?.length?table([t('invoice'),t('status'),t('total'),t('due')],invoices.map(i=>
   '<tr><td>'+safe(i.number||i.id)+'</td><td><span class="chip">'+safe(i.status)+
   '</span></td><td>'+money(i.total,i.currency)+'</td><td>'+safe(date(i.due_at))+'</td></tr>')):
   empty(t('noInvoices')))+'</section>';
 if(state.hotelTab==='finance')return metadata+invoicesInfo+info(t('warning'),'info');
 if(state.hotelTab==='subscription')return metadata+summary+subscriptionInfo+(state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled?await installationTrialPanel().catch(e=>info(e.message,'error'))+await commercialHotelOfferForm().catch(e=>info(e.message,'error')):'')+draftHistory+info(t('draftOnly'),'info');
 return metadata+await hotelNameForm(id)+(state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled?await customerProfilePanel().catch(e=>info(e.message,'error')):'')+summary+subscriptionInfo+info(t('warning'),'info');
}


async function commercialPolicyPanel(){
 const labels={ru:{title:'Утверждённые тарифы',note:'Коммерческие цены. Техническая доступность модулей проверяется отдельно.',setup:'Внедрение',trial:'Пробный период (дней)',term:'Месяцев',discount:'Скидка'},kg:{title:'Бекитилген тарифтер',note:'Коммерциялык баалар. Модулдардын техникалык жеткиликтүүлүгү өзүнчө текшерилет.',setup:'Орнотуу',trial:'Сыноо мезгили (күн)',term:'Ай',discount:'Арзандатуу'},en:{title:'Approved tariffs',note:'Commercial prices. Technical module availability is verified separately.',setup:'Implementation',trial:'Trial (days)',term:'Months',discount:'Discount'}};
 const l=labels[state.lang]||labels.ru;
 const edit={ru:'Изменить коммерческую цену',kg:'Коммерциялык бааны өзгөртүү',en:'Edit commercial price'}[state.lang]||'Изменить коммерческую цену';
 try{
  const r=await api('/v1/platform/commercial-policy'),p=r.policy;
  return '<section class="panel spacing-top"><h2>'+safe(l.title)+' · v'+safe(r.version)+'</h2>'+
   table([t('packageType'),t('price')],Object.entries(p.monthly_packages).map(([k,v])=>'<tr><td>'+safe(k)+'</td><td>'+money(v.price??v.base_price,p.currency)+'</td></tr>'))+
   '<h3>'+safe(t('features'))+'</h3>'+table([t('sku'),t('price')],Object.entries(p.module_monthly_prices).map(([k,v])=>'<tr><td>'+safe(k)+'</td><td>'+money(v,p.currency)+'</td></tr>'))+
   '<form id="commercial-price-form" class="admin-form"><h3>'+safe(edit)+'</h3><input type="hidden" name="expected_version" value="'+safe(r.version)+'"><label>'+safe(t('sku'))+'<select name="item">'+['BASE','BUSINESS','PREMIUM'].map(k=>'<option value="PACKAGE:'+safe(k)+'">'+safe(k)+'</option>').join('')+Object.keys(p.module_monthly_prices).map(k=>'<option value="MODULE:'+safe(k)+'">'+safe(k)+'</option>').join('')+'</select></label><label>'+safe(t('price'))+'<input name="monthly_price" type="number" min="0.01" max="999999999999.99" step="0.01" required></label><button type="submit" class="primary">'+safe(t('savePlanned'))+'</button><div role="status" aria-live="polite"></div></form>'+ 
   table([l.term,l.discount],Object.entries(p.term_discounts_pct).map(([k,v])=>'<tr><td>'+safe(k)+'</td><td>'+safe(v)+'%</td></tr>'))+
   '<div class="grid two">'+kv(l.setup,money(p.implementation_fee,p.currency))+kv(l.trial,p.trial.calendar_days)+'</div>'+info(l.note,'info')+'</section>';
 }catch(e){return '<section class="panel">'+info(t('error')+': '+e.message,'error')+'</section>';}
}

async function catalog(){
 if(state.me?.role==='SUPER_ADMIN'&&state.status?.qa_catalog_admin_enabled){
  const items=await api('/v1/platform/catalog');
  state.catalogItems=items;
  return heading(t('adminCatalog'),t('helpQa'))+toolbar()+adminCatalogButtons()+await commercialPolicyPanel()+await launchOfferPanel().catch(e=>info(e.message,'error'))+
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
 main.innerHTML='<div class="skeleton" aria-label="'+safe(t('loading'))+'"></div>';
 try{const views={overview,'billing-hold':billingHold,hotels:hotelList,catalog,'catalog-new':skuForm,'catalog-price':futurePriceForm,'catalog-versions':versionsPage,'subscription-draft':subscriptionDraftForm,obligations,hotel:hotelDetail,'hotel-new':registrationForm,'hotel-link':linkWizard,subscription,earnings,profile};const html=await (views[state.view]||overview)();if(serial!==state.serial)return;main.innerHTML=html;}
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
 if(b.dataset.hotel){state.hotelId=b.dataset.hotel;state.hotelTab='overview';state.view=state.me.role==='SUPER_ADMIN'?'hotel':'subscription';state.linkChallenge=null;state.linkSuccess=false;render();}
 if(b.dataset.hotelTab && ['overview','subscription','finance','usage','relations','history'].includes(b.dataset.hotelTab)){state.hotelTab=b.dataset.hotelTab;render();}
 if(b.dataset.link){state.hotelId=b.dataset.link;state.view='hotel-link';state.linkChallenge=null;state.linkSuccess=false;render();}
 if(b.dataset.period){state.period=b.dataset.period;render();}
 if(b.dataset.skuPrice){state.priceSku=b.dataset.skuPrice;state.view='catalog-price';render();}
 if(b.dataset.skuVersions){state.priceSku=b.dataset.skuVersions;state.view='catalog-versions';render();}
 if(b.dataset.publishTemplate){
  b.disabled=true;
  saveQaCatalogAction('tariff-templates',{package_id:b.dataset.publishTemplate})
   .then(()=>{b.textContent=t('templateSaved')})
   .catch(err=>{b.disabled=false;main.insertAdjacentHTML('afterbegin',info(t('error')+': '+err.message,'error'))});
 }
 if(b.dataset.packageSave){const form=document.getElementById('subscription-draft-form');if(form)submitAdminForm(form,'package');}
 if(b.dataset.retry)render();
 if(b.dataset.refresh)render();
 if(b.dataset.export){b.disabled=true;exportVisible().catch(err=>{main.insertAdjacentHTML('afterbegin',info(t('error')+': '+err.message,'error'))}).finally(()=>{b.disabled=false})}
 if(b.dataset.recoveryOpen){state.identityStep='forgot';state.recoveryMessage='';render();return;}
 if(b.dataset.recoveryBack){recoveryToken=null;state.identityStep='email';state.recoveryMessage='';render();return;}
 if(b.dataset.login)location.assign('/api/auth/login');
 if(b.dataset.identityLogout){
   identityRequest('sign-out',{}).then(()=>{
     location.assign('/api/auth/logout');
   }).catch(()=>{state.identityError=identityText('failed');render()});
 }
});
main.addEventListener('input',e=>{if(e.target.id==='hotel-search'){state.search=e.target.value;const rows=main.querySelectorAll('tbody tr');rows.forEach(tr=>tr.hidden=!tr.querySelector('td')?.textContent.toLocaleLowerCase().includes(state.search.toLocaleLowerCase()));}});
main.addEventListener('change',e=>{
 if(e.target.id==='hotel-status'){state.hotelStatus=e.target.value;render()}
 const draft=e.target.closest('#subscription-draft-form');
 if(draft){
  const selector=draft.elements.source_template_id;
  if(e.target===selector && selector.value){
   const option=selector.selectedOptions[0];
   const selected=new Set(JSON.parse(option.dataset.skus));
   draft.elements.package_kind.value=option.dataset.kind;
   applyPackageProposal(draft);
   draft.elements.custom_monthly_price.value='';
   for(const box of draft.querySelectorAll('input[name=skus]'))box.checked=selected.has(box.value);
  } else if(e.target.name==='package_kind'||e.target.name==='skus'){
   selector.value='';
   if(e.target.name==='package_kind')applyPackageProposal(draft);
  }
  refreshDraftEstimate(draft);
 }
});
async function submitCommercialPrice(form){
 const d=new FormData(form),[price_kind,code]=String(d.get('item')).split(':');
 const button=form.querySelector('button[type=submit]'),status=form.querySelector('[role=status]');
 button.disabled=true;
 try{await saveQaCatalogAction('commercial-policy',{expected_version:Number(d.get('expected_version')),price_kind,code,monthly_price:String(d.get('monthly_price'))});await render();}
 catch(err){status.textContent=err.message;button.disabled=false;}
}
main.addEventListener('submit',e=>{
 if(e.target.id==='customer-profile-form'){e.preventDefault();submitCustomerOperation(e.target,'customer-profile');return;}
 if(e.target.id==='agreement-draft-form'){e.preventDefault();submitCustomerOperation(e.target,'agreement-drafts');return;}
 if(e.target.classList.contains('invoice-preview-form')){e.preventDefault();submitCustomerOperation(e.target,'invoice-previews');return;}
 if(e.target.id==='hotel-installation-trial'){e.preventDefault();saveInstallationTrial(e.target);return;}
 if(e.target.id==='hotel-commercial-offer'){e.preventDefault();saveCommercialHotelOffer(e.target);return;}
 if(e.target.id==='commercial-price-form'){e.preventDefault();submitCommercialPrice(e.target);return;}
 if(['profile-email','profile-password'].includes(e.target.id)){e.preventDefault();saveAccountSettings(e.target);return;}
 if(e.target.id==='flex-profile-form'){e.preventDefault();saveProfile(e.target);return;}
 if(e.target.id==='flex-recovery-form'){e.preventDefault();submitRecovery(e.target);return;}
 if(e.target.id==='flex-identity-signin'||e.target.id==='flex-identity-totp'){e.preventDefault();submitIdentityForm(e.target)}
 if(e.target.id==='hotel-name-form'){e.preventDefault();submitHotelName(e.target);return;}
 if(e.target.id==='hotel-registration'){e.preventDefault();submitRegistration(e.target)}
 if(e.target.id==='link-challenge-form'){e.preventDefault();handleLinkForm(e.target,'challenge')}
 if(e.target.id==='link-confirm-form'){e.preventDefault();handleLinkForm(e.target,'confirm')}
 if(e.target.id==='catalog-sku-form'){e.preventDefault();submitAdminForm(e.target,'sku')}
 if(e.target.id==='catalog-price-form'){e.preventDefault();submitAdminForm(e.target,'price')}
 if(e.target.id==='subscription-draft-form'){e.preventDefault();submitAdminForm(e.target,'draft')}
});

document.getElementById('lang').addEventListener('change',e=>{state.lang=e.target.value;localStorage.setItem('flex_lang',state.lang);document.documentElement.lang=state.lang==='kg'?'ky':state.lang;render()});
document.getElementById('theme').addEventListener('click',()=>{state.theme=state.theme==='dark'?'light':'dark';localStorage.setItem('flex_theme',state.theme);document.body.classList.toggle('light',state.theme==='light')});
document.getElementById('session-button').addEventListener('click',()=>{
 if(state.status?.identity_ready&&!state.me){
   if(state.identitySession?.user && !state.status?.password_login){
     document.querySelector('[data-identity-logout]')?.click();
     return;
   }
   render();
   document.querySelector('#flex-identity-signin [name=email], #flex-identity-totp [name=code]')?.focus();
   return;
 }
 if(state.me && state.identitySession?.user){
   identityRequest('sign-out',{}).finally(()=>location.assign('/api/auth/logout'));
   return;
 }
 location.assign(state.me?'/api/auth/logout':'/api/auth/login');
});
start();
