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

// STAFF_I18N_AUDIT_V2
Object.assign(COPY, {
  "Telegram подтверждён": {
    "kg": "Telegram ырасталды",
    "kz": "Telegram расталды",
    "en": "Telegram confirmed"
  },
  "Telegram-вход временно недоступен": {
    "kg": "Telegram аркылуу кирүү убактылуу жеткиликсиз",
    "kz": "Telegram арқылы кіру уақытша қолжетімсіз",
    "en": "Telegram sign-in is temporarily unavailable"
  },
  "Telegram привязан. Следующий вход будет автоматическим.": {
    "kg": "Telegram байланыштырылды. Кийинки кирүү автоматтык болот.",
    "kz": "Telegram байланыстырылды. Келесі кіру автоматты болады.",
    "en": "Telegram linked. Next sign-in will be automatic."
  },
  "Telegram привязан. Следующий вход — автоматически.": {
    "kg": "Telegram байланыштырылды. Кийинки кирүү — автоматтык.",
    "kz": "Telegram байланыстырылды. Келесі кіру — автоматты.",
    "en": "Telegram linked. Next sign-in is automatic."
  },
  "MARINA SMART недоступен": {
    "kg": "MARINA SMART жеткиликсиз",
    "kz": "MARINA SMART қолжетімсіз",
    "en": "MARINA SMART is unavailable"
  },
  "Первый вход — рабочий логин и пароль. После привязки Telegram вход будет автоматическим.": {
    "kg": "Биринчи кирүү — жумуш логини жана сырсөз. Telegram байланыштырылгандан кийин кирүү автоматтык болот.",
    "kz": "Алғашқы кіру — жұмыс логині мен құпиясөз. Telegram байланыстырылғаннан кейін кіру автоматты болады.",
    "en": "First sign-in uses your work username and password. After Telegram is linked, sign-in will be automatic."
  },
  "Первый вход: рабочий логин и пароль. После привязки Telegram вход будет автоматическим.": {
    "kg": "Биринчи кирүү: жумуш логини жана сырсөз. Telegram байланыштырылгандан кийин кирүү автоматтык болот.",
    "kz": "Алғашқы кіру: жұмыс логині мен құпиясөз. Telegram байланыстырылғаннан кейін кіру автоматты болады.",
    "en": "First sign-in: work username and password. After Telegram is linked, sign-in will be automatic."
  },
  "Свободная": {
    "kg": "Бош",
    "kz": "Бос",
    "en": "Available"
  },
  "Кровать и бельё": {
    "kg": "Керебет жана шейшеп",
    "kz": "Төсек және төсек-орын",
    "en": "Bed and linen"
  },
  "Санузел": {
    "kg": "Санузел",
    "kz": "Санторап",
    "en": "Bathroom"
  },
  "Пол и поверхности": {
    "kg": "Пол жана беттер",
    "kz": "Еден және беттер",
    "en": "Floor and surfaces"
  },
  "Комплектация номера": {
    "kg": "Бөлмөнүн жабдылышы",
    "kz": "Бөлме жабдықталуы",
    "en": "Room amenities"
  },
  "Финальная проверка": {
    "kg": "Акыркы текшерүү",
    "kz": "Қорытынды тексеру",
    "en": "Final inspection"
  },
  "Не удалось загрузить смену": {
    "kg": "Нөөмөттү жүктөө мүмкүн болгон жок",
    "kz": "Ауысымды жүктеу мүмкін болмады",
    "en": "Could not load the shift"
  },
  "Ошибка связи": {
    "kg": "Байланыш катасы",
    "kz": "Байланыс қатесі",
    "en": "Connection error"
  },
  "Задачу уже забрал другой сотрудник": {
    "kg": "Тапшырманы башка кызматкер алып койгон",
    "kz": "Тапсырманы басқа қызметкер алып қойған",
    "en": "Another staff member already took this task"
  },
  "Ошибка операции": {
    "kg": "Операция катасы",
    "kz": "Операция қатесі",
    "en": "Operation error"
  },
  "Уборка выполнена, номер готов к проверке.": {
    "kg": "Тазалоо бүттү, бөлмө текшерүүгө даяр.",
    "kz": "Тазалау аяқталды, бөлме тексеруге дайын.",
    "en": "Cleaning completed; the room is ready for inspection."
  },
  "Ремонт выполнен.": {
    "kg": "Оңдоо бүттү.",
    "kz": "Жөндеу аяқталды.",
    "en": "Repair completed."
  },
  "Отметьте все пункты чек-листа перед сдачей номера.": {
    "kg": "Бөлмөнү өткөрөрдөн мурда чек-листтин бардык пункттарын белгилеңиз.",
    "kz": "Бөлмені тапсырар алдында чек-парақтың барлық тармағын белгілеңіз.",
    "en": "Complete every checklist item before submitting the room."
  },
  "Не удалось сдать работу": {
    "kg": "Ишти тапшыруу мүмкүн болгон жок",
    "kz": "Жұмысты тапсыру мүмкін болмады",
    "en": "Could not submit the work"
  },
  "Ошибка сдачи работы": {
    "kg": "Ишти тапшыруу катасы",
    "kz": "Жұмысты тапсыру қатесі",
    "en": "Work submission error"
  },
  "Новые задачи появятся автоматически.": {
    "kg": "Жаңы тапшырмалар автоматтык түрдө пайда болот.",
    "kz": "Жаңа тапсырмалар автоматты түрде пайда болады.",
    "en": "New tasks will appear automatically."
  },
  "Переключитесь на другой раздел.": {
    "kg": "Башка бөлүмгө өтүңүз.",
    "kz": "Басқа бөлімге ауысыңыз.",
    "en": "Switch to another section."
  },
  "Общая задача": {
    "kg": "Жалпы тапшырма",
    "kz": "Жалпы тапсырма",
    "en": "General task"
  },
  "Принять": {
    "kg": "Кабыл алуу",
    "kz": "Қабылдау",
    "en": "Accept"
  },
  "Готовить": {
    "kg": "Даярдоо",
    "kz": "Дайындау",
    "en": "Cook"
  },
  "Не используется": {
    "kg": "Колдонулбайт",
    "kz": "Қолданылмайды",
    "en": "Not used"
  },
  "Ошибка MARINA SMART": {
    "kg": "MARINA SMART катасы",
    "kz": "MARINA SMART қатесі",
    "en": "MARINA SMART error"
  },
  "Добавьте хотя бы одну утверждённую позицию": {
    "kg": "Жок дегенде бир бекитилген позиция кошуңуз",
    "kz": "Кемінде бір бекітілген позиция қосыңыз",
    "en": "Add at least one approved item"
  },
  "Ошибка заказа": {
    "kg": "Буйрутма катасы",
    "kz": "Тапсырыс қатесі",
    "en": "Order error"
  },
  "Ошибка статуса": {
    "kg": "Статус катасы",
    "kz": "Күй қатесі",
    "en": "Status error"
  },
  "Ошибка стола": {
    "kg": "Стол катасы",
    "kz": "Үстел қатесі",
    "en": "Table error"
  },
  "Ошибка меню": {
    "kg": "Меню катасы",
    "kz": "Мәзір қатесі",
    "en": "Menu error"
  },
  "Ошибка заезда": {
    "kg": "Кирүү катасы",
    "kz": "Келу қатесі",
    "en": "Arrival error"
  },
  "Только просмотр": {
    "kg": "Көрүү гана",
    "kz": "Тек қарау",
    "en": "View only"
  },
  "черновик": {
    "kg": "черновик",
    "kz": "нобай",
    "en": "draft"
  },
  "опубликовано": {
    "kg": "жарыяланды",
    "kz": "жарияланды",
    "en": "published"
  },
  "В меню": {
    "kg": "Менюда",
    "kz": "Мәзірде",
    "en": "In menu"
  },
  "Скрыто": {
    "kg": "Жашырылган",
    "kz": "Жасырылған",
    "en": "Hidden"
  },
  "Опубликовать": {
    "kg": "Жарыялоо",
    "kz": "Жариялау",
    "en": "Publish"
  },
  "Вернуть в черновик": {
    "kg": "Черновикке кайтаруу",
    "kz": "Нобайға қайтару",
    "en": "Return to draft"
  },
  "Активно": {
    "kg": "Активдүү",
    "kz": "Белсенді",
    "en": "Active"
  },
  "Не удалось загрузить план питания": {
    "kg": "Тамактануу планын жүктөө мүмкүн болгон жок",
    "kz": "Тамақтану жоспарын жүктеу мүмкін болмады",
    "en": "Could not load the meal plan"
  },
  "Время этого приёма пищи ещё не настроено. Зафиксировать производственный план вручную?": {
    "kg": "Бул тамактануу убактысы али жөндөлгөн эмес. Өндүрүш планын кол менен бекитесизби?",
    "kz": "Бұл тамақтану уақыты әлі бапталмаған. Өндірістік жоспарды қолмен бекітесіз бе?",
    "en": "This meal time is not configured yet. Freeze the production plan manually?"
  },
  "До штатного cutoff ещё есть время. Зафиксировать производственный план досрочно?": {
    "kg": "Кадимки cutoff убактысына чейин дагы убакыт бар. Өндүрүш планын эрте бекитесизби?",
    "kz": "Қалыпты cutoff уақытына дейін әлі уақыт бар. Өндірістік жоспарды ертерек бекітесіз бе?",
    "en": "The regular cutoff has not been reached yet. Freeze the production plan early?"
  },
  "Не удалось зафиксировать план кухни": {
    "kg": "Ашкана планын бекитүү мүмкүн болгон жок",
    "kz": "Асүй жоспарын бекіту мүмкін болмады",
    "en": "Could not freeze the kitchen plan"
  },
  "СЕГОДНЯ": {
    "kg": "БҮГҮН",
    "kz": "БҮГІН",
    "en": "TODAY"
  },
  "ДАТА": {
    "kg": "КҮН",
    "kz": "КҮН",
    "en": "DATE"
  },
  "Изменений после фиксации нет": {
    "kg": "Бекитилгенден кийин өзгөрүү жок",
    "kz": "Бекітілгеннен кейін өзгеріс жоқ",
    "en": "No changes after freeze"
  },
  "Время приёма пищи не настроено — автоматический cutoff недоступен.": {
    "kg": "Тамактануу убактысы жөндөлгөн эмес — автоматтык cutoff жеткиликсиз.",
    "kz": "Тамақтану уақыты бапталмаған — автоматты cutoff қолжетімсіз.",
    "en": "Meal time is not configured — automatic cutoff is unavailable."
  },
  "Cutoff достигнут — план можно зафиксировать.": {
    "kg": "Cutoff жетти — планды бекитсе болот.",
    "kz": "Cutoff жетті — жоспарды бекітуге болады.",
    "en": "Cutoff reached — the plan can be frozen."
  },
  "Фиксирую…": {
    "kg": "Бекитип жатам…",
    "kz": "Бекітіп жатырмын…",
    "en": "Freezing…"
  },
  "Зафиксировать план": {
    "kg": "Планды бекитүү",
    "kz": "Жоспарды бекіту",
    "en": "Freeze plan"
  },
  "Зафиксировать вручную": {
    "kg": "Кол менен бекитүү",
    "kz": "Қолмен бекіту",
    "en": "Freeze manually"
  },
  "Зафиксировать досрочно": {
    "kg": "Эрте бекитүү",
    "kz": "Ертерек бекіту",
    "en": "Freeze early"
  },
  "Весь день / другое": {
    "kg": "Күн бою / башка",
    "kz": "Күні бойы / басқа",
    "en": "All day / other"
  },
  "Ошибка Resort Core": {
    "kg": "Resort Core катасы",
    "kz": "Resort Core қатесі",
    "en": "Resort Core error"
  },
  "Нет доступа к меню кухни": {
    "kg": "Ашкана менюсуна кирүү укугу жок",
    "kz": "Асүй мәзіріне қолжетімділік жоқ",
    "en": "No access to the kitchen menu"
  },
  "Не удалось загрузить меню": {
    "kg": "Менюну жүктөө мүмкүн болгон жок",
    "kz": "Мәзірді жүктеу мүмкін болмады",
    "en": "Could not load the menu"
  },
  "Выберите хотя бы одно подтверждённое блюдо для публикации.": {
    "kg": "Жарыялоо үчүн жок дегенде бир бекитилген тамакты тандаңыз.",
    "kz": "Жариялау үшін кемінде бір бекітілген тағамды таңдаңыз.",
    "en": "Select at least one approved dish to publish."
  },
  "Не удалось опубликовать меню": {
    "kg": "Менюну жарыялоо мүмкүн болгон жок",
    "kz": "Мәзірді жариялау мүмкін болмады",
    "en": "Could not publish the menu"
  },
  "Не удалось изменить доступность": {
    "kg": "Жеткиликтүүлүктү өзгөртүү мүмкүн болгон жок",
    "kz": "Қолжетімділікті өзгерту мүмкін болмады",
    "en": "Could not change availability"
  },
  "Публикую…": {
    "kg": "Жарыялап жатам…",
    "kz": "Жариялап жатырмын…",
    "en": "Publishing…"
  },
  "Вернуть в продажу": {
    "kg": "Сатууга кайтаруу",
    "kz": "Сатылымға қайтару",
    "en": "Return to sale"
  },
  "Стоп-лист": {
    "kg": "Стоп-лист",
    "kz": "Стоп-лист",
    "en": "Stop list"
  },
  "Скрыть": {
    "kg": "Жашыруу",
    "kz": "Жасыру",
    "en": "Hide"
  },
  "Показать": {
    "kg": "Көрсөтүү",
    "kz": "Көрсету",
    "en": "Show"
  },
  "Другое": {
    "kg": "Башка",
    "kz": "Басқа",
    "en": "Other"
  },
  "Ошибка Dining Floor": {
    "kg": "Dining Floor катасы",
    "kz": "Dining Floor қатесі",
    "en": "Dining Floor error"
  },
  "Не удалось загрузить схему зала": {
    "kg": "Залдын схемасын жүктөө мүмкүн болгон жок",
    "kz": "Зал сызбасын жүктеу мүмкін болмады",
    "en": "Could not load the floor plan"
  },
  "Основной зал": {
    "kg": "Негизги зал",
    "kz": "Негізгі зал",
    "en": "Main hall"
  },
  "Не удалось сохранить позицию стола": {
    "kg": "Столдун ордун сактоо мүмкүн болгон жок",
    "kz": "Үстел орнын сақтау мүмкін болмады",
    "en": "Could not save table position"
  },
  "✓ Завершить расстановку": {
    "kg": "✓ Жайгаштырууну бүтүрүү",
    "kz": "✓ Орналастыруды аяқтау",
    "en": "✓ Finish layout"
  },
  "Расставить столы": {
    "kg": "Столдорду жайгаштыруу",
    "kz": "Үстелдерді орналастыру",
    "en": "Arrange tables"
  },
  "Все зоны": {
    "kg": "Бардык аймактар",
    "kz": "Барлық аймақтар",
    "en": "All zones"
  },
  "ГОСТЬ ЗА СТОЛОМ": {
    "kg": "КОНОК СТОЛДО",
    "kz": "ҚОНАҚ ҮСТЕЛДЕ",
    "en": "GUEST SEATED"
  },
  "ОЖИДАЕТ": {
    "kg": "КҮТҮҮДӨ",
    "kz": "КҮТУДЕ",
    "en": "WAITING"
  },
  "Приём не указан": {
    "kg": "Тамактануу көрсөтүлгөн эмес",
    "kz": "Тамақтану көрсетілмеген",
    "en": "Meal not specified"
  },
  "Официант не назначен": {
    "kg": "Официант дайындалган эмес",
    "kz": "Даяшы тағайындалмаған",
    "en": "Waiter not assigned"
  },
  "Сохранить параметры": {
    "kg": "Параметрлерди сактоо",
    "kz": "Параметрлерді сақтау",
    "en": "Save settings"
  },
  "Перетаскивайте столы прямо по схеме. Позиция сохраняется при отпускании.": {
    "kg": "Столдорду схема боюнча түз жылдырыңыз. Коё бергенде орду сакталат.",
    "kz": "Үстелдерді сызбада тікелей жылжытыңыз. Босатқанда орны сақталады.",
    "en": "Drag tables directly on the floor plan. Position is saved when released."
  },
  "Включите «Расставить столы», чтобы перетаскивать их мышкой или пальцем.": {
    "kg": "Столдорду чычкан же манжа менен жылдыруу үчүн «Столдорду жайгаштыруу» режимин күйгүзүңүз.",
    "kz": "Үстелдерді тышқанмен немесе саусақпен жылжыту үшін «Үстелдерді орналастыру» режимін қосыңыз.",
    "en": "Enable Arrange tables to drag them with a mouse or finger."
  },
  "Забронирован": {
    "kg": "Брондолгон",
    "kz": "Броньдалған",
    "en": "Reserved"
  },
  "Гости за столом": {
    "kg": "Коноктор столдо",
    "kz": "Қонақтар үстелде",
    "en": "Guests seated"
  },
  "Не пришли": {
    "kg": "Келишкен жок",
    "kz": "Келмеді",
    "en": "No-show"
  },
  "Не удалось загрузить зал": {
    "kg": "Залды жүктөө мүмкүн болгон жок",
    "kz": "Залды жүктеу мүмкін болмады",
    "en": "Could not load the dining floor"
  },
  "Нет доступа": {
    "kg": "Кирүү укугу жок",
    "kz": "Қолжетімділік жоқ",
    "en": "Access denied"
  },
  "Для входа в зал нужна роль DINING_STAFF, MANAGER или OWNER.": {
    "kg": "Залга кирүү үчүн DINING_STAFF, MANAGER же OWNER ролу керек.",
    "kz": "Залға кіру үшін DINING_STAFF, MANAGER немесе OWNER рөлі қажет.",
    "en": "DINING_STAFF, MANAGER, or OWNER role is required to access the floor."
  },
  "Не удалось войти": {
    "kg": "Кирүү мүмкүн болгон жок",
    "kz": "Кіру мүмкін болмады",
    "en": "Could not sign in"
  },
  "Не удалось взять заказ": {
    "kg": "Буйрутманы алуу мүмкүн болгон жок",
    "kz": "Тапсырысты алу мүмкін болмады",
    "en": "Could not take the order"
  },
  "Не удалось закрыть выдачу": {
    "kg": "Берүүнү жабуу мүмкүн болгон жок",
    "kz": "Беруді жабу мүмкін болмады",
    "en": "Could not close service"
  },
  "Не удалось изменить бронь стола": {
    "kg": "Стол бронун өзгөртүү мүмкүн болгон жок",
    "kz": "Үстел бронін өзгерту мүмкін болмады",
    "en": "Could not change the table reservation"
  },
  "Не удалось забронировать стол": {
    "kg": "Столду брондоо мүмкүн болгон жок",
    "kz": "Үстелді броньдау мүмкін болмады",
    "en": "Could not reserve the table"
  },
  "Не удалось создать заказ": {
    "kg": "Буйрутма түзүү мүмкүн болгон жок",
    "kz": "Тапсырыс құру мүмкін болмады",
    "en": "Could not create the order"
  },
  "Войти в зал": {
    "kg": "Залга кирүү",
    "kz": "Залға кіру",
    "en": "Enter dining floor"
  },
  "Гость отеля": {
    "kg": "Мейманкана коногу",
    "kz": "Қонақүй қонағы",
    "en": "Hotel guest"
  },
  "Например: без лука": {
    "kg": "Мисалы: пиязсыз",
    "kz": "Мысалы: пиязсыз",
    "en": "For example: no onions"
  },
  "Приложите браслет или введите его UID.": {
    "kg": "Билерикти тийгизиңиз же UID киргизиңиз.",
    "kz": "Білезікті жақындатыңыз немесе UID енгізіңіз.",
    "en": "Tap the wristband or enter its UID."
  },
  "Не удалось прочитать баланс": {
    "kg": "Балансты окуу мүмкүн болгон жок",
    "kz": "Балансты оқу мүмкін болмады",
    "en": "Could not read balance"
  },
  "Ошибка чтения браслета": {
    "kg": "Билерикти окуу катасы",
    "kz": "Білезікті оқу қатесі",
    "en": "Wristband read error"
  },
  "NFC API недоступен в этом браузере. Введите UID браслета вручную или используйте поддерживаемое устройство.": {
    "kg": "Бул браузерде NFC API жеткиликсиз. Билериктин UID'ин кол менен киргизиңиз же колдоого алынган түзмөктү колдонуңуз.",
    "kz": "Бұл браузерде NFC API қолжетімсіз. Білезік UID кодын қолмен енгізіңіз немесе қолдау көрсетілетін құрылғыны пайдаланыңыз.",
    "en": "NFC API is unavailable in this browser. Enter the wristband UID manually or use a supported device."
  },
  "Не удалось прочитать браслет. Приложите его повторно.": {
    "kg": "Билерикти окуу мүмкүн болгон жок. Кайра тийгизиңиз.",
    "kz": "Білезікті оқу мүмкін болмады. Қайта жақындатыңыз.",
    "en": "Could not read the wristband. Tap it again."
  },
  "NFC-сканирование недоступно": {
    "kg": "NFC сканерлөө жеткиликсиз",
    "kz": "NFC сканерлеу қолжетімсіз",
    "en": "NFC scanning unavailable"
  },
  "Укажите целую сумму в сомах и сначала прочитайте баланс браслета.": {
    "kg": "Сом менен бүтүн сумманы көрсөтүп, адегенде билериктин балансын окуңуз.",
    "kz": "Соммен бүтін соманы көрсетіп, алдымен білезік балансын оқыңыз.",
    "en": "Enter a whole amount in som and read the wristband balance first."
  },
  "На браслете недостаточно средств.": {
    "kg": "Билерикте каражат жетишсиз.",
    "kz": "Білезікте қаражат жеткіліксіз.",
    "en": "Insufficient wristband balance."
  },
  "Списание отклонено": {
    "kg": "Эсептен чыгаруу четке кагылды",
    "kz": "Шегеру қабылданбады",
    "en": "Charge declined"
  },
  "Ошибка списания": {
    "kg": "Эсептен чыгаруу катасы",
    "kz": "Шегеру қатесі",
    "en": "Charge error"
  },
  "NFC готов": {
    "kg": "NFC даяр",
    "kz": "NFC дайын",
    "en": "NFC ready"
  },
  "Ручной UID": {
    "kg": "Кол менен UID",
    "kz": "Қолмен UID",
    "en": "Manual UID"
  },
  "Жду браслет…": {
    "kg": "Билерикти күтүп жатам…",
    "kz": "Білезікті күтіп тұрмын…",
    "en": "Waiting for wristband…"
  },
  "Приложить NFC": {
    "kg": "NFC тийгизүү",
    "kz": "NFC жақындату",
    "en": "Tap NFC"
  },
  "UID браслета": {
    "kg": "Билерик UID",
    "kz": "Білезік UID",
    "en": "Wristband UID"
  },
  "Баланс": {
    "kg": "Баланс",
    "kz": "Баланс",
    "en": "Balance"
  },
  "Сумма в KGS": {
    "kg": "KGS суммасы",
    "kz": "KGS сомасы",
    "en": "Amount in KGS"
  },
  "Услуга, например: гидроцикл 10 мин": {
    "kg": "Кызмат, мисалы: гидроцикл 10 мүн",
    "kz": "Қызмет, мысалы: гидроцикл 10 мин",
    "en": "Service, e.g. jet ski 10 min"
  },
  "Провожу…": {
    "kg": "Өткөрүп жатам…",
    "kz": "Өткізіп жатырмын…",
    "en": "Processing…"
  },
  "Повторить безопасно": {
    "kg": "Коопсуз кайталоо",
    "kz": "Қауіпсіз қайталау",
    "en": "Retry safely"
  },
  "Введите сумму": {
    "kg": "Сумманы киргизиңиз",
    "kz": "Соманы енгізіңіз",
    "en": "Enter amount"
  }
});

