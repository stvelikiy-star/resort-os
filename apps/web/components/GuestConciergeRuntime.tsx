"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { MARINA_GUEST_LOCALES, MarinaGuestLocale, marinaGuestIntlLocale, useMarinaGuestLocale } from "../lib/marinaGuestLocale";

type Locale = MarinaGuestLocale;
type RequestCode = "HOUSEKEEPING" | "TOWELS" | "LINEN" | "MAINTENANCE" | "TRANSFER" | "MEALS" | "PARKING" | "SAUNA" | "BILLIARDS" | "EXCURSIONS" | "ADMIN";
type RequestStatus = "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";

type GuestContext = {
  qr_valid: boolean;
  authenticated: boolean;
  verification_required: boolean;
  active_stay: boolean;
  room: { code: string; name: string; room_type_name: string };
  guest: { first_name: string } | null;
  stay: { check_in: string; check_out: string } | null;
};

type GuestRequest = {
  id: string;
  request_code: string;
  status: RequestStatus;
  description?: string | null;
  service_date?: string | null;
  service_time?: string | null;
  created_at: string;
};

type Service = { code: RequestCode; icon: string; title: string; note: string };

const HOTEL_PHONE_E164 = "+996501772233";
const HOTEL_WHATSAPP_URL = "https://wa.me/996501772233";

