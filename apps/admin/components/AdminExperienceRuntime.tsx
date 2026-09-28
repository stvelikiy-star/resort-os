"use client";

import { useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "kz" | "en";

type PinPayload = {
  reservation_id?: string;
  stay_id?: string;
  room_code?: string;
  guest_access_pin: string;
  guest_access_pin_valid_for_hours?: number;
  guest_access_pin_display_once?: boolean;
};

type Phrase = { ru: string; kg: string; en: string };

const STORAGE_KEY = "three-crowns-admin-locale";


const KZ_EXACT: Record<string, string> = {
  "Главная": "Басты бет",
  "Супершахматка": "Супершахматка",
  "CRM / Заявки": "CRM / Өтінімдер",
  "Ресепшен / Брони": "Ресепшен / Броньдар",
  "Сервис гостя": "Қонақ сервисі",
  "Гости / История": "Қонақтар / Тарих",
  "QR номеров": "Бөлме QR",
  "QR зон": "Аймақ QR",
  "Рост / Отзывы": "Өсу / Пікірлер",
  "Выйти": "Шығу",
  "Обновить": "Жаңарту",
  "Брони и проживание": "Броньдар және тұру",
  "Карточка брони": "Бронь карточкасы",
  "Закрыть": "Жабу",
  "Гость": "Қонақ",
  "Без имени": "Аты жоқ",
  "Текущий/рабочий номер": "Ағымдағы бөлме",
  "Проживание": "Тұру",
  "Источник": "Дереккөз",
  "График проживания": "Тұру кестесі",
  "Внутренние платежи по брони": "Бронь бойынша ішкі төлемдер",
  "Стоимость": "Құны",
  "Подтверждено менеджером": "Менеджер растады",
  "Остаток": "Қалдық",
  "Задачи по номерам проживания": "Бөлмелер бойынша тапсырмалар",
  "Журнал действий": "Әрекеттер журналы",
  "Проблемные номера": "Мәселелі бөлмелер",
  "Повторяющиеся поломки": "Қайталанатын ақаулар",
  "Номера с повторными ремонтами": "Қайта жөнделген бөлмелер",
  "Сервис, уборка и ремонты": "Сервис, тазалау және жөндеу",
  "только факты Resort Core": "тек Resort Core деректері",
  "СОЗДАНО": "ҚҰРЫЛДЫ",
  "АКТИВНЫЕ": "БЕЛСЕНДІ",
  "ЗАВЕРШЕНО": "АЯҚТАЛДЫ",
  "СРОЧНО": "ШҰҒЫЛ",
  "ПРОБЛЕМНЫЕ НОМЕРА": "МӘСЕЛЕЛІ БӨЛМЕЛЕР",
  "ПОВТОРЯЮЩИЕСЯ ПОЛОМКИ": "ҚАЙТАЛАНАТЫН АҚАУЛАР",
  "Заезд": "Келу",
  "Выезд": "Шығу",
  "Карточка": "Карточка",
  "Оплата": "Төлем",
  "Даты": "Күндер",
  "Активные": "Белсенді",
  "Заезды сегодня": "Бүгін келетіндер",
  "Выезды сегодня": "Бүгін шығатындар",
  "Ожидают заезд": "Келуді күтуде",
  "Проживают": "Тұрып жатыр",
  "Выехали": "Шығып кетті",
  "Все": "Барлығы",
  "Дата отеля": "Қонақүй күні",
  "Номер на заезд": "Келу бөлмесі",
  "Текущий номер": "Ағымдағы бөлме",
  "Последний номер": "Соңғы бөлме",
  "Оплачено полностью": "Толық төленді",
  "Переселение": "Бөлме ауыстыру",
  "Готов": "Дайын",
  "Нужна уборка": "Тазалау қажет",
  "На проверке": "Тексеруде",
  "Ремонт": "Жөндеу",
  "Не указан": "Көрсетілмеген",
  "ВЛАДЕЛЕЦ": "ИЕСІ",
  "МЕНЕДЖЕР": "МЕНЕДЖЕР",
  "РЕСЕПШЕН": "РЕСЕПШЕН",
  "ГОРНИЧНАЯ": "БӨЛМЕ ҚЫЗМЕТКЕРІ",
  "ТЕХНИК": "ТЕХНИК",
  "РЕСТОРАН": "МЕЙРАМХАНА",
  "МАГАЗИН": "ДҮКЕН",
  "Заявка": "Өтінім",
  "ОПЕРАЦИИ ВЛАДЕЛЬЦА · С НАЧАЛА МЕСЯЦА": "ИЕСІНІҢ ОПЕРАЦИЯЛАРЫ · АЙ БАСЫНАН",
  "СЕРВИС ГОСТЕЙ · СОЗДАНО": "ҚОНАҚ СЕРВИСІ · ҚҰРЫЛДЫ",
  "СЕРВИС ГОСТЕЙ · АКТИВНЫЕ": "ҚОНАҚ СЕРВИСІ · БЕЛСЕНДІ",
  "СРЕДНЕЕ ВРЕМЯ ЗАКРЫТИЯ СЕРВИСНЫХ ЗАЯВОК": "СЕРВИСТІК ӨТІНІМДЕРДІ ЖАБУДЫҢ ОРТАША УАҚЫТЫ",
  "SLA СЕРВИСА ГОСТЕЙ": "ҚОНАҚ СЕРВИСІНІҢ SLA КӨРСЕТКІШІ",
  "УБОРКА · ЗАВЕРШЕНО": "ТАЗАЛАУ · АЯҚТАЛДЫ",
  "УБОРКА · СРОЧНО": "ТАЗАЛАУ · ШҰҒЫЛ",
  "РЕМОНТ · ЗАВЕРШЕНО": "ЖӨНДЕУ · АЯҚТАЛДЫ",
  "НЕ НАСТРОЕНО": "БАПТАЛМАҒАН",
  "ИЗМЕНЕНИЕ ГРАФИКА В PMS": "PMS КЕСТЕСІН ӨЗГЕРТУ",
  "МЕНЕДЖЕР СОЗДАЛ БРОНЬ ИЗ ШАХМАТКИ": "МЕНЕДЖЕР ШАХМАТКАДАН БРОНЬ ҚҰРДЫ",
  "ЗАЕЗД": "КЕЛУ",
  "ВЫЕЗД": "ШЫҒУ",
  "ПЕРЕВЫДАЧА КОДА GUEST OS": "GUEST OS КОДЫН ҚАЙТА БЕРУ",
  "УБОРКА": "ТАЗАЛАУ",
  "РЕМОНТ": "ЖӨНДЕУ",
  "В РАБОТЕ": "ЖҰМЫСТА",
  "НА ПРОВЕРКЕ": "ТЕКСЕРУДЕ",
  "ТЕХНИЧЕСКАЯ БЛОКИРОВКА": "ТЕХНИКАЛЫҚ БЛОК",
  "НЕ УКАЗАНО": "КӨРСЕТІЛМЕГЕН",
  "УСПЕШНО": "СӘТТІ",
  "ОБЫЧНЫЙ": "ҚАЛЫПТЫ",
  "ВЫСОКИЙ": "ЖОҒАРЫ",
  "НИЗКИЙ": "ТӨМЕН",
  "АКТИВНО": "БЕЛСЕНДІ",
  "ГАРАНТИРОВАНА": "КЕПІЛДЕНГЕН",
  "ПРОЖИВАЕТ": "ТҰРЫП ЖАТЫР",
  "ВЫЕХАЛ": "ШЫҒЫП КЕТТІ",
  "ОТМЕНЕНО": "БАС ТАРТЫЛДЫ",
  "НЕ ЗАЕХАЛ": "КЕЛМЕДІ",
};

const exact: Record<string, Phrase> = {
  "OWNER OPERATIONS · MTD": { ru: "ОПЕРАЦИИ ВЛАДЕЛЬЦА · С НАЧАЛА МЕСЯЦА", kg: "ЭЭСИНИН ОПЕРАЦИЯЛАРЫ · АЙ БАШЫНАН", en: "OWNER OPERATIONS · MONTH TO DATE" },
  "GUEST SERVICES · СОЗДАНО": { ru: "СЕРВИС ГОСТЕЙ · СОЗДАНО", kg: "КОНок СЕРВИСИ · ТҮЗҮЛДҮ", en: "GUEST SERVICES · CREATED" },
  "GUEST SERVICES · АКТИВНЫЕ": { ru: "СЕРВИС ГОСТЕЙ · АКТИВНЫЕ", kg: "КОНок СЕРВИСИ · АКТИВДҮҮ", en: "GUEST SERVICES · ACTIVE" },
  "СРЕДНЕЕ ЗАКРЫТИЕ GUEST SERVICES": { ru: "СРЕДНЕЕ ВРЕМЯ ЗАКРЫТИЯ СЕРВИСНЫХ ЗАЯВОК", kg: "СЕРВИСТИК ӨТҮНМДӨРДҮ ЖАБУУНУН ОРТОЧО УБАКТЫСЫ", en: "AVERAGE GUEST SERVICE CLOSE TIME" },
  "SLA GUEST SERVICES": { ru: "SLA СЕРВИСА ГОСТЕЙ", kg: "КОНок СЕРВИСИНИН SLA КӨРСӨТКҮЧҮ", en: "GUEST SERVICES SLA" },
  "HOUSEKEEPING · ЗАВЕРШЕНО": { ru: "УБОРКА · ЗАВЕРШЕНО", kg: "ТАЗАЛОО · БҮТТҮ", en: "HOUSEKEEPING · COMPLETED" },
  "HOUSEKEEPING · СРОЧНО": { ru: "УБОРКА · СРОЧНО", kg: "ТАЗАЛОО · ШАШЫЛЫШ", en: "HOUSEKEEPING · URGENT" },
  "MAINTENANCE · ЗАВЕРШЕНО": { ru: "РЕМОНТ · ЗАВЕРШЕНО", kg: "ОҢДОО · БҮТТҮ", en: "MAINTENANCE · COMPLETED" },
  "NOT_CONFIGURED": { ru: "НЕ НАСТРОЕНО", kg: "ЖӨНДӨЛГӨН ЭМЕС", en: "NOT CONFIGURED" },
  "PMS_SCHEDULE_MUTATION": { ru: "ИЗМЕНЕНИЕ ГРАФИКА В PMS", kg: "PMS ГРАФИГИН ӨЗГӨРТҮҮ", en: "PMS SCHEDULE CHANGE" },
  "MANAGER_CREATE_RESERVATION_FROM_GRID": { ru: "МЕНЕДЖЕР СОЗДАЛ БРОНЬ ИЗ ШАХМАТКИ", kg: "МЕНЕДЖЕР ШАХМАТКАДАН БРОНЬ ТҮЗДҮ", en: "MANAGER CREATED RESERVATION FROM GRID" },
  "CHECK_IN": { ru: "ЗАЕЗД", kg: "КИРҮҮ", en: "CHECK-IN" },
  "CHECK_OUT": { ru: "ВЫЕЗД", kg: "ЧЫГУУ", en: "CHECK-OUT" },
  "GUEST_PIN_REISSUE": { ru: "ПЕРЕВЫДАЧА КОДА GUEST OS", kg: "GUEST OS КОДУН КАЙРА БЕРҮҮ", en: "GUEST OS PIN REISSUED" },
  "HOUSEKEEPING": { ru: "УБОРКА", kg: "ТАЗАЛОО", en: "HOUSEKEEPING" },
  "MAINTENANCE": { ru: "РЕМОНТ", kg: "ОҢДОО", en: "MAINTENANCE" },
  "DONE": { ru: "ЗАВЕРШЕНО", kg: "БҮТТҮ", en: "DONE" },
  "IN_PROGRESS": { ru: "В РАБОТЕ", kg: "АТКАРЫЛУУДА", en: "IN PROGRESS" },
  "IN_INSPECTION": { ru: "НА ПРОВЕРКЕ", kg: "ТЕКШЕРҮҮДӨ", en: "IN INSPECTION" },
  "CLEAN": { ru: "ГОТОВ", kg: "ДАЯР", en: "CLEAN" },
  "DIRTY": { ru: "НУЖНА УБОРКА", kg: "ТАЗАЛОО КЕРЕК", en: "DIRTY" },
  "TECH_BLOCK": { ru: "ТЕХНИЧЕСКАЯ БЛОКИРОВКА", kg: "ТЕХНИКАЛЫК БЛОК", en: "TECH BLOCK" },
  "UNKNOWN": { ru: "НЕ УКАЗАНО", kg: "КӨРСӨТҮЛГӨН ЭМЕС", en: "UNKNOWN" },
  "SUCCESS": { ru: "УСПЕШНО", kg: "ИЙГИЛИКТҮҮ", en: "SUCCESS" },
  "NORMAL": { ru: "ОБЫЧНЫЙ", kg: "КАДИМКИ", en: "NORMAL" },
  "URGENT": { ru: "СРОЧНО", kg: "ШАШЫЛЫШ", en: "URGENT" },
  "HIGH": { ru: "ВЫСОКИЙ", kg: "ЖОГОРКУ", en: "HIGH" },
  "LOW": { ru: "НИЗКИЙ", kg: "ТӨМӨН", en: "LOW" },
  "ACTIVE": { ru: "АКТИВНО", kg: "АКТИВДҮҮ", en: "ACTIVE" },
  "GUARANTEED": { ru: "ГАРАНТИРОВАНА", kg: "КЕПИЛДЕНГЕН", en: "GUARANTEED" },
  "CHECKED_IN": { ru: "ПРОЖИВАЕТ", kg: "ЖАШАП ЖАТАТ", en: "CHECKED IN" },
  "CHECKED_OUT": { ru: "ВЫЕХАЛ", kg: "ЧЫГЫП КЕТТИ", en: "CHECKED OUT" },
  "CANCELLED": { ru: "ОТМЕНЕНО", kg: "ЖОККО ЧЫГАРЫЛДЫ", en: "CANCELLED" },
  "NO_SHOW": { ru: "НЕ ЗАЕХАЛ", kg: "КЕЛГЕН ЖОК", en: "NO SHOW" },
  "OWNER": { ru: "ВЛАДЕЛЕЦ", kg: "ЭЭСИ", en: "OWNER" },
  "MANAGER": { ru: "МЕНЕДЖЕР", kg: "МЕНЕДЖЕР", en: "MANAGER" },
  "RECEPTION": { ru: "РЕСЕПШЕН", kg: "РЕСЕПШЕН", en: "RECEPTION" },
  "MAID": { ru: "ГОРНИЧНАЯ", kg: "БӨЛМӨ КЫЗМАТКЕРИ", en: "MAID" },
  "TECHNICIAN": { ru: "ТЕХНИК", kg: "ТЕХНИК", en: "TECHNICIAN" },
  "DINING_STAFF": { ru: "РЕСТОРАН", kg: "РЕСТОРАН КЫЗМАТКЕРИ", en: "DINING STAFF" },
  "STORE_STAFF": { ru: "МАГАЗИН", kg: "ДҮКӨН КЫЗМАТКЕРИ", en: "STORE STAFF" },
  "Request": { ru: "Заявка", kg: "Өтүнмө", en: "Request" },
};

const common: Phrase[] = [
  { ru: "Главная", kg: "Башкы", en: "Home" },
  { ru: "Супершахматка", kg: "Супершахматка", en: "Super Grid" },
  { ru: "CRM / Заявки", kg: "CRM / Өтүнмөлөр", en: "CRM / Requests" },
  { ru: "Ресепшен / Брони", kg: "Ресепшен / Брондор", en: "Reception / Reservations" },
  { ru: "Сервис гостя", kg: "Конок сервиси", en: "Guest Services" },
  { ru: "Гости / История", kg: "Коноктор / Тарых", en: "Guests / History" },
  { ru: "QR номеров", kg: "Бөлмө QR", en: "Room QR" },
  { ru: "QR зон", kg: "Аймак QR", en: "Zone QR" },
  { ru: "Рост / Отзывы", kg: "Өсүү / Пикирлер", en: "Growth / Reviews" },
  { ru: "Выйти", kg: "Чыгуу", en: "Sign out" },
  { ru: "Обновить", kg: "Жаңыртуу", en: "Refresh" },
  { ru: "Брони и проживание", kg: "Брондор жана жашоо", en: "Reservations and stays" },
  { ru: "Карточка брони", kg: "Бронь карточкасы", en: "Reservation details" },
  { ru: "Закрыть", kg: "Жабуу", en: "Close" },
  { ru: "Гость", kg: "Конок", en: "Guest" },
  { ru: "Без имени", kg: "Аты жок", en: "No name" },
  { ru: "Текущий/рабочий номер", kg: "Учурдагы бөлмө", en: "Current room" },
  { ru: "Проживание", kg: "Жашоо", en: "Stay" },
  { ru: "Источник", kg: "Булак", en: "Source" },
  { ru: "График проживания", kg: "Жашоо графиги", en: "Stay schedule" },
  { ru: "Внутренние платежи по брони", kg: "Бронь боюнча ички төлөмдөр", en: "Reservation payments" },
  { ru: "Стоимость", kg: "Баасы", en: "Total" },
  { ru: "Подтверждено менеджером", kg: "Менеджер ырастаган", en: "Manager confirmed" },
  { ru: "Остаток", kg: "Калдык", en: "Balance" },
  { ru: "Задачи по номерам проживания", kg: "Бөлмө боюнча тапшырмалар", en: "Room tasks" },
  { ru: "Журнал действий", kg: "Аракеттер журналы", en: "Activity log" },
  { ru: "Проблемные номера", kg: "Көйгөйлүү бөлмөлөр", en: "Problem rooms" },
  { ru: "Повторяющиеся поломки", kg: "Кайталанган бузулуулар", en: "Recurring faults" },
  { ru: "Номера с повторными ремонтами", kg: "Кайталанган оңдоосу бар бөлмөлөр", en: "Rooms with repeat repairs" },
  { ru: "Сервис, уборка и ремонты", kg: "Сервис, тазалоо жана оңдоо", en: "Service, housekeeping and maintenance" },
  { ru: "только подтверждённые данные MARINA SMART", kg: "MARINA SMART тастыкталган маалыматтары гана", en: "MARINA SMART verified data only" },
  { ru: "СОЗДАНО", kg: "ТҮЗҮЛДҮ", en: "CREATED" },
  { ru: "АКТИВНЫЕ", kg: "АКТИВДҮҮ", en: "ACTIVE" },
  { ru: "ЗАВЕРШЕНО", kg: "БҮТТҮ", en: "COMPLETED" },
  { ru: "СРОЧНО", kg: "ШАШЫЛЫШ", en: "URGENT" },
  { ru: "ПРОБЛЕМНЫЕ НОМЕРА", kg: "КӨЙГӨЙЛҮҮ БӨЛМӨЛӨР", en: "PROBLEM ROOMS" },
  { ru: "ПОВТОРЯЮЩИЕСЯ ПОЛОМКИ", kg: "КАЙТАЛАНГАН БУЗУЛУУЛАР", en: "RECURRING FAULTS" },
  { ru: "Заезд", kg: "Кирүү", en: "Check-in" },
  { ru: "Выезд", kg: "Чыгуу", en: "Check-out" },
  { ru: "Карточка", kg: "Карточка", en: "Details" },
  { ru: "Оплата", kg: "Төлөм", en: "Payment" },
  { ru: "Даты", kg: "Күндөр", en: "Dates" },
  { ru: "Активные", kg: "Активдүү", en: "Active" },
  { ru: "Заезды сегодня", kg: "Бүгүн кире тургандар", en: "Arrivals today" },
  { ru: "Выезды сегодня", kg: "Бүгүн чыга тургандар", en: "Departures today" },
  { ru: "Ожидают заезд", kg: "Кирүүнү күтөт", en: "Awaiting check-in" },
  { ru: "Проживают", kg: "Жашап жатышат", en: "Checked in" },
  { ru: "Выехали", kg: "Чыгып кетишти", en: "Checked out" },
  { ru: "Все", kg: "Баары", en: "All" },
  { ru: "Дата отеля", kg: "Мейманкана күнү", en: "Hotel date" },
  { ru: "Номер на заезд", kg: "Кирүү бөлмөсү", en: "Arrival room" },
  { ru: "Текущий номер", kg: "Учурдагы бөлмө", en: "Current room" },
  { ru: "Последний номер", kg: "Акыркы бөлмө", en: "Last room" },
  { ru: "Оплачено полностью", kg: "Толук төлөндү", en: "Paid in full" },
  { ru: "Переселение", kg: "Көчүрүү", en: "Room move" },
  { ru: "Готов", kg: "Даяр", en: "Ready" },
  { ru: "Нужна уборка", kg: "Тазалоо керек", en: "Needs cleaning" },
  { ru: "На проверке", kg: "Текшерүүдө", en: "In inspection" },
  { ru: "Ремонт", kg: "Оңдоо", en: "Maintenance" },
  { ru: "Не указан", kg: "Көрсөтүлгөн эмес", en: "Not specified" },
];


/* MARINA_I18N_EXTENDED_V1 */
common.push(
  { ru: "Финансы", kg: "Каржы", en: "Finance" },
  { ru: "Уборка / Ремонт", kg: "Тазалоо / Оңдоо", en: "Housekeeping / Maintenance" },
  { ru: "Отчёты / Аналитика", kg: "Отчёттор / Аналитика", en: "Reports / Analytics" },
  { ru: "Настройки", kg: "Жөндөөлөр", en: "Settings" },
  { ru: "Ещё", kg: "Дагы", en: "More" },
  { ru: "Цены / Сезоны", kg: "Баалар / Сезондор", en: "Rates / Seasons" },
  { ru: "Групповая бронь", kg: "Топтук бронь", en: "Group booking" },
  { ru: "Агенты", kg: "Агенттер", en: "Agents" },
  { ru: "Маркетинг", kg: "Маркетинг", en: "Marketing" },
  { ru: "Питание / Ресторан", kg: "Тамактануу / Ресторан", en: "Dining / Restaurant" },
  { ru: "Настройки услуг", kg: "Кызмат жөндөөлөрү", en: "Service settings" },
  { ru: "Офферы гостю", kg: "Конокко сунуштар", en: "Guest offers" },
  { ru: "Сайт / Контент", kg: "Сайт / Контент", en: "Site / Content" },
  { ru: "Персонал", kg: "Кызматкерлер", en: "Staff" },
  { ru: "Сообщения", kg: "Билдирүүлөр", en: "Messages" },
  { ru: "Войти", kg: "Кирүү", en: "Sign in" },
  { ru: "Входим…", kg: "Кирип жатабыз…", en: "Signing in…" },
  { ru: "Неверный логин или пароль.", kg: "Логин же сырсөз туура эмес.", en: "Invalid username or password." },
  { ru: "Эта роль работает в интерфейсе «Моя смена», а не в Admin/PMS.", kg: "Бул роль Admin/PMS эмес, «Менин нөөмөтүм» интерфейсинде иштейт.", en: "This role works in My Shift, not Admin/PMS." },
  { ru: "Сервис входа MARINA SMART недоступен. Проверьте API.", kg: "MARINA SMART кирүү сервиси жеткиликсиз. API текшериңиз.", en: "MARINA SMART sign-in service is unavailable. Check the API." },
  { ru: "Логотип отеля", kg: "Мейманкана логотиби", en: "Hotel logo" },
  { ru: "Шахматка / Брони", kg: "Шахматка / Брондор", en: "Grid / Reservations" },
  { ru: "Ошибка загрузки", kg: "Жүктөө катасы", en: "Load error" },
  { ru: "Ошибка операции", kg: "Операция катасы", en: "Operation error" },
  { ru: "Сохраняю…", kg: "Сактап жатам…", en: "Saving…" },
  { ru: "Обновляю…", kg: "Жаңыртып жатам…", en: "Refreshing…" },
  { ru: "Проверяю…", kg: "Текшерип жатам…", en: "Checking…" },
  { ru: "Создать", kg: "Түзүү", en: "Create" },
  { ru: "Сохранить", kg: "Сактоо", en: "Save" },
  { ru: "Редактирование", kg: "Түзөтүү", en: "Editing" },
  { ru: "Новый период", kg: "Жаңы мезгил", en: "New period" },
  { ru: "Новый агент", kg: "Жаңы агент", en: "New agent" },
  { ru: "Создать карточку", kg: "Карточка түзүү", en: "Create record" },
  { ru: "Активен", kg: "Активдүү", en: "Active" },
  { ru: "Неактивен", kg: "Активдүү эмес", en: "Inactive" },
  { ru: "Включена", kg: "Күйгүзүлгөн", en: "Enabled" },
  { ru: "Выключена", kg: "Өчүрүлгөн", en: "Disabled" },
  { ru: "Открыт", kg: "Ачык", en: "Open" },
  { ru: "Открыта", kg: "Ачык", en: "Open" },
  { ru: "Решён", kg: "Чечилди", en: "Resolved" },
  { ru: "Архив", kg: "Архив", en: "Archive" },
  { ru: "Новая", kg: "Жаңы", en: "New" },
  { ru: "Рассчитана", kg: "Эсептелди", en: "Quoted" },
  { ru: "На согласовании оплаты", kg: "Төлөм макулдашууда", en: "Awaiting payment approval" },
  { ru: "Забронирована", kg: "Брондолду", en: "Reserved" },
  { ru: "Отклонена", kg: "Четке кагылды", en: "Rejected" },
  { ru: "Истекла", kg: "Мөөнөтү бүттү", en: "Expired" },
  { ru: "Рассчитан", kg: "Эсептелди", en: "Quoted" },
  { ru: "Ждём оплату", kg: "Төлөмдү күтөбүз", en: "Awaiting payment" },
  { ru: "Отменён", kg: "Жокко чыгарылды", en: "Cancelled" },
  { ru: "Отклонён", kg: "Четке кагылды", en: "Rejected" },
  { ru: "Истёк", kg: "Мөөнөтү бүттү", en: "Expired" },
  { ru: "Сайт", kg: "Сайт", en: "Website" },
  { ru: "Телефон", kg: "Телефон", en: "Phone" },
  { ru: "Вручную", kg: "Кол менен", en: "Manual" },
  { ru: "Не определён", kg: "Аныкталган эмес", en: "Not defined" },
  { ru: "Уборка", kg: "Тазалоо", en: "Housekeeping" },
  { ru: "Запрос гостя", kg: "Конок өтүнмөсү", en: "Guest request" },
  { ru: "Срочно", kg: "Шашылыш", en: "Urgent" },
  { ru: "Высокий", kg: "Жогорку", en: "High" },
  { ru: "Обычный", kg: "Кадимки", en: "Normal" },
  { ru: "Низкий", kg: "Төмөн", en: "Low" },
  { ru: "Не назначено", kg: "Дайындалган эмес", en: "Not assigned" },
  { ru: "Номер не назначен", kg: "Бөлмө дайындалган эмес", en: "Room not assigned" },
  { ru: "Завтрак", kg: "Эртең мененки тамак", en: "Breakfast" },
  { ru: "Обед", kg: "Түшкү тамак", en: "Lunch" },
  { ru: "Ужин", kg: "Кечки тамак", en: "Dinner" },
  { ru: "Питание", kg: "Тамактануу", en: "Dining" },
  { ru: "Гость / номер / телефон", kg: "Конок / бөлмө / телефон", en: "Guest / room / phone" },
  { ru: "Выберите гостя", kg: "Конокту тандаңыз", en: "Select guest" },
  { ru: "Сохранить питание", kg: "Тамактанууну сактоо", en: "Save dining" },
  { ru: "Групповые брони", kg: "Топтук брондор", en: "Group reservations" },
  { ru: "Агенты / туроператоры", kg: "Агенттер / туроператорлор", en: "Agents / tour operators" },
  { ru: "Уборка по просьбе гостя", kg: "Коноктун өтүнүчү боюнча тазалоо", en: "Housekeeping by guest request" },
  { ru: "Полотенца", kg: "Сүлгүлөр", en: "Towels" },
  { ru: "Замена белья", kg: "Төшөк жабдыгын алмаштыруу", en: "Linen change" },
  { ru: "Трансфер", kg: "Трансфер", en: "Transfer" },
  { ru: "Сауна", kg: "Сауна", en: "Sauna" },
  { ru: "Бильярд", kg: "Бильярд", en: "Billiards" },
  { ru: "Экскурсии", kg: "Экскурсиялар", en: "Excursions" },
  { ru: "Экскурсии / туры", kg: "Экскурсиялар / турлар", en: "Excursions / tours" },
  { ru: "Администратор", kg: "Администратор", en: "Administrator" },
  { ru: "Горничные", kg: "Бөлмө кызматкерлери", en: "Housekeeping staff" },
  { ru: "Техник", kg: "Техник", en: "Technician" },
  { ru: "Парковка", kg: "Унаа токтотуучу жай", en: "Parking" },
  { ru: "Бассейн", kg: "Бассейн", en: "Pool" },
  { ru: "Пляж", kg: "Пляж", en: "Beach" },
  { ru: "Санузел", kg: "Санузел", en: "Restroom" },
  { ru: "Коридор / общая зона", kg: "Коридор / жалпы аймак", en: "Corridor / common area" },
  { ru: "Другая зона", kg: "Башка аймак", en: "Other area" },
  { ru: "Технический блок", kg: "Техникалык блок", en: "Technical block" },
  { ru: "Ручной блок", kg: "Кол менен блок", en: "Manual block" },
  { ru: "✓ Номер готов", kg: "✓ Бөлмө даяр", en: "✓ Room ready" },
  { ru: "Можно заселять", kg: "Жайгаштырууга болот", en: "Ready for check-in" },
  { ru: "Нужна подготовка", kg: "Даярдоо керек", en: "Preparation required" },
  { ru: "На проверку", kg: "Текшерүүгө", en: "Send to inspection" },
  { ru: "Ждёт контроля", kg: "Текшерүүнү күтөт", en: "Awaiting inspection" },
  { ru: "Ремонт / блок", kg: "Оңдоо / блок", en: "Maintenance / block" },
  { ru: "Не заселять", kg: "Жайгаштырбоо", en: "Do not check in" },
  { ru: "Закрыть номер", kg: "Бөлмөнү жабуу", en: "Close room" },
  { ru: "Фильтры шахматки", kg: "Шахматка чыпкалары", en: "Grid filters" },
  { ru: "Быстрые режимы ресепшена", kg: "Ресепшендин тез режимдери", en: "Reception quick modes" },
  { ru: "Легенда шахматки", kg: "Шахматка легендасы", en: "Grid legend" },
  { ru: "Сводка по номерам", kg: "Бөлмөлөр боюнча жыйынтык", en: "Room summary" },
  { ru: "Все номера", kg: "Бардык бөлмөлөр", en: "All rooms" },
  { ru: "Свободны сегодня", kg: "Бүгүн бош", en: "Available today" },
  { ru: "Блок", kg: "Блок", en: "Block" },
  { ru: "Подключение", kg: "Туташуу", en: "Connection" },
  { ru: "Realtime подключён", kg: "Realtime туташты", en: "Realtime connected" },
  { ru: "Realtime подключается…", kg: "Realtime туташууда…", en: "Realtime connecting…" },
  { ru: "HTTP подключён", kg: "HTTP туташты", en: "HTTP connected" },
  { ru: "HTTP режим", kg: "HTTP режими", en: "HTTP mode" },
  { ru: "Назад 7 дней", kg: "7 күн артка", en: "Back 7 days" },
  { ru: "Вперёд 7 дней", kg: "7 күн алдыга", en: "Forward 7 days" },
  { ru: "Обновить шахматку", kg: "Шахматканы жаңыртуу", en: "Refresh grid" },
  { ru: "Операционный центр", kg: "Операциялык борбор", en: "Operations center" },
  { ru: "Скрыть операционный центр", kg: "Операциялык борборду жашыруу", en: "Hide operations center" },
  { ru: "Скрыть расширенные операции", kg: "Кеңейтилген операцияларды жашыруу", en: "Hide advanced operations" },
  { ru: "Перенос / Split Stay", kg: "Көчүрүү / Split Stay", en: "Move / Split Stay" },
  { ru: "Фильтр по агенту", kg: "Агент боюнча чыпка", en: "Agent filter" },
  { ru: "Проживание оплачено", kg: "Жашоо төлөндү", en: "Stay paid" },
  { ru: "Гарантирована", kg: "Кепилденген", en: "Guaranteed" },
  { ru: "Выезд завершён", kg: "Чыгуу аяктады", en: "Checked out" },
  { ru: "Выполнено", kg: "Аткарылды", en: "Completed" },
  { ru: "Создана заявка гостя", kg: "Конок өтүнмөсү түзүлдү", en: "Guest request created" },
  { ru: "Заявка выполнена", kg: "Өтүнмө аткарылды", en: "Request completed" },
  { ru: "Заявка отменена", kg: "Өтүнмө жокко чыгарылды", en: "Request cancelled" },
  { ru: "Фактическое назначение номера изменено", kg: "Бөлмөнүн фактикалык дайындоосу өзгөрдү", en: "Actual room assignment changed" },
  { ru: "Владелец", kg: "Ээси", en: "Owner" },
  { ru: "Агентство / туроператор", kg: "Агенттик / туроператор", en: "Agency / tour operator" },
  { ru: "Горничная", kg: "Бөлмө кызматкери", en: "Housekeeper" },
  { ru: "Магазин", kg: "Дүкөн", en: "Store" },
  { ru: "Столовая / ресторан", kg: "Ашкана / ресторан", en: "Dining hall / restaurant" },
  { ru: "Контент-менеджер", kg: "Контент-менеджер", en: "Content manager" },
  { ru: "Создать сотрудника", kg: "Кызматкер түзүү", en: "Create staff member" },
  { ru: "Доступ отключён", kg: "Кирүү өчүрүлгөн", en: "Access disabled" },
  { ru: "привязан", kg: "байланган", en: "linked" },
  { ru: "не привязан", kg: "байланган эмес", en: "not linked" },
  { ru: "Имя, логин, Telegram…", kg: "Аты, логин, Telegram…", en: "Name, username, Telegram…" },
  { ru: "7 дней", kg: "7 күн", en: "7 days" },
  { ru: "Этот месяц", kg: "Бул ай", en: "This month" },
  { ru: "Прошлый месяц", kg: "Өткөн ай", en: "Last month" },
  { ru: "Сезон", kg: "Сезон", en: "Season" },
  { ru: "Год", kg: "Жыл", en: "Year" },
  { ru: "Печать / PDF", kg: "Басып чыгаруу / PDF", en: "Print / PDF" },
  { ru: "Сравнение", kg: "Салыштыруу", en: "Comparison" },
  { ru: "Динамика", kg: "Динамика", en: "Trend" },
  { ru: "Загрузка по дням", kg: "Күндөр боюнча жүктөлүү", en: "Occupancy by day" },
  { ru: "Продажи", kg: "Сатуулар", en: "Sales" },
  { ru: "CRM-воронка", kg: "CRM-воронка", en: "CRM funnel" },
  { ru: "Операции", kg: "Операциялар", en: "Operations" },
  { ru: "Уборка и ремонт", kg: "Тазалоо жана оңдоо", en: "Housekeeping and maintenance" },
  { ru: "Номерной фонд", kg: "Бөлмө фонду", en: "Room inventory" },
  { ru: "Эффективность категорий", kg: "Категориялардын натыйжалуулугу", en: "Category performance" },
  { ru: "Источники", kg: "Булактар", en: "Sources" },
  { ru: "Каналы броней", kg: "Бронь каналдары", en: "Reservation channels" },
  { ru: "Контроль денег", kg: "Акчаны көзөмөлдөө", en: "Money control" },
  { ru: "Текущая задолженность", kg: "Учурдагы карыз", en: "Current debt" },
  { ru: "До заезда", kg: "Кирүүгө чейин", en: "Before arrival" },
  { ru: "Выехал с долгом", kg: "Карыз менен чыкты", en: "Checked out with debt" },
  { ru: "Период внутреннего отчёта", kg: "Ички отчёт мезгили", en: "Internal report period" },
  { ru: "Финансовые права", kg: "Каржылык укуктар", en: "Financial permissions" },
  { ru: "Оплаты — только просмотр", kg: "Төлөмдөр — көрүү гана", en: "Payments — view only" },
  { ru: "Принять оплату", kg: "Төлөмдү кабыл алуу", en: "Record payment" },
  { ru: "Записать факт оплаты", kg: "Төлөм фактын жазуу", en: "Record payment received" },
  { ru: "Фактический способ оплаты", kg: "Фактикалык төлөм ыкмасы", en: "Actual payment method" },
  { ru: "Переплата", kg: "Ашыкча төлөм", en: "Overpayment" },
  { ru: "Наличные", kg: "Накталай", en: "Cash" },
  { ru: "Карта / POS", kg: "Карта / POS", en: "Card / POS" },
  { ru: "QR / безнал", kg: "QR / накталай эмес", en: "QR / cashless" },
  { ru: "Банковский перевод", kg: "Банк которуусу", en: "Bank transfer" },
  { ru: "Другое", kg: "Башка", en: "Other" },
  { ru: "Ротация", kg: "Алмаштыруу", en: "Rotate" },
  { ru: "Выпустить", kg: "Чыгаруу", en: "Issue" },
  { ru: "НЕ ВЫПУЩЕН", kg: "ЧЫГАРЫЛГАН ЭМЕС", en: "NOT ISSUED" },
  { ru: "Русский", kg: "Орусча", en: "Russian" },
  { ru: "Кыргызча", kg: "Кыргызча", en: "Kyrgyz" },
  { ru: "Первый экран", kg: "Биринчи экран", en: "Hero section" },
  { ru: "Главный заголовок", kg: "Негизги аталыш", en: "Main heading" },
  { ru: "Описание", kg: "Сүрөттөмө", en: "Description" },
  { ru: "Главная кнопка", kg: "Негизги баскыч", en: "Primary button" },
  { ru: "Вторая кнопка", kg: "Экинчи баскыч", en: "Secondary button" },
  { ru: "Преимущества", kg: "Артыкчылыктар", en: "Advantages" },
  { ru: "Галерея", kg: "Галерея", en: "Gallery" },
  { ru: "Главные блоки", kg: "Негизги блоктор", en: "Main sections" },
  { ru: "Номерной фонд", kg: "Бөлмө фонду", en: "Room inventory" },
  { ru: "Загружаю…", kg: "Жүктөп жатам…", en: "Loading…" },
  { ru: "Выбрать файл", kg: "Файл тандоо", en: "Choose file" },
  { ru: "Сохранить черновик", kg: "Черновикти сактоо", en: "Save draft" },
  { ru: "Публикую…", kg: "Жарыялап жатам…", en: "Publishing…" },
);

const KZ_EXTRA: Record<string, string> = {
  "Финансы": "Қаржы",
  "Уборка / Ремонт": "Тазалау / Жөндеу",
  "Отчёты / Аналитика": "Есептер / Аналитика",
  "Настройки": "Баптаулар",
  "Ещё": "Тағы",
  "Цены / Сезоны": "Бағалар / Маусымдар",
  "Групповая бронь": "Топтық бронь",
  "Агенты": "Агенттер",
  "Маркетинг": "Маркетинг",
  "Питание / Ресторан": "Тамақтану / Мейрамхана",
  "Настройки услуг": "Қызмет баптаулары",
  "Офферы гостю": "Қонақ ұсыныстары",
  "Сайт / Контент": "Сайт / Контент",
  "Персонал": "Қызметкерлер",
  "Сообщения": "Хабарламалар",
  "Войти": "Кіру",
  "Входим…": "Кіріп жатырмыз…",
  "Неверный логин или пароль.": "Логин немесе құпиясөз қате.",
  "Эта роль работает в интерфейсе «Моя смена», а не в Admin/PMS.": "Бұл рөл Admin/PMS емес, «Менің ауысымым» интерфейсінде жұмыс істейді.",
  "Сервис входа MARINA SMART недоступен. Проверьте API.": "MARINA SMART кіру сервисі қолжетімсіз. API тексеріңіз.",
  "Логотип отеля": "Қонақүй логотипі",
  "Шахматка / Брони": "Шахматка / Броньдар",
  "Ошибка загрузки": "Жүктеу қатесі",
  "Ошибка операции": "Операция қатесі",
  "Сохраняю…": "Сақтап жатырмын…",
  "Обновляю…": "Жаңартып жатырмын…",
  "Проверяю…": "Тексеріп жатырмын…",
  "Создать": "Құру",
  "Сохранить": "Сақтау",
  "Редактирование": "Өңдеу",
  "Новый период": "Жаңа кезең",
  "Новый агент": "Жаңа агент",
  "Создать карточку": "Карточка құру",
  "Активен": "Белсенді",
  "Неактивен": "Белсенді емес",
  "Включена": "Қосылған",
  "Выключена": "Өшірілген",
  "Открыт": "Ашық",
  "Открыта": "Ашық",
  "Решён": "Шешілді",
  "Архив": "Мұрағат",
  "Новая": "Жаңа",
  "Рассчитана": "Есептелді",
  "На согласовании оплаты": "Төлем келісуде",
  "Забронирована": "Броньдалды",
  "Отклонена": "Қабылданбады",
  "Истекла": "Мерзімі өтті",
  "Рассчитан": "Есептелді",
  "Ждём оплату": "Төлемді күтеміз",
  "Отменён": "Бас тартылды",
  "Отклонён": "Қабылданбады",
  "Истёк": "Мерзімі өтті",
  "Сайт": "Сайт",
  "Телефон": "Телефон",
  "Вручную": "Қолмен",
  "Не определён": "Анықталмаған",
  "Уборка": "Тазалау",
  "Запрос гостя": "Қонақ өтінімі",
  "Срочно": "Шұғыл",
  "Высокий": "Жоғары",
  "Обычный": "Қалыпты",
  "Низкий": "Төмен",
  "Не назначено": "Тағайындалмаған",
  "Номер не назначен": "Бөлме тағайындалмаған",
  "Завтрак": "Таңғы ас",
  "Обед": "Түскі ас",
  "Ужин": "Кешкі ас",
  "Питание": "Тамақтану",
  "Гость / номер / телефон": "Қонақ / бөлме / телефон",
  "Выберите гостя": "Қонақты таңдаңыз",
  "Сохранить питание": "Тамақтануды сақтау",
  "Групповые брони": "Топтық броньдар",
  "Агенты / туроператоры": "Агенттер / туроператорлар",
  "Уборка по просьбе гостя": "Қонақ өтініші бойынша тазалау",
  "Полотенца": "Сүлгілер",
  "Замена белья": "Төсек-орынды ауыстыру",
  "Трансфер": "Трансфер",
  "Сауна": "Сауна",
  "Бильярд": "Бильярд",
  "Экскурсии": "Экскурсиялар",
  "Экскурсии / туры": "Экскурсиялар / турлар",
  "Администратор": "Әкімші",
  "Горничные": "Бөлме қызметкерлері",
  "Техник": "Техник",
  "Парковка": "Тұрақ",
  "Бассейн": "Бассейн",
  "Пляж": "Жағажай",
  "Санузел": "Санторап",
  "Коридор / общая зона": "Дәліз / ортақ аймақ",
  "Другая зона": "Басқа аймақ",
  "Технический блок": "Техникалық блок",
  "Ручной блок": "Қолмен блок",
  "✓ Номер готов": "✓ Бөлме дайын",
  "Можно заселять": "Қоныстандыруға болады",
  "Нужна подготовка": "Дайындау қажет",
  "На проверку": "Тексеруге",
  "Ждёт контроля": "Бақылауды күтуде",
  "Ремонт / блок": "Жөндеу / блок",
  "Не заселять": "Қоныстандырмау",
  "Закрыть номер": "Бөлмені жабу",
  "Фильтры шахматки": "Шахматка сүзгілері",
  "Быстрые режимы ресепшена": "Ресепшеннің жылдам режимдері",
  "Легенда шахматки": "Шахматка түсіндірмесі",
  "Сводка по номерам": "Бөлмелер бойынша жиынтық",
  "Все номера": "Барлық бөлмелер",
  "Свободны сегодня": "Бүгін бос",
  "Блок": "Блок",
  "Подключение": "Қосылу",
  "Realtime подключён": "Realtime қосылды",
  "Realtime подключается…": "Realtime қосылып жатыр…",
  "HTTP подключён": "HTTP қосылды",
  "HTTP режим": "HTTP режимі",
  "Назад 7 дней": "7 күн артқа",
  "Вперёд 7 дней": "7 күн алға",
  "Обновить шахматку": "Шахматканы жаңарту",
  "Операционный центр": "Операциялық орталық",
  "Скрыть операционный центр": "Операциялық орталықты жасыру",
  "Скрыть расширенные операции": "Кеңейтілген операцияларды жасыру",
  "Перенос / Split Stay": "Ауыстыру / Split Stay",
  "Фильтр по агенту": "Агент бойынша сүзгі",
  "Проживание оплачено": "Тұру төленді",
  "Гарантирована": "Кепілденген",
  "Выезд завершён": "Шығу аяқталды",
  "Выполнено": "Орындалды",
  "Создана заявка гостя": "Қонақ өтінімі құрылды",
  "Заявка выполнена": "Өтінім орындалды",
  "Заявка отменена": "Өтінімнен бас тартылды",
  "Фактическое назначение номера изменено": "Бөлменің нақты тағайындалуы өзгерді",
  "Владелец": "Иесі",
  "Агентство / туроператор": "Агенттік / туроператор",
  "Горничная": "Бөлме қызметкері",
  "Магазин": "Дүкен",
  "Столовая / ресторан": "Асхана / мейрамхана",
  "Контент-менеджер": "Контент-менеджер",
  "Создать сотрудника": "Қызметкер құру",
  "Доступ отключён": "Қолжетімділік өшірілген",
  "привязан": "байланыстырылған",
  "не привязан": "байланыстырылмаған",
  "Имя, логин, Telegram…": "Аты, логин, Telegram…",
  "7 дней": "7 күн",
  "Этот месяц": "Осы ай",
  "Прошлый месяц": "Өткен ай",
  "Сезон": "Маусым",
  "Год": "Жыл",
  "Печать / PDF": "Басып шығару / PDF",
  "Сравнение": "Салыстыру",
  "Динамика": "Динамика",
  "Загрузка по дням": "Күндер бойынша жүктеме",
  "Продажи": "Сатылымдар",
  "CRM-воронка": "CRM-воронка",
  "Операции": "Операциялар",
  "Уборка и ремонт": "Тазалау және жөндеу",
  "Номерной фонд": "Бөлме қоры",
  "Эффективность категорий": "Санаттар тиімділігі",
  "Источники": "Дереккөздер",
  "Каналы броней": "Бронь арналары",
  "Контроль денег": "Ақшаны бақылау",
  "Текущая задолженность": "Ағымдағы берешек",
  "До заезда": "Келуге дейін",
  "Выехал с долгом": "Қарызбен шықты",
  "Период внутреннего отчёта": "Ішкі есеп кезеңі",
  "Финансовые права": "Қаржылық құқықтар",
  "Оплаты — только просмотр": "Төлемдер — тек қарау",
  "Принять оплату": "Төлемді қабылдау",
  "Записать факт оплаты": "Төлем фактісін жазу",
  "Фактический способ оплаты": "Нақты төлем тәсілі",
  "Переплата": "Артық төлем",
  "Наличные": "Қолма-қол",
  "Карта / POS": "Карта / POS",
  "QR / безнал": "QR / қолма-қолсыз",
  "Банковский перевод": "Банк аударымы",
  "Другое": "Басқа",
  "Ротация": "Ауыстыру",
  "Выпустить": "Шығару",
  "НЕ ВЫПУЩЕН": "ШЫҒАРЫЛМАҒАН",
  "Русский": "Орысша",
  "Кыргызча": "Қырғызша",
  "Первый экран": "Бірінші экран",
  "Главный заголовок": "Негізгі тақырып",
  "Описание": "Сипаттама",
  "Главная кнопка": "Негізгі батырма",
  "Вторая кнопка": "Екінші батырма",
  "Преимущества": "Артықшылықтар",
  "Галерея": "Галерея",
  "Главные блоки": "Негізгі блоктар",
  "Номерной фонд": "Бөлме қоры",
  "Загружаю…": "Жүктеп жатырмын…",
  "Выбрать файл": "Файл таңдау",
  "Сохранить черновик": "Нобайды сақтау",
  "Публикую…": "Жариялап жатырмын…",
};

const phraseIndex = new Map<string, Phrase>();
for (const phrase of common) {
  phraseIndex.set(phrase.ru, phrase);
  phraseIndex.set(phrase.kg, phrase);
  phraseIndex.set(phrase.en, phrase);
}
for (const [key, phrase] of Object.entries(exact)) {
  phraseIndex.set(key, phrase);
  phraseIndex.set(phrase.ru, phrase);
  phraseIndex.set(phrase.kg, phrase);
  phraseIndex.set(phrase.en, phrase);
}

const tokenReplacements: Record<Locale, Array<[RegExp, string]>> = {
  ru: [
    [/\bGUEST SERVICES\b/g, "СЕРВИС ГОСТЕЙ"],
    [/\bHOUSEKEEPING\b/g, "УБОРКА"],
    [/\bMAINTENANCE\b/g, "РЕМОНТ"],
    [/\bNOT_CONFIGURED\b/g, "НЕ НАСТРОЕНО"],
    [/\bOWNER OPERATIONS\b/g, "ОПЕРАЦИИ ВЛАДЕЛЬЦА"],
    [/\bMTD\b/g, "С НАЧАЛА МЕСЯЦА"],
    [/\bDONE\b/g, "ЗАВЕРШЕНО"],
    [/\bIN_PROGRESS\b/g, "В РАБОТЕ"],
    [/\bIN_INSPECTION\b/g, "НА ПРОВЕРКЕ"],
    [/\bSUCCESS\b/g, "УСПЕШНО"],
    [/\bNORMAL\b/g, "ОБЫЧНЫЙ"],
  ],
  kg: [
    [/\bGUEST SERVICES\b/g, "КОНок СЕРВИСИ"],
    [/\bHOUSEKEEPING\b/g, "ТАЗАЛОО"],
    [/\bMAINTENANCE\b/g, "ОҢДОО"],
    [/\bNOT_CONFIGURED\b/g, "ЖӨНДӨЛГӨН ЭМЕС"],
    [/\bOWNER OPERATIONS\b/g, "ЭЭСИНИН ОПЕРАЦИЯЛАРЫ"],
    [/\bMTD\b/g, "АЙ БАШЫНАН"],
    [/\bDONE\b/g, "БҮТТҮ"],
    [/\bIN_PROGRESS\b/g, "АТКАРЫЛУУДА"],
    [/\bIN_INSPECTION\b/g, "ТЕКШЕРҮҮДӨ"],
    [/\bSUCCESS\b/g, "ИЙГИЛИКТҮҮ"],
    [/\bNORMAL\b/g, "КАДИМКИ"],
  ],
  kz: [
    [/\bGUEST SERVICES\b/g, "ҚОНАҚ СЕРВИСІ"],
    [/\bHOUSEKEEPING\b/g, "ТАЗАЛАУ"],
    [/\bMAINTENANCE\b/g, "ЖӨНДЕУ"],
    [/\bNOT_CONFIGURED\b/g, "БАПТАЛМАҒАН"],
    [/\bOWNER OPERATIONS\b/g, "ИЕСІНІҢ ОПЕРАЦИЯЛАРЫ"],
    [/\bMTD\b/g, "АЙ БАСЫНАН"],
    [/\bDONE\b/g, "АЯҚТАЛДЫ"],
    [/\bIN_PROGRESS\b/g, "ЖҰМЫСТА"],
    [/\bIN_INSPECTION\b/g, "ТЕКСЕРУДЕ"],
    [/\bSUCCESS\b/g, "СӘТТІ"],
    [/\bNORMAL\b/g, "ҚАЛЫПТЫ"],
  ],
  en: [
    [/\bСЕРВИС ГОСТЕЙ\b/g, "GUEST SERVICES"],
    [/\bУБОРКА\b/g, "HOUSEKEEPING"],
    [/\bРЕМОНТ\b/g, "MAINTENANCE"],
    [/\bНЕ НАСТРОЕНО\b/g, "NOT CONFIGURED"],
    [/\bОПЕРАЦИИ ВЛАДЕЛЬЦА\b/g, "OWNER OPERATIONS"],
    [/\bС НАЧАЛА МЕСЯЦА\b/g, "MONTH TO DATE"],
    [/\bЗАВЕРШЕНО\b/g, "COMPLETED"],
    [/\bВ РАБОТЕ\b/g, "IN PROGRESS"],
    [/\bНА ПРОВЕРКЕ\b/g, "IN INSPECTION"],
    [/\bУСПЕШНО\b/g, "SUCCESS"],
    [/\bОБЫЧНЫЙ\b/g, "NORMAL"],
  ],
};

function translateText(source: string, locale: Locale): string {
  const trimmed = source.trim();
  if (!trimmed) return source;
  const direct = phraseIndex.get(trimmed);
  let translated: string;
  if (locale === "kz") {
    const canonicalRu = direct?.ru ?? exact[trimmed]?.ru ?? trimmed;
    translated = KZ_EXACT[canonicalRu] ?? KZ_EXTRA[canonicalRu] ?? KZ_EXACT[trimmed] ?? KZ_EXTRA[trimmed] ?? trimmed;
  } else {
    translated = direct ? direct[locale] : trimmed;
    if (!direct && exact[trimmed]) translated = exact[trimmed][locale];
  }
  for (const [pattern, replacement] of tokenReplacements[locale]) {
    translated = translated.replace(pattern, replacement);
  }
  const prefix = source.slice(0, source.indexOf(trimmed));
  const suffix = source.slice(source.indexOf(trimmed) + trimmed.length);
  return `${prefix}${translated}${suffix}`;
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

export default function AdminExperienceRuntime() {
  const [locale, setLocale] = useState<Locale>("ru");
  const [pin, setPin] = useState<PinPayload | null>(null);
  const [currentReservationId, setCurrentReservationId] = useState<string | null>(null);
  const [currentReservationCheckedIn, setCurrentReservationCheckedIn] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [pinBusy, setPinBusy] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const originalText = useMemo(() => new WeakMap<Text, { source: string; rendered: string }>(), []);
  const originalAttrs = useMemo(() => new WeakMap<Element, Map<string, { source: string; rendered: string }>>(), []);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "ru" || stored === "kg" || stored === "kz" || stored === "en") setLocale(stored);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale === "kg" ? "ky" : locale === "kz" ? "kk" : locale;
  }, [locale]);

  useEffect(() => {
    function translateNode(node: Node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node as Text;
        const current = text.nodeValue || "";
        if (!current.trim()) return;
        const previous = originalText.get(text);
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translateText(source, locale);
        originalText.set(text, { source, rendered });
        if (current !== rendered) text.nodeValue = rendered;
        return;
      }
      if (!(node instanceof Element)) return;
      if (node.matches("script,style,code,pre,[data-i18n-skip]")) return;
      for (const attr of ["placeholder", "title", "aria-label"]) {
        if (!node.hasAttribute(attr)) continue;
        const current = node.getAttribute(attr) || "";
        const attrMap = originalAttrs.get(node) || new Map<string, { source: string; rendered: string }>();
        const previous = attrMap.get(attr);
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translateText(source, locale);
        attrMap.set(attr, { source, rendered });
        originalAttrs.set(node, attrMap);
        if (current !== rendered) node.setAttribute(attr, rendered);
      }
      for (const child of Array.from(node.childNodes)) translateNode(child);
    }

    translateNode(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") translateNode(mutation.target);
        for (const added of Array.from(mutation.addedNodes)) translateNode(added);
      }
      setDetailOpen(Boolean(document.querySelector(".reservation-detail")));
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setDetailOpen(Boolean(document.querySelector(".reservation-detail")));
    return () => observer.disconnect();
  }, [locale, originalAttrs, originalText]);

  useEffect(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const response = await originalFetch(input, init);

      if (/\/core\/api\/v1\/admin\/stays\/reservations\/[0-9a-f-]+\/check-in(?:\?|$)/i.test(url) && response.ok) {
        void response.clone().json().then((body) => {
          if (body?.guest_access_pin) {
            setPin(body as PinPayload);
            setPinError(null);
          }
        }).catch(() => undefined);
      }

      const detailMatch = url.match(/\/core\/api\/v1\/admin\/booking\/reservations\/([0-9a-f-]+)(?:\?|$)/i);
      if (detailMatch && response.ok) {
        void response.clone().json().then((body) => {
          setCurrentReservationId(detailMatch[1]);
          setCurrentReservationCheckedIn(body?.reservation?.status === "CHECKED_IN");
        }).catch(() => undefined);
      }
      return response;
    };
    return () => { window.fetch = originalFetch; };
  }, []);

  async function reissuePin() {
    if (!currentReservationId) return;
    if (!window.confirm(locale === "en" ? "Issue a new Guest OS PIN? The previous PIN will stop working." : locale === "kg" ? "Жаңы Guest OS кодун бересизби? Мурунку код иштебей калат." : locale === "kz" ? "Жаңа Guest OS PIN кодын бересіз бе? Алдыңғы PIN жұмысын тоқтатады." : "Выдать новый код Guest OS? Предыдущий PIN перестанет работать.")) return;
    setPinBusy(true);
    setPinError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-access/reservations/${currentReservationId}/pin`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "PIN_REISSUE_FAILED");
      setPin(body as PinPayload);
    } catch (error) {
      setPinError(error instanceof Error ? error.message : "PIN_REISSUE_FAILED");
    } finally {
      setPinBusy(false);
    }
  }

  async function copyPin() {
    if (!pin?.guest_access_pin) return;
    await navigator.clipboard.writeText(pin.guest_access_pin);
  }

  const labels = {
    ru: { language: "Язык", reissue: "Новый код Guest OS", title: "Код Guest OS выдан", room: "Номер", code: "Код гостя", valid: "Действует 24 часа", once: "Показывается только один раз. Передайте код гостю сейчас.", copy: "Скопировать код", close: "Закрыть", error: "Не удалось выдать новый код" },
    kg: { language: "Тил", reissue: "Жаңы Guest OS коду", title: "Guest OS коду берилди", room: "Бөлмө", code: "Конок коду", valid: "24 саат жарактуу", once: "Бир гана жолу көрсөтүлөт. Кодду конокко азыр бериңиз.", copy: "Кодду көчүрүү", close: "Жабуу", error: "Жаңы кодду берүү мүмкүн болгон жок" },
    kz: { language: "Тіл", reissue: "Жаңа Guest OS PIN", title: "Guest OS PIN берілді", room: "Бөлме", code: "Қонақ PIN", valid: "24 сағат жарамды", once: "Тек бір рет көрсетіледі. PIN кодын қонаққа қазір беріңіз.", copy: "PIN көшіру", close: "Жабу", error: "Жаңа PIN беру мүмкін болмады" },
    en: { language: "Language", reissue: "New Guest OS PIN", title: "Guest OS PIN issued", room: "Room", code: "Guest PIN", valid: "Valid for 24 hours", once: "Shown only once. Give this PIN to the guest now.", copy: "Copy PIN", close: "Close", error: "Could not issue a new PIN" },
  }[locale];

  return <>
    <div className="admin-locale-switcher" data-i18n-skip>
      <span>{labels.language}</span>
      {(["ru", "kg", "kz", "en"] as Locale[]).map((value) => <button key={value} type="button" className={locale === value ? "active" : ""} onClick={() => setLocale(value)}>{value.toUpperCase()}</button>)}
    </div>

    {detailOpen && currentReservationCheckedIn && <button type="button" className="guest-pin-reissue" data-i18n-skip onClick={reissuePin} disabled={pinBusy}>{pinBusy ? "…" : labels.reissue}</button>}
    {pinError && <div className="guest-pin-runtime-error" data-i18n-skip>{labels.error}: {pinError}</div>}

    {pin && <div className="guest-pin-backdrop" data-i18n-skip role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setPin(null); }}>
      <section className="guest-pin-modal" role="dialog" aria-modal="true" aria-label={labels.title}>
        <p>{labels.title}</p>
        <h2>{pin.room_code ? `${labels.room} ${pin.room_code}` : labels.code}</h2>
        <div className="guest-pin-value">{pin.guest_access_pin}</div>
        <strong>{labels.valid}</strong>
        <small>{labels.once}</small>
        <div className="guest-pin-actions"><button type="button" onClick={copyPin}>{labels.copy}</button><button type="button" onClick={() => setPin(null)}>{labels.close}</button></div>
      </section>
    </div>}
  </>;
}
