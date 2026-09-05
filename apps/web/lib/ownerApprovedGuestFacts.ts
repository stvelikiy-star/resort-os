export type GuestFactsLocale = "ru" | "kg" | "en";

export type GuestReviewCard = { title: string; text: string };
export type GuestServiceCard = { code: string; title: string; text: string; cta?: string; href?: string };
export type OwnerApprovedGuestFacts = {
  reviews: { eyebrow: string; title: string; intro: string; cards: GuestReviewCard[]; readCta: string; leaveCta: string };
  included: { title: string; text: string };
  services: { eyebrow: string; title: string; intro: string; cards: GuestServiceCard[] };
};

export const TWO_GIS_REVIEWS_URL = "https://2gis.kg/cholpon-ata/firm/70000001027860639/tab/reviews";
const MANAGER_WHATSAPP = "https://wa.me/996558085008";
const transferHref = (message: string) => `${MANAGER_WHATSAPP}?text=${encodeURIComponent(message)}`;

export const ownerApprovedGuestFacts: Record<GuestFactsLocale, OwnerApprovedGuestFacts> = {
  ru: {
    reviews: {
      eyebrow: "Отзывы гостей · 2ГИС",
      title: "Что гости говорят о Трёх Коронах",
      intro: "Актуальные оценки и отзывы гостей доступны в карточке отеля в 2ГИС. На сайте мы показываем только общие темы отзывов и не выдаём их за собственные оценки.",
      cards: [
        { title: "Питание", text: "В отзывах 2ГИС гости регулярно отмечают вкусную и разнообразную еду." },
        { title: "Чистота и территория", text: "Гости отмечают чистоту номеров, ухоженную территорию и спокойную атмосферу." },
        { title: "Пляж и бассейн", text: "Собственный пляж и бассейн часто упоминаются как важная часть отдыха." },
        { title: "Персонал", text: "В отзывах часто благодарят сотрудников за доброжелательность и помощь во время проживания." },
      ],
      readCta: "Читать отзывы в 2ГИС",
      leaveCta: "Оставить отзыв",
    },
    included: {
      title: "В базовой стоимости",
      text: "Wi‑Fi, собственный пляж, открытый бассейн, зонтики и шезлонги, бесплатная парковка для проживающих и настольный теннис. Питание зависит от выбранного тарифа или подключается дополнительно.",
    },
    services: {
      eyebrow: "Дополнительные услуги",
      title: "Соберите отдых под себя",
      intro: "Трансфер, питание и дополнительные услуги можно согласовать вместе с проживанием. Стоимость проживания в Core считается отдельно и не меняется автоматически из-за этих услуг.",
      cards: [
        { code: "TRANSFER", title: "Трансфер", text: "Манас: седан 6 500 / минивен 7 500 сом. Аэропорт Тамчы: седан 2 500 / минивен 3 500 сом. Бишкек: седан 5 500 / минивен 6 500 сом. Цена за автомобиль в одну сторону.", cta: "Заказать трансфер", href: transferHref("Здравствуйте! Хочу заказать трансфер в отель «Три Короны». Подскажите, пожалуйста, доступность.") },
        { code: "MEALS", title: "Трёхразовое питание", text: "Взрослый — 1 900 сом в день, ребёнок — 1 400 сом. Отдельно для взрослых: завтрак 500, обед 750, ужин 650 сом; для детей: 400 / 550 / 450 сом. Оплата в отеле." },
        { code: "PARKING", title: "Парковка", text: "Для проживающих парковка бесплатная. Ориентировочная вместимость — 20–30 автомобилей." },
        { code: "SAUNA", title: "Сауна", text: "Работает только в зимний период. 5 000 сом за 1 час, формат рассчитан на 4–5 человек." },
        { code: "BILLIARDS", title: "Бильярд", text: "500 сом за 1 час." },
        { code: "TABLE_TENNIS", title: "Настольный теннис", text: "Для проживающих — бесплатно." },
        { code: "EXCURSIONS", title: "Туры по Иссык-Кулю · сезон 2026", text: "Основные маршруты по прайсу MIX TOUR.KG: Семёновское ущелье + горячий источник — 2 000 сом/чел.; Джети-Огуз + горячий источник — 3 500; Мёртвое озеро + горячий источник — 3 000; Барскоонский водопад + ущелье Сказка + Джети-Огуз + Каракол (церковь и мечеть) + горячий источник — 4 500 сом/чел. Выезды ежедневно с 20 июня по 25 августа 2026 года. В цену входят трансфер и услуги гида; входные билеты, горячие источники, питание и дополнительные расходы оплачиваются отдельно.", cta: "Подобрать тур", href: transferHref("Здравствуйте! Хочу подобрать экскурсию или тур по Иссык-Кулю во время проживания в «Трёх Коронах».") },
        { code: "THERMAL_SPRINGS", title: "Термальные источники рядом", text: "Термальные источники находятся в шаговой доступности от отеля. Точный маршрут можно уточнить у администратора." },
        { code: "WATER_ACTIVITIES", title: "Водные активности на пляже", text: "Гидроциклы, парашют и другие сезонные развлечения могут быть доступны у независимых пляжных операторов. Это не услуги отеля: цены и доступность определяет оператор." },
        { code: "RULES", title: "Правила проживания", text: "Ключевые правила отеля, время выезда, порядок посещения гостями, уборки и условия отмены собраны на отдельной странице.", cta: "Открыть правила", href: "/rules" },
      ],
    },
  },
  kg: {
    reviews: {
      eyebrow: "Коноктордун пикирлери · 2ГИС",
      title: "Коноктор Үч Таажы жөнүндө эмне дешет",
      intro: "Учурдагы баалар жана коноктордун пикирлери 2ГИС картасында жеткиликтүү. Сайтта биз пикирлердин жалпы темаларын гана көрсөтөбүз.",
      cards: [
        { title: "Тамактануу", text: "2ГИС пикирлеринде коноктор даамдуу жана түрдүү тамактарды көп белгилешет." },
        { title: "Тазалык жана аймак", text: "Коноктор бөлмөлөрдүн тазалыгын, каралган аймакты жана тынч атмосфераны белгилешет." },
        { title: "Пляж жана бассейн", text: "Өз пляжы жана бассейн эс алуунун маанилүү бөлүгү катары көп айтылат." },
        { title: "Кызматкерлер", text: "Пикирлерде кызматкерлердин сылык мамилеси жана жардамы үчүн көп ыраазычылык айтылат." },
      ],
      readCta: "2ГИСтен пикирлерди окуу",
      leaveCta: "Пикир калтыруу",
    },
    included: { title: "Базалык баага кирет", text: "Wi‑Fi, өз пляжы, ачык бассейн, кол чатырлар жана шезлонгдор, жашоочулар үчүн акысыз унаа токтотуучу жай жана стол тенниси. Тамактануу тандалган тарифке жараша же кошумча кошулат." },
    services: {
      eyebrow: "Кошумча кызматтар",
      title: "Эс алууну өзүңүзгө ылайык түзүңүз",
      intro: "Трансфер, тамактануу жана кошумча кызматтар жашоо менен бирге макулдашылат. Алар бөлмөнүн Core баасын автоматтык түрдө өзгөртпөйт.",
      cards: [
        { code: "TRANSFER", title: "Трансфер", text: "Манас: седан 6 500 / минивэн 7 500 сом. Тамчы аэропорту: седан 2 500 / минивэн 3 500 сом. Бишкек: седан 5 500 / минивэн 6 500 сом. Баа бир тарапка бир унаа үчүн.", cta: "Трансфер заказ кылуу", href: transferHref("Саламатсызбы! «Үч Таажы» мейманканасына трансфер заказ кылгым келет.") },
        { code: "MEALS", title: "Үч маал тамак", text: "Чоң киши — күнүнө 1 900 сом, бала — 1 400 сом. Өзүнчө: чоңдор үчүн эртең мененки 500, түшкү 750, кечки 650 сом; балдар үчүн 400 / 550 / 450 сом. Төлөм мейманканада." },
        { code: "PARKING", title: "Унаа токтотуучу жай", text: "Жашоочулар үчүн акысыз. Болжолдуу сыйымдуулугу — 20–30 унаа." },
        { code: "SAUNA", title: "Сауна", text: "Кыш мезгилинде гана иштейт. 1 саат — 5 000 сом, 4–5 адамга ылайыктуу." },
        { code: "BILLIARDS", title: "Бильярд", text: "1 саат — 500 сом." },
        { code: "TABLE_TENNIS", title: "Стол тенниси", text: "Жашоочулар үчүн акысыз." },
        { code: "EXCURSIONS", title: "Ысык-Көл боюнча турлар · 2026", text: "MIX TOUR.KG прайсынан негизги багыттар: Семёнов капчыгайы + ысык булак — 2 000 сом/адам; Жети-Өгүз + ысык булак — 3 500; Өлүк көл + ысык булак — 3 000; Барскоон шаркыратмасы + Сказка капчыгайы + Жети-Өгүз + Каракол (чиркөө жана мечит) + ысык булак — 4 500 сом/адам. Каттамдар 2026-жылдын 20-июнунан 25-августуна чейин күн сайын. Баага трансфер жана гид кирет; кирүү билеттерин, ысык булактарды, тамактанууну жана кошумча чыгымдарды конок өзүнчө төлөйт.", cta: "Тур тандоо", href: transferHref("Саламатсызбы! «Үч Таажыда» жашаган учурда Ысык-Көл боюнча экскурсия же тур тандагым келет.") },
        { code: "THERMAL_SPRINGS", title: "Жакынкы термалдык булактар", text: "Термалдык булактар мейманканадан жөө жетчү аралыкта. Так маршрутту администратордон тактоого болот." },
        { code: "WATER_ACTIVITIES", title: "Пляждагы суу активдүүлүктөрү", text: "Гидроцикл, парашют жана башка сезондук көңүл ачуулар көз карандысыз пляж операторлорунда болушу мүмкүн. Бул мейманкананын кызматы эмес; баа жана жеткиликтүүлүктү оператор аныктайт." },
        { code: "RULES", title: "Жашоо эрежелери", text: "Мейманкананын негизги эрежелери, чыгуу убактысы, коноктордун келүүсү, тазалоо жана жокко чыгаруу шарттары өзүнчө баракта берилген.", cta: "Эрежелерди ачуу", href: "/rules" },
      ],
    },
  },
  en: {
    reviews: {
      eyebrow: "Guest reviews · 2GIS",
      title: "What guests say about Three Crowns",
      intro: "Current ratings and guest reviews are available on the hotel’s 2GIS listing. The website shows only broad review themes and does not present them as our own ratings.",
      cards: [
        { title: "Food", text: "2GIS reviews frequently mention tasty and varied meals." },
        { title: "Cleanliness and grounds", text: "Guests mention clean rooms, well-kept grounds and a calm atmosphere." },
        { title: "Beach and pool", text: "The private beach and pool are frequently mentioned as an important part of the stay." },
        { title: "Staff", text: "Reviews often thank the team for their friendly attitude and help during the stay." },
      ],
      readCta: "Read reviews on 2GIS",
      leaveCta: "Leave a review",
    },
    included: { title: "Included in the base stay", text: "Wi‑Fi, private beach, outdoor pool, umbrellas and sun loungers, free parking for staying guests and table tennis. Meals depend on the selected rate or can be added separately." },
    services: {
      eyebrow: "Additional services",
      title: "Build the stay around your plans",
      intro: "Transfers, meals and additional services can be arranged together with accommodation. They do not automatically change the Core room price.",
      cards: [
        { code: "TRANSFER", title: "Transfer", text: "Manas Airport: sedan 6,500 / minivan 7,500 KGS. Tamchy Airport: sedan 2,500 / minivan 3,500 KGS. Bishkek city: sedan 5,500 / minivan 6,500 KGS. Price is per vehicle, one way.", cta: "Order a transfer", href: transferHref("Hello! I would like to arrange a transfer to Three Crowns hotel.") },
        { code: "MEALS", title: "Three meals a day", text: "Adult — 1,900 KGS/day, child — 1,400 KGS/day. Separately for adults: breakfast 500, lunch 750, dinner 650 KGS; for children: 400 / 550 / 450 KGS. Payment is made at the hotel." },
        { code: "PARKING", title: "Parking", text: "Free for staying guests. Approximate capacity: 20–30 vehicles." },
        { code: "SAUNA", title: "Sauna", text: "Available in winter only. 5,000 KGS for 1 hour, intended for 4–5 guests." },
        { code: "BILLIARDS", title: "Billiards", text: "500 KGS per hour." },
        { code: "TABLE_TENNIS", title: "Table tennis", text: "Free for staying guests." },
        { code: "EXCURSIONS", title: "Issyk-Kul tours · 2026 season", text: "Selected routes from the MIX TOUR.KG price list: Semenovskoye Gorge + hot spring — 2,000 KGS/person; Jeti-Oguz + hot spring — 3,500; Dead Lake + hot spring — 3,000; Barskoon waterfall + Skazka Gorge + Jeti-Oguz + Karakol (church and mosque) + hot spring — 4,500 KGS/person. Departures run daily from 20 June to 25 August 2026. Transfer and guide services are included; admission tickets, hot-spring entry, meals and other additional expenses are paid separately.", cta: "Choose a tour", href: transferHref("Hello! I would like to choose an Issyk-Kul excursion or tour during my stay at Three Crowns.") },
        { code: "THERMAL_SPRINGS", title: "Thermal springs nearby", text: "Thermal springs are within walking distance of the hotel. The reception team can confirm the exact route." },
        { code: "WATER_ACTIVITIES", title: "Water activities on the beach", text: "Jet skis, parasailing and other seasonal activities may be offered by independent beach operators. These are not hotel services; price and availability are set by the operator." },
        { code: "RULES", title: "Hotel rules", text: "Key hotel rules, checkout time, visitor policy, housekeeping and cancellation terms are collected on a separate page.", cta: "View hotel rules", href: "/rules" },
      ],
    },
  },
};