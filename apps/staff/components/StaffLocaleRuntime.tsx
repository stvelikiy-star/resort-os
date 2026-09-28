"use client";

import { useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "kz" | "en";
type Copy = { kg: string; kz: string; en: string };

const STORAGE_KEY = "marina-smart-staff-locale";

const COPY: Record<string, Copy> = {
  "Моя смена": { kg: "Менин нөөмөтүм", kz: "Менің ауысымым", en: "My shift" },
  "Логин": { kg: "Логин", kz: "Логин", en: "Username" },
  "Пароль": { kg: "Сырсөз", kz: "Құпиясөз", en: "Password" },
  "Войти": { kg: "Кирүү", kz: "Кіру", en: "Sign in" },
  "Выйти": { kg: "Чыгуу", kz: "Шығу", en: "Sign out" },
  "Обновить": { kg: "Жаңыртуу", kz: "Жаңарту", en: "Refresh" },
  "Кухня": { kg: "Ашкана", kz: "Асүй", en: "Kitchen" },
  "Официант / зал": { kg: "Официант / зал", kz: "Даяшы / зал", en: "Waiter / dining floor" },
  "Меню сегодня": { kg: "Бүгүнкү меню", kz: "Бүгінгі мәзір", en: "Today's menu" },
  "Заказы": { kg: "Буйрутмалар", kz: "Тапсырыстар", en: "Orders" },
  "Столы": { kg: "Столдор", kz: "Үстелдер", en: "Tables" },
  "Меню": { kg: "Меню", kz: "Мәзір", en: "Menu" },
  "Заезды": { kg: "Кирүүлөр", kz: "Келулер", en: "Arrivals" },
  "Новый": { kg: "Жаңы", kz: "Жаңа", en: "New" },
  "Принят": { kg: "Кабыл алынды", kz: "Қабылданды", en: "Accepted" },
  "Готовится": { kg: "Даярдалууда", kz: "Дайындалып жатыр", en: "Cooking" },
  "Готов": { kg: "Даяр", kz: "Дайын", en: "Ready" },
  "Готов к выдаче": { kg: "Берүүгө даяр", kz: "Беруге дайын", en: "Ready to serve" },
  "Выдан": { kg: "Берилди", kz: "Берілді", en: "Served" },
  "Отменён": { kg: "Жокко чыгарылды", kz: "Бас тартылды", en: "Cancelled" },
  "Свободен": { kg: "Бош", kz: "Бос", en: "Available" },
  "Ожидает": { kg: "Күтүүдө", kz: "Күтуде", en: "Waiting" },
  "Занят": { kg: "Бош эмес", kz: "Бос емес", en: "Occupied" },
  "Уборка": { kg: "Тазалоо", kz: "Тазалау", en: "Cleaning" },
  "Закрыт": { kg: "Жабык", kz: "Жабық", en: "Closed" },
  "Бронь": { kg: "Бронь", kz: "Бронь", en: "Reserved" },
  "Завтрак": { kg: "Эртең мененки тамак", kz: "Таңғы ас", en: "Breakfast" },
  "Обед": { kg: "Түшкү тамак", kz: "Түскі ас", en: "Lunch" },
  "Ужин": { kg: "Кечки тамак", kz: "Кешкі ас", en: "Dinner" },
  "Супы": { kg: "Шорполор", kz: "Сорпалар", en: "Soups" },
  "Салаты": { kg: "Салаттар", kz: "Салаттар", en: "Salads" },
  "Основное": { kg: "Негизги", kz: "Негізгі", en: "Main dishes" },
  "Гарниры": { kg: "Гарнирлер", kz: "Гарнирлер", en: "Sides" },
  "Десерты": { kg: "Десерттер", kz: "Десерттер", en: "Desserts" },
  "Напитки": { kg: "Суусундуктар", kz: "Сусындар", en: "Drinks" },
  "Создать заказ": { kg: "Буйрутма түзүү", kz: "Тапсырыс құру", en: "Create order" },
  "Новый заказ": { kg: "Жаңы буйрутма", kz: "Жаңа тапсырыс", en: "New order" },
  "Сумма заказа": { kg: "Буйрутманын суммасы", kz: "Тапсырыс сомасы", en: "Order total" },
  "Комментарий": { kg: "Комментарий", kz: "Түсініктеме", en: "Comment" },
  "Без стола": { kg: "Столсуз", kz: "Үстелсіз", en: "No table" },
  "Стол": { kg: "Стол", kz: "Үстел", en: "Table" },
  "Номер": { kg: "Бөлмө", kz: "Бөлме", en: "Room" },
  "Гость": { kg: "Конок", kz: "Қонақ", en: "Guest" },
  "Гости": { kg: "Коноктор", kz: "Қонақтар", en: "Guests" },
  "Дата": { kg: "Күн", kz: "Күн", en: "Date" },
  "Сегодня": { kg: "Бүгүн", kz: "Бүгін", en: "Today" },
  "сегодня": { kg: "бүгүн", kz: "бүгін", en: "today" },
  "Открыть Kitchen Admin": { kg: "Kitchen Admin ачуу", kz: "Kitchen Admin ашу", en: "Open Kitchen Admin" },
  "Kitchen Admin готов к работе.": { kg: "Kitchen Admin иштөөгө даяр.", kz: "Kitchen Admin жұмысқа дайын.", en: "Kitchen Admin is ready." },
  "Рабочая очередь ниже обновляется автоматически.": { kg: "Төмөнкү жумуш кезеги автоматтык жаңыртылат.", kz: "Төмендегі жұмыс кезегі автоматты жаңартылады.", en: "The work queue below refreshes automatically." },
  "Берите заявку в работу и закрывайте её после фактического выполнения.": { kg: "Өтүнмөнү ишке алып, чыныгы аткарылгандан кийин жабыңыз.", kz: "Өтінімді жұмысқа алып, нақты орындалғаннан кейін жабыңыз.", en: "Take a request into work and close it only after completion." },
  "Подключаю смену…": { kg: "Нөөмөттү туташтырып жатам…", kz: "Ауысымды қосып жатырмын…", en: "Connecting shift…" },
  "Проверяю рабочую сессию и Telegram.": { kg: "Жумуш сессиясын жана Telegram'ды текшерип жатам.", kz: "Жұмыс сессиясы мен Telegram тексерілуде.", en: "Checking the work session and Telegram." },
  "Войдите под рабочей учётной записью.": { kg: "Жумуш аккаунту менен кириңиз.", kz: "Жұмыс аккаунтымен кіріңіз.", en: "Sign in with your work account." },
  "Неверный логин, пароль или роль не относится к операционной смене.": { kg: "Логин, сырсөз туура эмес же роль операциялык нөөмөткө кирбейт.", kz: "Логин не құпиясөз қате немесе рөл операциялық ауысымға жатпайды.", en: "Invalid username/password or this role is not assigned to the operational shift." },
  "Resort Core недоступен": { kg: "Resort Core жеткиликсиз", kz: "Resort Core қолжетімсіз", en: "Resort Core is unavailable" },
  "Владелец": { kg: "Ээси", kz: "Иесі", en: "Owner" },
  "Менеджер": { kg: "Менеджер", kz: "Менеджер", en: "Manager" },
  "Ресепшен": { kg: "Ресепшен", kz: "Ресепшен", en: "Reception" },
  "Горничная": { kg: "Бөлмө кызматкери", kz: "Бөлме қызметкері", en: "Housekeeper" },
  "Техник": { kg: "Техник", kz: "Техник", en: "Technician" },
  "Питание": { kg: "Тамактануу", kz: "Тамақтану", en: "Dining" },
  "Магазин": { kg: "Дүкөн", kz: "Дүкен", en: "Store" },
  "Срочно": { kg: "Шашылыш", kz: "Шұғыл", en: "Urgent" },
  "Высокий": { kg: "Жогорку", kz: "Жоғары", en: "High" },
  "Обычный": { kg: "Кадимки", kz: "Қалыпты", en: "Normal" },
  "Низкий": { kg: "Төмөн", kz: "Төмен", en: "Low" },
  "В работе": { kg: "Аткарылууда", kz: "Жұмыста", en: "In progress" },
  "На проверке": { kg: "Текшерүүдө", kz: "Тексеруде", en: "In inspection" },
  "Готово": { kg: "Даяр", kz: "Дайын", en: "Done" },
  "Отменена": { kg: "Жокко чыгарылды", kz: "Бас тартылды", en: "Cancelled" },
  "Нужна уборка": { kg: "Тазалоо керек", kz: "Тазалау қажет", en: "Needs cleaning" },
  "Техблок": { kg: "Техблок", kz: "Техблок", en: "Tech block" },
  "Не указан": { kg: "Көрсөтүлгөн эмес", kz: "Көрсетілмеген", en: "Not specified" },
  "Мои задачи": { kg: "Менин тапшырмаларым", kz: "Менің тапсырмаларым", en: "My tasks" },
  "Свободные задачи": { kg: "Бош тапшырмалар", kz: "Бос тапсырмалар", en: "Available tasks" },
  "Завершённые": { kg: "Аяктагандар", kz: "Аяқталғандар", en: "Completed" },
  "Здесь пока пусто": { kg: "Бул жерде азырынча бош", kz: "Мұнда әзірге бос", en: "Nothing here yet" },
  "Взять в работу": { kg: "Ишке алуу", kz: "Жұмысқа алу", en: "Take task" },
  "Сдать уборку": { kg: "Тазалоону тапшыруу", kz: "Тазалауды тапсыру", en: "Submit cleaning" },
  "Сдать ремонт": { kg: "Оңдоону тапшыруу", kz: "Жөндеуді тапсыру", en: "Submit repair" },
  "Отчёт о работе": { kg: "Иш боюнча отчет", kz: "Жұмыс есебі", en: "Work report" },
  "Чек-лист уборки": { kg: "Тазалоо чек-листи", kz: "Тазалау чек-парағы", en: "Cleaning checklist" },
  "Что сделано": { kg: "Эмне жасалды", kz: "Не жасалды", en: "Work completed" },
  "Фото / ссылка на подтверждение": { kg: "Сүрөт / ырастоо шилтемеси", kz: "Фото / растау сілтемесі", en: "Photo / evidence link" },
  "Отправить на проверку": { kg: "Текшерүүгө жөнөтүү", kz: "Тексеруге жіберу", en: "Send for inspection" },
  "Завершить ремонт": { kg: "Оңдоону аяктоо", kz: "Жөндеуді аяқтау", en: "Complete repair" },
  "Очередь кухни": { kg: "Ашкана кезеги", kz: "Асүй кезегі", en: "Kitchen queue" },
  "Активных заказов нет.": { kg: "Активдүү буйрутмалар жок.", kz: "Белсенді тапсырыстар жоқ.", en: "No active orders." },
  "Добавить стол": { kg: "Стол кошуу", kz: "Үстел қосу", en: "Add table" },
  "Количество мест": { kg: "Орундардын саны", kz: "Орын саны", en: "Number of seats" },
  "Добавить": { kg: "Кошуу", kz: "Қосу", en: "Add" },
  "Меню кухни": { kg: "Ашкана менюсу", kz: "Асүй мәзірі", en: "Kitchen menu" },
  "Новые заезды": { kg: "Жаңы кирүүлөр", kz: "Жаңа келулер", en: "New arrivals" },
  "Непросмотренных заездов нет.": { kg: "Каралбаган жаңы кирүүлөр жок.", kz: "Қаралмаған келулер жоқ.", en: "No unreviewed arrivals." },
  "Ознакомился": { kg: "Тааныштым", kz: "Таныстым", en: "Reviewed" },
  "Схема зала": { kg: "Залдын схемасы", kz: "Зал сызбасы", en: "Floor plan" },
  "Весь зал": { kg: "Бардык зал", kz: "Бүкіл зал", en: "All floor" },
  "Выберите стол": { kg: "Стол тандаңыз", kz: "Үстелді таңдаңыз", en: "Select a table" },
  "Активные заказы": { kg: "Активдүү буйрутмалар", kz: "Белсенді тапсырыстар", en: "Active orders" },
  "Взять заказ": { kg: "Буйрутманы алуу", kz: "Тапсырысты алу", en: "Take order" },
  "Выдано гостю": { kg: "Конокко берилди", kz: "Қонаққа берілді", en: "Served to guest" },
  "Заказ со стола": { kg: "Столдон буйрутма", kz: "Үстелден тапсырыс", en: "Table order" },
  "Сумма": { kg: "Сумма", kz: "Сома", en: "Total" },
  "Брони столов сегодня": { kg: "Бүгүнкү стол брондору", kz: "Бүгінгі үстел броньдары", en: "Today's table reservations" },
  "Забронировать стол": { kg: "Стол брондоо", kz: "Үстелді броньдау", en: "Reserve a table" },
  "Имя гостя": { kg: "Коноктун аты", kz: "Қонақтың аты", en: "Guest name" },
  "Телефон": { kg: "Телефон", kz: "Телефон", en: "Phone" },
  "Начало": { kg: "Башталышы", kz: "Басталуы", en: "Start" },
  "До": { kg: "Чейин", kz: "Дейін", en: "Until" },
  "Создать бронь стола": { kg: "Стол бронун түзүү", kz: "Үстел бронін құру", en: "Create table reservation" },
};

function translated(text: string, locale: Locale): string {
  if (locale === "ru") return text;
  const direct = COPY[text];
  if (direct) return direct[locale];
  const room = text.match(/^Номер\s+(.+)$/);
  if (room) return `${locale === "en" ? "Room" : locale === "kz" ? "Бөлме" : "Бөлмө"} ${room[1]}`;
  return text;
}

export default function StaffLocaleRuntime() {
  const [locale, setLocale] = useState<Locale>("ru");
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
        const trimmed = current.trim();
        if (!trimmed) return;
        const previous = originalText.get(text);
        const source = previous && current === previous.rendered ? previous.source : current;
        const sourceTrimmed = source.trim();
        const renderedCore = translated(sourceTrimmed, locale);
        const prefix = source.slice(0, source.indexOf(sourceTrimmed));
        const suffix = source.slice(source.indexOf(sourceTrimmed) + sourceTrimmed.length);
        const rendered = `${prefix}${renderedCore}${suffix}`;
        originalText.set(text, { source, rendered });
        if (current !== rendered) text.nodeValue = rendered;
        return;
      }
      if (!(node instanceof Element)) return;
      if (node.matches("script,style,code,pre,[data-staff-i18n-skip]")) return;
      for (const attr of ["placeholder", "title", "aria-label"]) {
        if (!node.hasAttribute(attr)) continue;
        const current = node.getAttribute(attr) || "";
        const attrMap = originalAttrs.get(node) || new Map<string, { source: string; rendered: string }>();
        const previous = attrMap.get(attr);
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translated(source, locale);
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
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, [locale, originalAttrs, originalText]);

  const label = locale === "en" ? "Language" : locale === "kg" ? "Тил" : locale === "kz" ? "Тіл" : "Язык";

  return <div data-staff-i18n-skip style={{ position: "fixed", right: 12, top: 12, zIndex: 9999, display: "flex", alignItems: "center", gap: 4, padding: "6px 7px", borderRadius: 999, background: "rgba(10,17,40,.94)", color: "#fff", boxShadow: "0 8px 28px rgba(0,0,0,.22)", font: "700 11px/1 system-ui,sans-serif" }}>
    <span style={{ padding: "0 5px", opacity: .8 }}>{label}</span>
    {(["ru", "kg", "kz", "en"] as Locale[]).map((value) => <button key={value} type="button" onClick={() => setLocale(value)} aria-pressed={locale === value} style={{ border: "1px solid rgba(255,255,255,.22)", borderRadius: 999, padding: "6px 7px", cursor: "pointer", background: locale === value ? "#fff" : "transparent", color: locale === value ? "#0a1128" : "#fff", font: "800 10px/1 system-ui,sans-serif" }}>{value.toUpperCase()}</button>)}
  </div>;
}