const COPY = {
  ru: {
    property: "AK BERMET",
    product: "MARINA SMART · гостевой кабинет",
    language: "Язык",
    loading: "Открываем цифровой консьерж…",
    invalidTitle: "Код номера недоступен",
    invalidText: "Код не найден или был заменён. Обратитесь на ресепшен.",
    noStayTitle: "Номер готов к следующему заезду",
    noStayText: "Сейчас за этим номером нет активного проживания.",
    room: "Номер",
    verifyTitle: "Подтвердите проживание",
    verifyText: "Введите шестизначный код, который вы получили на ресепшене при заселении.",
    pin: "Код гостя",
    open: "Открыть кабинет",
    checking: "Проверяем…",
    wrong: "Код не подошёл. Проверьте цифры или обратитесь на ресепшен.",
    expired: "Срок действия кода закончился. Попросите ресепшен выдать новый код.",
    limited: "Слишком много попыток. Попробуйте позже или обратитесь на ресепшен.",
    error: "Не удалось загрузить кабинет. Проверьте соединение и попробуйте снова.",
    retry: "Повторить",
    hello: "Добро пожаловать",
    stay: "Ваше проживание",
    from: "с",
    to: "по",
    checkout: "Выезд до 11:00",
    quick: "Что нужно сейчас?",
    quickNote: "Большинство услуг можно запросить за несколько нажатий.",
    myRequests: "Мои заявки",
    noRequests: "Заявок пока нет.",
    refresh: "Обновить",
    newRequest: "Новая заявка",
    service: "Услуга",
    date: "Дата",
    time: "Время",
    comment: "Комментарий",
    commentPlaceholder: "Уточните детали, если нужно",
    send: "Отправить",
    sending: "Отправляем…",
    sent: "Заявка отправлена. Статус появится в разделе «Мои заявки».",
    cancel: "Отменить",
    close: "Закрыть",
    mealsTitle: "Питание",
    mealsNote: "Выберите приём пищи и количество гостей. Меню, доступность и стоимость подтверждает столовая.",
    meal: "Приём пищи",
    breakfast: "Завтрак",
    lunch: "Обед",
    dinner: "Ужин",
    adults: "Взрослые",
    children: "Дети",
    estimated: "Стоимость",
    mealWarning: "Включённое в проживание питание определяется вашей бронью. Стоимость дополнительного питания подтверждает столовая.",
    transferTitle: "Трансфер",
    origin: "Откуда",
    destination: "Куда",
    vehicle: "Автомобиль",
    sedan: "Седан",
    minivan: "Минивэн",
    manas: "Аэропорт Манас",
    tamchy: "Аэропорт Тамчы",
    bishkek: "Бишкек",
    hotel: "AK BERMET",
    other: "Другое место",
    luggage: "Багаж / особые пожелания",
    serviceInfo: "После отправки сотрудник подтвердит доступность, время и окончательные условия.",
    rules: "Правила и информация",
    rulesText: "Заезд с 13:00. Выезд до 11:00. По вопросам проживания, услуг и безопасности обращайтесь на ресепшен.",
    contacts: "Связаться с отелем",
    call: "Позвонить на ресепшен",
    message: "Написать менеджеру",
    signOut: "Закрыть гостевой доступ",
    status: { OPEN: "Принято", IN_PROGRESS: "В работе", IN_INSPECTION: "На проверке", DONE: "Выполнено", CANCELLED: "Отменено" },
    services: {
      HOUSEKEEPING: ["Уборка", "Уборка номера в удобное время"],
      TOWELS: ["Полотенца", "Принести чистые полотенца"],
      LINEN: ["Бельё", "Замена постельного белья"],
      MAINTENANCE: ["Ремонт", "Сообщить о проблеме в номере"],
      MEALS: ["Питание", "Завтрак, обед или ужин"],
      TRANSFER: ["Трансфер", "Поездка в аэропорт или город"],
      SAUNA: ["Сауна", "Запросить удобное время"],
      BILLIARDS: ["Бильярд", "Запросить посещение"],
      EXCURSIONS: ["Экскурсии", "Подобрать и запросить поездку"],
      PARKING: ["Парковка", "Помощь с парковкой"],
      ADMIN: ["Помощь", "Связаться с администратором"],
    },
  },
  kg: {
    property: "AK BERMET",
    product: "MARINA SMART · конок кабинети",
    language: "Тил",
    loading: "Санарип жардамчы ачылууда…",
    invalidTitle: "Бөлмө коду жеткиликсиз",
    invalidText: "Код табылган жок же алмаштырылган. Кабыл алуу кызматына кайрылыңыз.",
    noStayTitle: "Бөлмө кийинки конокко даяр",
    noStayText: "Азыр бул бөлмөдө активдүү жашоо жок.",
    room: "Бөлмө",
    verifyTitle: "Жашооңузду ырастаңыз",
    verifyText: "Катталууда кабыл алуу кызматынан алган алты орундуу кодду киргизиңиз.",
    pin: "Конок коду",
    open: "Кабинетти ачуу",
    checking: "Текшерилүүдө…",
    wrong: "Код туура эмес. Сандарды текшериңиз же кабыл алуу кызматына кайрылыңыз.",
    expired: "Коддун мөөнөтү бүттү. Кабыл алуу кызматынан жаңы код сураңыз.",
    limited: "Аракеттер өтө көп болду. Кийин кайра аракет кылыңыз же кабыл алуу кызматына кайрылыңыз.",
    error: "Кабинет ачылган жок. Байланышты текшерип, кайра аракет кылыңыз.",
    retry: "Кайра аракет кылуу",
    hello: "Кош келиңиз",
    stay: "Сиздин жашооңуз",
    from: "баштап",
    to: "чейин",
    checkout: "Чыгуу саат 11:00гө чейин",
    quick: "Азыр эмне керек?",
    quickNote: "Көпчүлүк кызматтарды бир нече басуу менен сураса болот.",
    myRequests: "Менин өтүнмөлөрүм",
    noRequests: "Азырынча өтүнмөлөр жок.",
    refresh: "Жаңыртуу",
    newRequest: "Жаңы өтүнмө",
    service: "Кызмат",
    date: "Күн",
    time: "Убакыт",
    comment: "Түшүндүрмө",
    commentPlaceholder: "Керек болсо маалымат кошуңуз",
    send: "Жөнөтүү",
    sending: "Жөнөтүлүүдө…",
    sent: "Өтүнмө жөнөтүлдү. Анын абалы «Менин өтүнмөлөрүм» бөлүмүндө көрүнөт.",
    cancel: "Жокко чыгаруу",
    close: "Жабуу",
    mealsTitle: "Тамактануу",
    mealsNote: "Тамактануу түрүн жана коноктордун санын тандаңыз. Менюну, жеткиликтүүлүктү жана бааны ашкана ырастайт.",
    meal: "Тамактануу",
    breakfast: "Эртең мененки тамак",
    lunch: "Түшкү тамак",
    dinner: "Кечки тамак",
    adults: "Чоңдор",
    children: "Балдар",
    estimated: "Баасы",
    mealWarning: "Жашоого кирген тамактануу сиздин бронуңуз боюнча аныкталат. Кошумча тамактануунун баасын ашкана ырастайт.",
    transferTitle: "Трансфер",
    origin: "Кайдан",
    destination: "Кайда",
    vehicle: "Унаа",
    sedan: "Седан",
    minivan: "Минивэн",
    manas: "Манас аэропорту",
    tamchy: "Тамчы аэропорту",
    bishkek: "Бишкек",
    hotel: "AK BERMET",
    other: "Башка жер",
    luggage: "Жүк / өзгөчө каалоо",
    serviceInfo: "Жөнөткөндөн кийин кызматкер жеткиликтүүлүктү, убакытты жана акыркы шарттарды ырастайт.",
    rules: "Эрежелер жана маалымат",
    rulesText: "Кирүү саат 13:00дөн, чыгуу саат 11:00гө чейин. Жашоо, кызматтар жана коопсуздук боюнча кабыл алуу кызматына кайрылыңыз.",
    contacts: "Мейманкана менен байланыш",
    call: "Кабыл алуу кызматына чалуу",
    message: "Менеджерге жазуу",
    signOut: "Конок кирүүсүн жабуу",
    status: { OPEN: "Кабыл алынды", IN_PROGRESS: "Аткарылууда", IN_INSPECTION: "Текшерүүдө", DONE: "Аткарылды", CANCELLED: "Жокко чыгарылды" },
    services: {
      HOUSEKEEPING: ["Тазалоо", "Бөлмөнү ыңгайлуу убакта тазалоо"],
      TOWELS: ["Сүлгүлөр", "Таза сүлгү алып келүү"],
      LINEN: ["Төшөк жабдыгы", "Төшөк жабдыгын алмаштыруу"],
      MAINTENANCE: ["Оңдоо", "Бөлмөдөгү көйгөйдү билдирүү"],
      MEALS: ["Тамактануу", "Эртең мененки, түшкү же кечки тамак"],
      TRANSFER: ["Трансфер", "Аэропортко же шаарга баруу"],
      SAUNA: ["Сауна", "Ыңгайлуу убакытты суроо"],
      BILLIARDS: ["Бильярд", "Келүү убактысын суроо"],
      EXCURSIONS: ["Экскурсиялар", "Саякат тандоо жана өтүнмө берүү"],
      PARKING: ["Унаа токтотуу", "Унаа токтотууга жардам"],
      ADMIN: ["Жардам", "Администратор менен байланышуу"],
    },
  },
  kz: {
    property: "AK BERMET",
    product: "MARINA SMART · қонақ кабинеті",
    language: "Тіл",
    loading: "Цифрлық консьерж ашылуда…",
    invalidTitle: "Бөлме коды қолжетімсіз",
    invalidText: "Код табылмады немесе ауыстырылды. Қабылдау бөліміне хабарласыңыз.",
    noStayTitle: "Бөлме келесі қонаққа дайын",
    noStayText: "Қазір бұл бөлмеге белсенді тұру тіркелмеген.",
    room: "Бөлме",
    verifyTitle: "Тұруыңызды растаңыз",
    verifyText: "Орналасу кезінде қабылдау бөлімінен алған алты таңбалы кодты енгізіңіз.",
    pin: "Қонақ коды",
    open: "Кабинетті ашу",
    checking: "Тексерілуде…",
    wrong: "Код сәйкес келмеді. Сандарды тексеріңіз немесе қабылдау бөліміне хабарласыңыз.",
    expired: "Кодтың мерзімі аяқталды. Қабылдау бөлімінен жаңа код сұраңыз.",
    limited: "Әрекет саны тым көп. Кейінірек қайталаңыз немесе қабылдау бөліміне хабарласыңыз.",
    error: "Кабинетті жүктеу мүмкін болмады. Байланысты тексеріп, қайта көріңіз.",
    retry: "Қайталау",
    hello: "Қош келдіңіз",
    stay: "Сіздің тұруыңыз",
    from: "бастап",
    to: "дейін",
    checkout: "Шығу 11:00-ге дейін",
    quick: "Қазір не қажет?",
    quickNote: "Қызметтердің көбін бірнеше рет басу арқылы сұратуға болады.",
    myRequests: "Менің өтінімдерім",
    noRequests: "Әзірге өтінімдер жоқ.",
    refresh: "Жаңарту",
    newRequest: "Жаңа өтінім",
    service: "Қызмет",
    date: "Күн",
    time: "Уақыт",
    comment: "Түсініктеме",
    commentPlaceholder: "Қажет болса, қосымша мәлімет жазыңыз",
    send: "Жіберу",
    sending: "Жіберілуде…",
    sent: "Өтінім жіберілді. Күйі «Менің өтінімдерім» бөлімінде көрінеді.",
    cancel: "Бас тарту",
    close: "Жабу",
    mealsTitle: "Тамақтану",
    mealsNote: "Тамақтану түрін және қонақтар санын таңдаңыз. Мәзірді, қолжетімділікті және құнын асүй қызметі растайды.",
    meal: "Тамақтану",
    breakfast: "Таңғы ас",
    lunch: "Түскі ас",
    dinner: "Кешкі ас",
    adults: "Ересектер",
    children: "Балалар",
    estimated: "Құны",
    mealWarning: "Тұруға кіретін тамақтану сіздің броніңізге байланысты. Қосымша тамақтану құнын асхана растайды.",
    transferTitle: "Трансфер",
    origin: "Қайдан",
    destination: "Қайда",
    vehicle: "Көлік",
    sedan: "Седан",
    minivan: "Минивэн",
    manas: "Манас әуежайы",
    tamchy: "Тамчы әуежайы",
    bishkek: "Бішкек",
    hotel: "AK BERMET",
    other: "Басқа орын",
    luggage: "Жүк / ерекше тілек",
    serviceInfo: "Жіберілгеннен кейін қызметкер қолжетімділікті, уақытты және соңғы шарттарды растайды.",
    rules: "Ережелер мен ақпарат",
    rulesText: "Кіру 13:00-ден, шығу 11:00-ге дейін. Тұру, қызметтер және қауіпсіздік мәселелері бойынша қабылдау бөліміне хабарласыңыз.",
    contacts: "Қонақүймен байланысу",
    call: "Қабылдау бөліміне қоңырау шалу",
    message: "Менеджерге жазу",
    signOut: "Қонақ қолжетімділігін жабу",
    status: { OPEN: "Қабылданды", IN_PROGRESS: "Жұмыста", IN_INSPECTION: "Тексеруде", DONE: "Орындалды", CANCELLED: "Бас тартылды" },
    services: {
      HOUSEKEEPING: ["Тазалау", "Бөлмені ыңғайлы уақытта тазалау"],
      TOWELS: ["Сүлгілер", "Таза сүлгі әкелу"],
      LINEN: ["Төсек-орын", "Төсек-орынды ауыстыру"],
      MAINTENANCE: ["Жөндеу", "Бөлмедегі мәселе туралы хабарлау"],
      MEALS: ["Тамақтану", "Таңғы, түскі немесе кешкі ас"],
      TRANSFER: ["Трансфер", "Әуежайға немесе қалаға бару"],
      SAUNA: ["Сауна", "Ыңғайлы уақытты сұрату"],
      BILLIARDS: ["Бильярд", "Келу уақытын сұрату"],
      EXCURSIONS: ["Экскурсиялар", "Сапарды таңдау және сұрату"],
      PARKING: ["Тұрақ", "Тұраққа көмектесу"],
      ADMIN: ["Көмек", "Әкімшімен байланысу"],
    },
  },
  en: {
    property: "AK BERMET",
    product: "MARINA SMART · Guest area",
    language: "Language",
    loading: "Opening your digital concierge…",
    invalidTitle: "Room code unavailable",
    invalidText: "This code was not found or has been replaced. Please contact reception.",
    noStayTitle: "Room ready for the next arrival",
    noStayText: "There is no active stay assigned to this room right now.",
    room: "Room",
    verifyTitle: "Confirm your stay",
    verifyText: "Enter the six-digit code issued by reception at check-in.",
    pin: "Guest code",
    open: "Open guest area",
    checking: "Checking…",
    wrong: "That code did not match. Check the digits or contact reception.",
    expired: "This code has expired. Ask reception for a new code.",
    limited: "Too many attempts. Try later or contact reception.",
    error: "The guest area could not be loaded. Check your connection and try again.",
    retry: "Try again",
    hello: "Welcome",
    stay: "Your stay",
    from: "from",
    to: "to",
    checkout: "Check-out by 11:00",
    quick: "What do you need now?",
    quickNote: "Most hotel services can be requested in just a few taps.",
    myRequests: "My requests",
    noRequests: "No requests yet.",
    refresh: "Refresh",
    newRequest: "New request",
    service: "Service",
    date: "Date",
    time: "Time",
    comment: "Comment",
    commentPlaceholder: "Add details if needed",
    send: "Send request",
    sending: "Sending…",
    sent: "Request sent. Its status will appear under My requests.",
    cancel: "Cancel",
    close: "Close",
    mealsTitle: "Dining",
    mealsNote: "Choose a meal and number of guests. The dining team confirms the menu, availability and price.",
    meal: "Meal",
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
    adults: "Adults",
    children: "Children",
    estimated: "Price",
    mealWarning: "Meal inclusion depends on your reservation. The dining team confirms the price of additional meals.",
    transferTitle: "Transfer",
    origin: "From",
    destination: "To",
    vehicle: "Vehicle",
    sedan: "Sedan",
    minivan: "Minivan",
    manas: "Manas Airport",
    tamchy: "Tamchy Airport",
    bishkek: "Bishkek",
    hotel: "AK BERMET",
    other: "Other location",
    luggage: "Luggage / special request",
    serviceInfo: "After submission, staff will confirm availability, timing and final conditions.",
    rules: "Rules and information",
    rulesText: "Check-in is from 13:00. Check-out is by 11:00. Contact reception for stay, service or safety questions.",
    contacts: "Contact the hotel",
    call: "Call reception",
    message: "Message manager",
    signOut: "Close guest access",
    status: { OPEN: "Received", IN_PROGRESS: "In progress", IN_INSPECTION: "Under review", DONE: "Completed", CANCELLED: "Cancelled" },
    services: {
      HOUSEKEEPING: ["Housekeeping", "Clean the room at a convenient time"],
      TOWELS: ["Towels", "Bring fresh towels"],
      LINEN: ["Bed linen", "Replace bed linen"],
      MAINTENANCE: ["Maintenance", "Report a room issue"],
      MEALS: ["Dining", "Breakfast, lunch or dinner"],
      TRANSFER: ["Transfer", "Airport or city transfer"],
      SAUNA: ["Sauna", "Request a convenient time"],
      BILLIARDS: ["Billiards", "Request a visit"],
      EXCURSIONS: ["Excursions", "Choose and request a trip"],
      PARKING: ["Parking", "Get parking assistance"],
      ADMIN: ["Help", "Contact an administrator"],
    },
  },
} as const;