function translated(text: string, locale: Locale): string {
  if (locale === "ru") return text;
  const direct = COPY[text];
  if (direct) return direct[locale];
  const room = text.match(/^Номер\s+(.+)$/);
  if (room) return `${locale === "en" ? "Room" : locale === "kz" ? "Бөлме" : "Бөлмө"} ${room[1]}`;
  const waiter = text.match(/^Официант:\s*(.+)$/);
  if (waiter) return `${locale === "en" ? "Waiter" : locale === "kz" ? "Даяшы" : "Официант"}: ${waiter[1]}`;
  const tableSaved = text.match(/^Стол\s+(.+):\s+схема сохранена\.$/);
  if (tableSaved) return locale === "en" ? `Table ${tableSaved[1]}: layout saved.` : locale === "kz" ? `Үстел ${tableSaved[1]}: сызба сақталды.` : `Стол ${tableSaved[1]}: схема сакталды.`;
  const publishCount = text.match(/^Опубликовать:\s*(\d+)$/);
  if (publishCount) return locale === "en" ? `Publish: ${publishCount[1]}` : locale === "kz" ? `Жариялау: ${publishCount[1]}` : `Жарыялоо: ${publishCount[1]}`;
  const charge = text.match(/^Списать\s+(.+)\s+KGS$/);
  if (charge) return locale === "en" ? `Charge ${charge[1]} KGS` : locale === "kz" ? `${charge[1]} KGS шегеру` : `${charge[1]} KGS эсептен чыгаруу`;
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