const SERVICE_ORDER: RequestCode[] = ["MEALS", "HOUSEKEEPING", "TRANSFER", "MAINTENANCE", "SAUNA", "EXCURSIONS", "TOWELS", "LINEN", "BILLIARDS", "ADMIN"];
const SERVICE_ICONS: Record<RequestCode, string> = { MEALS: "🍽", HOUSEKEEPING: "✦", TRANSFER: "↗", MAINTENANCE: "⌁", SAUNA: "♨", EXCURSIONS: "⌖", TOWELS: "▤", LINEN: "▧", BILLIARDS: "●", PARKING: "P", ADMIN: "?" };

function dateLabel(value: string, locale: Locale) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(marinaGuestIntlLocale(locale), { day: "numeric", month: "short" });
}

export default function GuestConciergeRuntime({ token }: { token: string }) {
  const [locale, chooseLocale] = useMarinaGuestLocale();
  const [context, setContext] = useState<GuestContext | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "invalid" | "error">("loading");
  const [pin, setPin] = useState("");
  const [pinMessage, setPinMessage] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [requests, setRequests] = useState<GuestRequest[]>([]);
  const [selected, setSelected] = useState<RequestCode | null>(null);
  const [comment, setComment] = useState("");
  const [serviceDate, setServiceDate] = useState("");
  const [serviceTime, setServiceTime] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [meal, setMeal] = useState<"breakfast" | "lunch" | "dinner">("lunch");
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [origin, setOrigin] = useState("hotel");
  const [destination, setDestination] = useState("tamchy");
  const [vehicle, setVehicle] = useState("sedan");

  const copy = COPY[locale];

  const loadContext = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}`, { credentials: "include", cache: "no-store" });
      if (response.status === 404) { setContext(null); setState("invalid"); return; }
      if (!response.ok) throw new Error();
      setContext(await response.json() as GuestContext);
      setState("ready");
    } catch { setContext(null); setState("error"); }
  }, [token]);

  const loadRequests = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, { credentials: "include", cache: "no-store" });
      if (!response.ok) { setRequests([]); return; }
      const body = await response.json() as { items?: GuestRequest[] };
      setRequests(body.items ?? []);
    } catch { setRequests([]); }
  }, [token]);

  useEffect(() => { void loadContext(); }, [loadContext]);
  useEffect(() => {
    if (!context?.authenticated) return;
    void loadRequests();
    const timer = window.setInterval(() => void loadRequests(), 15000);
    return () => window.clearInterval(timer);
  }, [context?.authenticated, loadRequests]);

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(pin)) return;
    setChecking(true); setPinMessage(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/verify`, { method: "POST", credentials: "include", headers: { "content-type": "application/json" }, body: JSON.stringify({ pin }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const code = body?.detail?.code;
        setPinMessage(code === "PIN_EXPIRED" ? copy.expired : code === "PIN_RATE_LIMIT" ? copy.limited : copy.wrong);
        return;
      }
      setPin(""); await loadContext();
    } catch { setPinMessage(copy.error); }
    finally { setChecking(false); }
  }

  function descriptionFor(code: RequestCode) {
    if (code === "MEALS") {
      const mealName = copy[meal];
      return `${mealName}; ${copy.adults}: ${adults}; ${copy.children}: ${children}${comment.trim() ? `; ${copy.comment}: ${comment.trim()}` : ""}`;
    }
    if (code === "TRANSFER") {
      const from = copy[origin as "hotel" | "manas" | "tamchy" | "bishkek" | "other"];
      const to = copy[destination as "hotel" | "manas" | "tamchy" | "bishkek" | "other"];
      const car = vehicle === "minivan" ? copy.minivan : copy.sedan;
      return `${copy.origin}: ${from}; ${copy.destination}: ${to}; ${copy.vehicle}: ${car}${comment.trim() ? `; ${copy.luggage}: ${comment.trim()}` : ""}`;
    }
    return comment.trim() || null;
  }

  async function sendRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSending(true); setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST", credentials: "include", headers: { "content-type": "application/json" },
        body: JSON.stringify({ request_code: selected, description: descriptionFor(selected), service_date: serviceDate || null, service_time: serviceTime || null }),
      });
      if (!response.ok) throw new Error();
      setNotice(copy.sent); setComment(""); setServiceDate(""); setServiceTime("");
      await loadRequests();
    } catch { setNotice(copy.error); }
    finally { setSending(false); }
  }

  async function cancelRequest(id: string) {
    const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests/${id}/cancel`, { method: "POST", credentials: "include" }).catch(() => null);
    if (response?.ok) await loadRequests();
  }

  async function logout() {
    await fetch("/core/api/v1/guest-os/logout", { method: "POST", credentials: "include" }).catch(() => null);
    setContext(null); setRequests([]); await loadContext();
  }

  const services: Service[] = useMemo(() => SERVICE_ORDER.map((code) => ({ code, icon: SERVICE_ICONS[code], title: copy.services[code][0], note: copy.services[code][1] })), [copy]);

  return <main className="concierge-page">
    <header className="concierge-topbar">
      <div className="concierge-brand"><span>III</span><div><strong>{copy.property}</strong><small>{copy.product}</small></div></div>
      <div className="concierge-langs" aria-label={copy.language}>{MARINA_GUEST_LOCALES.map((item) => <button key={item} onClick={() => chooseLocale(item)} aria-pressed={locale === item}>{item.toUpperCase()}</button>)}</div>
    </header>

    {state === "loading" && <section className="concierge-state">{copy.loading}</section>}
    {state === "invalid" && <section className="concierge-state"><h1>{copy.invalidTitle}</h1><p>{copy.invalidText}</p></section>}
    {state === "error" && <section className="concierge-state"><h1>{copy.error}</h1><button onClick={() => void loadContext()}>{copy.retry}</button></section>}

    {state === "ready" && context && !context.active_stay && <section className="concierge-state"><p>{copy.room} {context.room.code}</p><h1>{copy.noStayTitle}</h1><p>{copy.noStayText}</p></section>}

    {state === "ready" && context?.active_stay && !context.authenticated && <section className="concierge-auth">
      <span className="concierge-room-chip">{copy.room} {context.room.code}</span>
      <h1>{copy.verifyTitle}</h1><p>{copy.verifyText}</p>
      <form onSubmit={verify}><label>{copy.pin}<input inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="••••••" /></label>{pinMessage && <div className="concierge-error">{pinMessage}</div>}<button disabled={checking || pin.length !== 6}>{checking ? copy.checking : copy.open}</button></form>
    </section>}

    {state === "ready" && context?.authenticated && context.stay && <>
      <section className="concierge-hero">
        <div><p>{copy.hello}{context.guest?.first_name ? `, ${context.guest.first_name}` : ""}</p><h1>{copy.room} {context.room.code}</h1></div>
        <div className="concierge-stay"><strong>{copy.stay}</strong><span>{dateLabel(context.stay.check_in, locale)} — {dateLabel(context.stay.check_out, locale)}</span><small>{copy.checkout}</small></div>
      </section>

      <section className="concierge-section"><div className="concierge-heading"><div><h2>{copy.quick}</h2><p>{copy.quickNote}</p></div></div><div className="concierge-actions">{services.slice(0, 6).map((service) => <button key={service.code} onClick={() => { setSelected(service.code); setNotice(null); }}><span>{service.icon}</span><strong>{service.title}</strong><small>{service.note}</small></button>)}</div></section>

      <section className="concierge-section concierge-requests"><div className="concierge-heading"><h2>{copy.myRequests}</h2><button onClick={() => void loadRequests()}>{copy.refresh}</button></div>{!requests.length ? <p className="concierge-empty">{copy.noRequests}</p> : <div className="concierge-request-list">{requests.map((item) => { const code = (SERVICE_ORDER.includes(item.request_code as RequestCode) || item.request_code === "PARKING" ? item.request_code : "ADMIN") as RequestCode; return <article key={item.id}><div><strong>{copy.services[code][0]}</strong><span data-status={item.status}>{copy.status[item.status]}</span></div>{item.description && <p>{item.description}</p>} {item.status === "OPEN" && <button onClick={() => void cancelRequest(item.id)}>{copy.cancel}</button>}</article>; })}</div>}</section>

      <section className="concierge-section"><div className="concierge-heading"><h2>{copy.rules}</h2></div><div className="concierge-info-grid"><article><p>{copy.rulesText}</p></article><article><h3>{copy.contacts}</h3><a href={`tel:${HOTEL_PHONE_E164}`}>{copy.call}</a><a href={HOTEL_WHATSAPP_URL} target="_blank" rel="noreferrer">{copy.message}</a></article></div></section>
      <button className="concierge-signout" onClick={() => void logout()}>{copy.signOut}</button>
    </>}

    {selected && <div className="concierge-modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelected(null); }}><section className="concierge-modal" role="dialog" aria-modal="true"><div className="concierge-modal-head"><div><small>{copy.newRequest}</small><h2>{selected === "MEALS" ? copy.mealsTitle : selected === "TRANSFER" ? copy.transferTitle : copy.services[selected][0]}</h2></div><button onClick={() => setSelected(null)} aria-label={copy.close}>×</button></div><p>{selected === "MEALS" ? copy.mealsNote : selected === "TRANSFER" ? copy.serviceInfo : copy.services[selected][1]}</p><form onSubmit={sendRequest}>
      {selected === "MEALS" && <><label>{copy.meal}<select value={meal} onChange={(e) => setMeal(e.target.value as typeof meal)}><option value="breakfast">{copy.breakfast}</option><option value="lunch">{copy.lunch}</option><option value="dinner">{copy.dinner}</option></select></label><div className="concierge-two"><label>{copy.adults}<input type="number" min="0" max="10" value={adults} onChange={(e) => setAdults(Number(e.target.value))} /></label><label>{copy.children}<input type="number" min="0" max="10" value={children} onChange={(e) => setChildren(Number(e.target.value))} /></label></div><div className="concierge-estimate"><span>{copy.estimated}</span><strong>{copy.mealWarning}</strong></div></>}
      {selected === "TRANSFER" && <><div className="concierge-two"><label>{copy.origin}<select value={origin} onChange={(e) => setOrigin(e.target.value)}><option value="hotel">{copy.hotel}</option><option value="manas">{copy.manas}</option><option value="tamchy">{copy.tamchy}</option><option value="bishkek">{copy.bishkek}</option><option value="other">{copy.other}</option></select></label><label>{copy.destination}<select value={destination} onChange={(e) => setDestination(e.target.value)}><option value="hotel">{copy.hotel}</option><option value="manas">{copy.manas}</option><option value="tamchy">{copy.tamchy}</option><option value="bishkek">{copy.bishkek}</option><option value="other">{copy.other}</option></select></label></div><label>{copy.vehicle}<select value={vehicle} onChange={(e) => setVehicle(e.target.value)}><option value="sedan">{copy.sedan}</option><option value="minivan">{copy.minivan}</option></select></label></>}
      <div className="concierge-two"><label>{copy.date}<input type="date" value={serviceDate} onChange={(e) => setServiceDate(e.target.value)} /></label><label>{copy.time}<input type="time" value={serviceTime} onChange={(e) => setServiceTime(e.target.value)} /></label></div><label>{selected === "TRANSFER" ? copy.luggage : copy.comment}<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder={copy.commentPlaceholder} maxLength={1200} /></label>{notice && <div className="concierge-notice">{notice}</div>}<button className="concierge-submit" disabled={sending}>{sending ? copy.sending : copy.send}</button></form></section></div>}
  </main>;
}
