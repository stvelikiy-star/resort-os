"use client";

import { useEffect } from "react";

import { getLocalizedRoomCopy, PublicLocale, resolveClientLocale, roomLocaleBySlug } from "../lib/publicLocale";

const HOME = {
  kg: {
    heroMeta: ["номер", "категория", "пирс", "бассейн"], scroll: "Баштоо",
    bookingTrust: ["Актуалдуу бош орундар", "Мезгилдин баасы", "Менеджердин жардамы"],
    help: ["Жардам керекпи?", "Номерди чогуу тандайбыз", "Ким келе турганын, канча күнгө жана кандай эс алууну каалаарыңызды жазыңыз. Менеджер категорияларды жана кошумча кызматтарды салыштырууга жардам берет.", "Чалуу · +996 558 08 50 02", "WhatsApp аркылуу жазуу ↗", "Маанилүү", "Өтүнмө жөнөтүлгөндөн кийин номер автоматтык түрдө кармалбайт. Ырасталган бронь шарттар жана алдын ала төлөм макулдашылгандан кийин менеджер тарабынан түзүлөт."],
    advantageIntro: "Курорттун артыкчылыктары жөн гана узун тизмек эмес. Алар бир күндүн табигый жүрүшүнө айланат: ойгонуу, аймакка чыгуу, көлгө жетүү, бассейнде эс алуу жана кечти SPA менен бүтүрүү.",
    advantages: [
      ["Ысык-Көлдүн биринчи линиясы", "Эс алуу көлдүн айланасында курулат: жээк, өз пляжы жана узун пирс курорттук маршруттун ичинде."],
      ["Өз пляжы", "Сууга жетүү үчүн өзүнчө жол пландаштыруунун кереги жок — пляж аймактын табигый уландысы."],
      ["150 метрлик пирс", "Курорттун негизги көркөм чекиттеринин бири: сейилдөө, Ысык-Көлдүн абасы жана ачык суу көрүнүшү."],
      ["SPA жана массаж", "Активдүү күндөн кийин тынч эс алууга жана калыбына келүүгө өтүүгө болот."],
      ["15×8 м бассейн", "Ачык бассейн көл жээгиндеги эс алууну толуктайт жана күндүзкү курорттук ритмге ылайыктуу."],
      ["Жайгашуунун 12 категориясы", "Компакттуу бир кишилик номерлерден эки бөлмөлүү варианттарга жана ашканасы бар апартаменттерге чейин."],
    ],
    rooms: ["Номерлер", "Бардык 12 категория.<br />Шашпай тандаңыз.", "Компакттуу бир кишилик варианттардан кең эки бөлмөлүү категорияларга жана апартаменттерге чейин. Сыйымдуулукту, аянтты жана сезондук бааны салыштырып, андан кийин категорияны ачып даталарды текшериңиз.", "Толук каталогду ачуу →", "Жогорку сезон", "сом / түн", "Категорияны көрүү →"],
    territory: ["Курорттун аймагы", "Биринчи кадамдан<br />пирстин аягына чейин", "Курорттун бардык маршрутун басып өтүңүз — жайгашуудан жана күндүзкү эс алуудан өз пляжына жана Ысык-Көлдүн ачык мейкиндигине чыккан узун пирске чейин.", "Үч Таажы · аймак", "Корпустар, жашыл аймак жана курорттун ички маршруту"],
    territoryJourney: [
      ["Келүү жана жайгашуу", "Эс алууну ашыкча түйшүксүз баштаңыз: категорияны алдын ала тандап, даталар боюнча бош орунду текшерип, деталдарды менеджер менен макулдашыңыз."],
      ["Курорттун аймагы", "Жайгашкандан кийин негизги эс алуу сценарийи бир аймакта: номер, бассейн, SPA жана көлгө жол."],
      ["Ачык бассейн", "15×8 м бассейн — сейилдөө жана сапарлардын ортосунда тынч эс алуу үчүн өзүнчө күндүзкү зона."],
      ["SPA жана массаж", "Кечинде активдүүлүктү калыбына келүү жана жайыраак ритм менен алмаштырууга болот."],
      ["Өз пляжы", "Жайкы күндүн негизги чекити — курорттон чыкпай эле Ысык-Көлдүн жээги."],
      ["150 метрлик пирс", "Маршруттун финалы — узун пирс, ачык суу жана Ысык-Көлдүн ошол өзгөчө масштабы."],
    ],
    amenitiesHead: ["Көл жана суу жээгиндеги эс алуу", "Ысык-Көл — ар бир<br />күндүн бир бөлүгү.", "Өз пляжы, 150 метрлик пирс жана ачык суу эс алуунун ритмин түзөт. Жээкте тынч күн өткөрсөңүз да, суудагы активдүүлүктү кошсоңуз да болот.", "Өз пляжы", "150 м пирс", "Ачык бассейн 15×8 м", "Даталарды текшерүү", "Ысык-Көл", "Пляж · пирс · суу · жайкы таасирлер"],
    amenities: [
      ["Суу жээгиндеги эс алуу", "Өз пляжы, 150 м пирс жана 15×8 м ачык бассейн курорттун ичинде толук суу сценарийин түзөт."],
      ["SPA & Recovery", "SPA жана массаж пляждагы эс алууну калыбына келүү жана тынч кеч менен толуктайт."],
      ["Үй-бүлөлөр үчүн", "Категориялардын кең тандоосу бир конокко, жупка же төрт кишиге чейинки үй-бүлөгө ылайыктуу вариант табууга мүмкүнчүлүк берет."],
      ["Узак жайгашуу", "Чоң аянттагы апартаменттер жана ашканасы бар категория бир-эки түндөн узак келгенде ыңгайлуу."],
      ["Менеджер менен байланыш", "Эгер өзүңүз тандоону каалабасаңыз, менеджер категорияны, даталарды жана кошумча кызматтарды тандоого жардам берет."],
      ["Ийкемдүү сценарий", "Тынч пляждык эс алууну, Ысык-Көл боюнча активдүү программаны же топтук сапарды өз максатыңызга ылайык түзүүгө болот."],
    ],
    reviewsHead: ["Коноктордун пикирлери", "Сапардан кийин<br />эмне эсте калат", "Пикирлерде коноктор көбүнчө көлгө жакын жайгашууну, өз пляжын, пирсти жана күндүн көп бөлүгүн бир курорттук мейкиндикте өткөрүү мүмкүнчүлүгүн белгилешет."],
    reviews: [
      ["Ысык-Көл жээгиндеги жайгашуу", "Коноктор суунун жанында жашап, пляжга күн сайын өзүнчө барууга убакыт коротпогонду өзгөчө баалашат."],
      ["Пляж жана пирс", "Өз жээги жана узун пирс — эс алуунун жана сапардагы сүрөттөрдүн эң эсте каларлык бөлүктөрүнүн бири."],
      ["Жайгашуу форматын тандоо", "Ар түрдүү категориялар жупка, үй-бүлөгө, компанияга же узагыраак эс алууга ылайыктуу вариант тандаганга жардам берет."],
      ["Курорттук ритм", "Көл, бассейн, SPA жана аймак бир күн ичинде активдүүлүк менен тынч эс алууну айкалыштырууга мүмкүнчүлүк берет."],
    ],
    extrasHead: ["Кошумча", "Эс алуу курорттун аймагы менен бүтпөйт", "Көбүрөөк таасир же мүмкүн болушунча жөнөкөй маршрут кааласаңыз, кошумча кызматтарды жашоо менен бирге макулдашса болот."],
    extras: [
      ["Экскурсиялар жана турлар", "Ысык-Көл боюнча сапарларды жана таасирлерди тандоого жардам беребиз. Так программа жана жеткиликтүүлүк кайрылганда ырасталат."],
      ["Трансфер", "Чолпон-Атага чейинки трансферди жана маршрутту алдын ала талкуулоого болот."],
      ["Такси жана сапарлар", "Жеке маршруттар үчүн менеджер транспорт маселесинде суроо боюнча жардам берет."],
      ["Суудагы активдүүлүк", "Сезонго жараша жеткиликтүү суудагы көңүл ачууларды жана сейилдөөлөрдү келердин алдында тактоого болот."],
    ],
    groupCta: "Топтук келүүнү талкуулоо",
    groups: [
      ["Корпоративдик келүүлөр", "Команданы жайгаштыруу, уюштуруучу менен бирдиктүү байланыш жана болуу программасын макулдашуу."],
      ["Спорттук жыйындар", "Топтун курамына ылайык номерлерди тандап, жашоо жана тамактануу режимин алдын ала талкуулайбыз."],
      ["Атайын меню", "Спорттук жана уюштурулган топтор үчүн рационго жана тамактануу графигине өзүнчө талаптарды алдын ала талкуулоого болот."],
      ["Топтор жана иш-чаралар", "Жайгашууну, тамактанууну, трансферди жана кошумча активдүүлүктү бир түшүнүктүү программага чогултууга жардам беребиз."],
    ],
    contacts: ["Байланыш жана жол", "Чолпон-Ата.<br />Ысык-Көлдүн жээги.", "Брондоо", "WhatsApp / менеджер", "Email", "Сапар алдында", "Байланыштарды сактап коюңуз — калганын уюштурууга жардам беребиз", "Номер тандоо, топтук жайгашуу, трансфер же Ысык-Көл боюнча кошумча программа керек болсо, менеджерге жазыңыз.", "Даталарды тандоо", "Google Maps ачуу ↗"],
    final: ["Үч Таажы · Resort & SPA", "Даталарды тандаңыз.<br />Ысык-Көл күтүп жатат.", "Бош категорияларды жана сиздин мезгилге жашоонун баасын текшериңиз.", "Номерлерди текшерүү"],
    footer: ["Үч Таажы · Resort & SPA", "Номерлер", "Аймак", "Топторго", "Байланыш"], mobileBook: "Бош номерлерди текшерүү",
  },
  en: {
    heroMeta: ["rooms", "categories", "pier", "pool"], scroll: "Start",
    bookingTrust: ["Live availability", "Full-stay price", "Manager support"],
    help: ["Need help?", "We’ll choose the room together", "Tell us who is travelling, for how long and what kind of stay you want. A manager will help compare categories and additional services.", "Call · +996 558 08 50 02", "Message on WhatsApp ↗", "Important", "Submitting a request does not automatically hold a room. A confirmed reservation is created by a manager after the terms and prepayment are agreed."],
    advantageIntro: "The resort advantages are not just a long feature list. They form the natural flow of a day: wake up, step outside, walk to the lake, relax by the pool and finish the evening at the SPA.",
    advantages: [
      ["First line of Issyk-Kul", "The stay is built around the lake: shoreline, private beach and long pier are all part of the resort route."],
      ["Private beach", "No separate trip to the water is needed — the beach is a natural extension of the resort grounds."],
      ["150-metre pier", "One of the resort’s signature viewpoints for walks, Issyk-Kul air and open-water views."],
      ["SPA and massage", "After an active day, switch to a calmer pace and recovery."],
      ["15×8 m pool", "The outdoor pool complements the lakeside stay and suits the daytime resort rhythm."],
      ["12 accommodation categories", "From compact single rooms to two-room categories and apartments with a kitchen."],
    ],
    rooms: ["Room collection", "All 12 categories.<br />Choose at your pace.", "From compact single options to spacious two-room categories and apartments. Compare capacity, area and seasonal rates, then open a category and check your dates.", "Open full catalogue →", "High season", "KGS / night", "View category →"],
    territory: ["Resort grounds", "From the first step<br />to the end of the pier", "Follow the full resort route — from check-in and daytime relaxation to the private beach and the long pier extending into the open space of Issyk-Kul.", "Three Crowns · grounds", "Buildings, greenery and the resort’s internal route"],
    territoryJourney: [
      ["Arrival and check-in", "Start the stay without unnecessary friction: choose a category in advance, check availability for your dates and coordinate details with the manager."],
      ["Resort grounds", "After check-in, the main stay experience unfolds within one area — room, pool, SPA and the path to the water."],
      ["Outdoor pool", "The 15×8 m pool is a separate daytime zone for relaxed time between walks and trips."],
      ["SPA and massage", "In the evening, switch from activity to recovery and a slower pace."],
      ["Private beach", "The main summer-day destination is the Issyk-Kul shore without leaving the resort."],
      ["150-metre pier", "The route ends with the long pier, open water and the scale of Issyk-Kul that brings people back."],
    ],
    amenitiesHead: ["Lake and waterfront", "Issyk-Kul is part of<br />every day.", "A private beach, a 150-metre pier and open water set the rhythm of the stay. Spend a quiet day by the shore or add more movement and water experiences.", "Private beach", "150 m pier", "Outdoor pool 15×8 m", "Check dates", "Issyk-Kul", "Beach · pier · water · summer experiences"],
    amenities: [
      ["Waterfront time", "A private beach, 150 m pier and 15×8 m outdoor pool create a complete waterfront experience inside the resort."],
      ["SPA & Recovery", "SPA and massage add recovery and a calm evening to a beach-focused stay."],
      ["For families", "A broad room mix makes it possible to choose accommodation for one guest, a couple or a family of up to four."],
      ["Longer stays", "Larger apartments and the kitchen category are practical when you stay for more than one or two nights."],
      ["Manager support", "If you prefer not to compare everything yourself, a manager can help choose a category, dates and additional services."],
      ["Flexible stay", "Build a quiet beach holiday, an active Issyk-Kul programme or a group trip around your needs."],
    ],
    reviewsHead: ["Guest reviews", "What stays with you<br />after the trip", "Guests most often highlight the lakeside location, private beach, pier and the ability to spend most of the day inside one resort environment."],
    reviews: [
      ["Issyk-Kul location", "Guests especially value staying close to the water without spending their holiday on daily trips to the beach."],
      ["Beach and pier", "The private shoreline and long pier are among the most memorable parts of the stay and its photos."],
      ["Choice of accommodation", "Different categories help match the stay to a couple, family, group of friends or a longer holiday."],
      ["Resort rhythm", "The lake, pool, SPA and grounds let you alternate activity and quiet time throughout the day."],
    ],
    extrasHead: ["More", "The experience goes beyond the grounds", "If you want more experiences or the simplest possible journey, additional services can be coordinated together with your stay."],
    extras: [
      ["Excursions and tours", "We can help choose trips and experiences around Issyk-Kul. Specific programmes and availability are confirmed on request."],
      ["Transfer", "Discuss the transfer and route to Cholpon-Ata in advance so the journey to the hotel is organised too."],
      ["Taxi and local trips", "For individual routes, the manager can assist with transport on request."],
      ["Water activities", "Seasonal water activities and boat options can be checked shortly before arrival."],
    ],
    groupCta: "Discuss a group stay",
    groups: [
      ["Corporate stays", "Team accommodation, one communication channel with the organiser and coordination of the stay programme."],
      ["Sports camps", "We match room inventory to the group and discuss accommodation and meal schedules in advance."],
      ["Special menu", "For sports and organised groups, dietary requirements and meal timing can be discussed in advance."],
      ["Groups and events", "We help combine accommodation, meals, transfer and additional activities into one clear programme."],
    ],
    contacts: ["Contacts and directions", "Cholpon-Ata.<br />The Issyk-Kul shore.", "Reservations", "WhatsApp / manager", "Email", "Before your trip", "Save the contacts — we’ll help organise the rest", "Message the manager if you need room selection, group accommodation, transfer or an additional Issyk-Kul programme.", "Choose dates", "Open Google Maps ↗"],
    final: ["Three Crowns · Resort & SPA", "Choose your dates.<br />Issyk-Kul is waiting.", "Check available categories and the stay price for your dates.", "Check rooms"],
    footer: ["Three Crowns · Resort & SPA", "Rooms", "Resort", "Groups", "Contacts"], mobileBook: "Check available rooms",
  },
};

const ROOMS_PAGE = {
  kg: {
    hero: ["Жайгашуу · 12 категория", "Сиздин эс алуу<br />ритмиңизге ылайык номер", "Бир-эки конок үчүн компакттуу варианттардан кең эки бөлмөлүү категорияларга жана апартаменттерге чейин. Форматты, бааны салыштырып, даталарыңызга эмне бош экенин текшериңиз.", "Категорияларды көрүү", "Даталарды текшерүү"],
    catalog: ["Каталог", "12 категория.<br />Өзүңүздүкүн тандаңыз.", "Сыйымдуулукту, аянтты жана сезондук бааны салыштырыңыз. Конкреттүү жайгашуунун деталдарын жана кошумча орундарды бронду ырастоодон мурун менеджерден тактоого болот.", "Жогорку сезон", "сом / түн", "Категория жөнүндө толук →"],
    truth: [["Баасы даталарга жараша өзгөрөт.", "Сезондук прайс категорияларды салыштырууга жардам берет, ал эми бүт мезгилдин так суммасы тандалган даталар текшерилгенден кийин көрсөтүлөт."], ["Өтүнмө ≠ ырасталган бронь.", "Өтүнмө жөнөтүлгөндөн кийин номер автоматтык түрдө кармалбайт. Менеджер шарттарды жана алдын ала төлөмдү макулдашат; активдүү бронь менеджер ырастагандан кийин гана пайда болот."]],
    footer: "Брондоо: +996 558 08 50 02",
  },
  en: {
    hero: ["Accommodation · 12 categories", "A room for your<br />holiday rhythm", "From compact options for one or two guests to spacious two-room categories and apartments. Compare the format and price, then check what is free for your dates.", "Browse categories", "Check dates"],
    catalog: ["Catalogue", "12 categories.<br />Choose yours.", "Compare capacity, area and seasonal rates. Details of the exact room and extra-bed options can be confirmed with the manager before the reservation is finalised.", "High season", "KGS / night", "Category details →"],
    truth: [["Price depends on dates.", "Seasonal rates help compare categories; the exact full-stay amount is shown after checking your chosen dates."], ["Request ≠ confirmed reservation.", "Submitting a request does not automatically hold a room. The manager agrees the terms and prepayment; an active reservation appears only after manager confirmation."]],
    footer: "Reservations: +996 558 08 50 02",
  },
};

const ROOM_DETAIL = {
  kg: {
    back: "← Бардык категориялар", category: "Категория", availability: "Бош орун — тандалган даталар боюнча", eyebrow: "Категория жөнүндө", title: "Көл жээгиндеги<br />сиздин эс алуу форматы", tail: "Брондоодон мурун менеджер конкреттүү номердин деталдарын жана керек болсо кошумча орундарды тактоого жардам берет.", placement: "Жайгашуу", area: "Аянты", how: "Кантип брондоо керек", safety: "Төмөндө даталарды тандап, бош орунду жана акыркы сумманы көрүңүз. Жөнөтүлгөн өтүнмө номерди автоматтык түрдө кармабайт: ырасталган бронь шарттар жана алдын ала төлөм макулдашылгандан кийин менеджер тарабынан түзүлөт.", summer: "Жайкы прайс · 2026", periods: ["1-июнь — 6-июль", "7-июль — 25-август", "26-август — 15-сентябрь"], note: "Баасы сезондук мезгил боюнча номер / түн үчүн көрсөтүлгөн. Бүт эс алуунун так суммасы даталарды тандагандан кийин эсептелет.", cta: "Даталарды текшерүү", footer: "Брондоо: +996 558 08 50 02",
  },
  en: {
    back: "← All categories", category: "Category", availability: "Availability — for your selected dates", eyebrow: "About this category", title: "Your way to stay<br />by the lake", tail: "Before booking, the manager can help confirm details of the exact room and any extra-bed requirements.", placement: "Accommodation", area: "Area", how: "How to book", safety: "Choose dates below to see availability and the full price. A submitted request does not automatically hold the room: a confirmed reservation is created by the manager after the terms and prepayment are agreed.", summer: "Summer rates · 2026", periods: ["1 June — 6 July", "7 July — 25 August", "26 August — 15 September"], note: "The price is per room / night for the seasonal period. The exact full-stay total is calculated after you choose dates.", cta: "Check dates", footer: "Reservations: +996 558 08 50 02",
  },
};

function setText(selector: string, value: string | undefined, root: ParentNode = document) {
  if (!value) return;
  const el = root.querySelector<HTMLElement>(selector);
  if (el) el.textContent = value;
}

function setHtml(selector: string, value: string | undefined, root: ParentNode = document) {
  if (!value) return;
  const el = root.querySelector<HTMLElement>(selector);
  if (el) el.innerHTML = value;
}

function setPairCards(selector: string, values: string[][], titleSelector: string, textSelector: string) {
  document.querySelectorAll<HTMLElement>(selector).forEach((card, index) => {
    const copy = values[index % values.length];
    if (!copy) return;
    setText(titleSelector, copy[0], card);
    setText(textSelector, copy[1], card);
  });
}

function relabelPrice(root: ParentNode, suffix: string) {
  const strong = root.querySelector<HTMLElement>("strong");
  if (!strong) return;
  const number = strong.textContent?.match(/[\d\s.,]+/)?.[0]?.trim();
  if (number) strong.textContent = `${number} ${suffix}`;
}

function localizeHome(locale: "kg" | "en") {
  const c = HOME[locale];
  document.querySelectorAll<HTMLElement>(".v3-hero-meta span").forEach((el, index) => {
    const b = el.querySelector("b");
    if (b && c.heroMeta[index]) el.innerHTML = `${b.outerHTML} ${c.heroMeta[index]}`;
  });
  setText(".v3-scroll-cue span", c.scroll);
  document.querySelectorAll<HTMLElement>(".v3-booking-trust span").forEach((el, index) => { if (c.bookingTrust[index]) el.textContent = c.bookingTrust[index]; });
  setText(".v3-booking-help .eyebrow", c.help[0]); setText(".v3-booking-help h3", c.help[1]); setText(".v3-booking-help > div:first-child > p:last-child", c.help[2]);
  document.querySelectorAll<HTMLElement>(".v3-help-actions a").forEach((el, index) => { if (c.help[3 + index]) el.textContent = c.help[3 + index]; });
  setText(".v3-booking-rule strong", c.help[5]); setText(".v3-booking-rule p", c.help[6]);
  setText(".v3-advantages .v3-section-head > p", c.advantageIntro);
  setPairCards(".v3-advantage-card", c.advantages, "h3", "p");
  setText(".v3-rooms .v3-section-head .eyebrow", c.rooms[0]); setHtml("#rooms-title", c.rooms[1]); setText(".v3-rooms .v3-section-head > div:last-child > p", c.rooms[2]); setText(".v3-rooms .v3-section-head .text-link", c.rooms[3]);
  const roomSlugs = Object.keys(roomLocaleBySlug);
  document.querySelectorAll<HTMLElement>(".v3-room-card").forEach((card, index) => {
    const copy = getLocalizedRoomCopy(roomSlugs[index], locale); if (!copy) return;
    const meta = card.querySelectorAll<HTMLElement>(".v3-room-card-top span"); if (meta[1]) { const area = meta[1].textContent?.split("·").slice(1).join("·").trim(); meta[1].textContent = `${copy.capacity}${area ? ` · ${area}` : ""}`; }
    setText("h3", copy.name, card); setText(".v3-room-card-body > p", copy.summary, card); setText(".v3-room-card-price small", c.rooms[4], card); relabelPrice(card.querySelector(".v3-room-card-price") ?? card, c.rooms[5]); setText(".v3-room-card-body > b", c.rooms[6], card);
  });
  setText(".v3-territory .v3-section-head .eyebrow", c.territory[0]); setHtml("#territory-title", c.territory[1]); setText(".v3-territory .v3-section-head > p", c.territory[2]); setText(".v3-film-caption span", c.territory[3]); setText(".v3-film-caption strong", c.territory[4]);
  setPairCards(".v3-territory-route article", c.territoryJourney, "h3", "p");
  const ah = c.amenitiesHead; setText(".v3-amenities-copy .eyebrow", ah[0]); setHtml("#amenities-title", ah[1]); setText(".v3-amenities-copy .lead", ah[2]); document.querySelectorAll<HTMLElement>(".v3-water-tags span").forEach((el, i) => { if (ah[3 + i]) el.textContent = ah[3 + i]; }); setText(".v3-amenities-copy .button", ah[6]); setText(".v3-lake-film figcaption span", ah[7]); setText(".v3-lake-film figcaption strong", ah[8]);
  setPairCards(".v3-amenity-grid article", c.amenities, "h3", "p");
  setText(".v3-reviews .v3-section-head .eyebrow", c.reviewsHead[0]); setHtml("#reviews-title", c.reviewsHead[1]); setText(".v3-reviews .v3-section-head > p", c.reviewsHead[2]); setPairCards(".v3-review-grid article", c.reviews, "h3", "p");
  setText(".v3-extra-heading .eyebrow", c.extrasHead[0]); setText(".v3-extra-heading h3", c.extrasHead[1]); setText(".v3-extra-heading > p:last-child", c.extrasHead[2]); setPairCards(".v3-extra-grid article", c.extras, "h4", "p");
  setText(".v3-groups-intro .button", c.groupCta); setPairCards(".v3-group-grid article", c.groups, "h3", "p");
  setText(".v3-contact-head .eyebrow", c.contacts[0]); setHtml("#contacts-title", c.contacts[1]); document.querySelectorAll<HTMLElement>(".v3-contact-actions a span").forEach((el, i) => { if (c.contacts[2 + i]) el.textContent = c.contacts[2 + i]; }); setText(".v3-arrival-card .eyebrow", c.contacts[5]); setText(".v3-arrival-card h3", c.contacts[6]); setText(".v3-arrival-card > p:not(.eyebrow)", c.contacts[7]); setText(".v3-arrival-card .button", c.contacts[8]); setText(".v3-arrival-card .text-link", c.contacts[9]);
  setText(".v3-final-cta .eyebrow", c.final[0]); setHtml(".v3-final-cta h2", c.final[1]); setText(".v3-final-cta .v3-final-layout > div:last-child > p", c.final[2]); setText(".v3-final-cta .button", c.final[3]);
  setText(".home-footer-inner > strong", c.footer[0]); document.querySelectorAll<HTMLElement>(".home-footer-links a").forEach((el, i) => { if (c.footer[1 + i]) el.textContent = c.footer[1 + i]; }); setText(".mobile-book", c.mobileBook);
}

function localizeRoomsIndex(locale: "kg" | "en") {
  const c = ROOMS_PAGE[locale];
  setText(".rooms-hero-content .eyebrow", c.hero[0]); setHtml("#rooms-page-title", c.hero[1]); setText(".rooms-hero-copy", c.hero[2]); document.querySelectorAll<HTMLElement>(".rooms-hero-actions a").forEach((el, i) => { if (c.hero[3 + i]) el.textContent = c.hero[3 + i]; });
  setText(".catalog-heading .eyebrow", c.catalog[0]); setHtml("#catalog-title", c.catalog[1]); setText(".catalog-heading > p", c.catalog[2]);
  const slugs = Object.keys(roomLocaleBySlug);
  document.querySelectorAll<HTMLElement>(".room-catalog-card").forEach((card, index) => {
    const copy = getLocalizedRoomCopy(slugs[index], locale); if (!copy) return;
    const meta = card.querySelector<HTMLElement>(".room-catalog-meta"); if (meta) { const area = meta.textContent?.split("·").slice(1).join("·").trim(); meta.textContent = `${copy.capacity}${area ? ` · ${area}` : ""}`; }
    setText("h2", copy.name, card); setText("p", copy.summary, card); setText(".room-catalog-price span", c.catalog[3], card); relabelPrice(card.querySelector(".room-catalog-price") ?? card, c.catalog[4]); setText(".text-link", c.catalog[5], card);
  });
  document.querySelectorAll<HTMLElement>(".catalog-truth > div").forEach((box, i) => { const copy = c.truth[i]; if (!copy) return; setText("strong", copy[0], box); setText("p", copy[1], box); });
  setText(".rooms-footer a[href^='tel:']", c.footer);
  document.title = locale === "en" ? "Rooms and Apartments · Three Crowns" : "Номерлер жана апартаменттер · Үч Таажы";
}

function localizeRoomDetail(locale: "kg" | "en", slug: string) {
  const c = ROOM_DETAIL[locale]; const room = getLocalizedRoomCopy(slug, locale); if (!room) return;
  setText(".room-detail-back", c.back); setText(".room-detail-hero-content .eyebrow", `${c.category} ${document.querySelector(".room-detail-hero-content .eyebrow")?.textContent?.match(/\d+/)?.[0] ?? ""} · ${locale === "en" ? "Three Crowns" : "Үч Таажы"}`); setText("#room-detail-title", room.name);
  const kicker = document.querySelectorAll<HTMLElement>(".room-detail-kicker span"); if (kicker[0]) kicker[0].textContent = room.capacity; if (kicker[2]) kicker[2].textContent = c.availability;
  setText(".room-detail-copy .eyebrow", c.eyebrow); setHtml(".room-detail-copy h2", c.title); setText(".room-detail-copy .lead", `${room.summary} ${c.tail}`); const facts = document.querySelectorAll<HTMLElement>(".room-detail-facts > div"); if (facts[0]) { setText("span", c.placement, facts[0]); setText("strong", room.capacity, facts[0]); } if (facts[1]) setText("span", c.area, facts[1]);
  setText(".room-detail-safety strong", c.how); setText(".room-detail-safety p", c.safety); setText(".room-rate-card > p:first-child", c.summer); document.querySelectorAll<HTMLElement>(".room-rate-row span").forEach((el, i) => { if (c.periods[i]) el.textContent = c.periods[i]; }); document.querySelectorAll<HTMLElement>(".room-rate-row").forEach((row) => relabelPrice(row, locale === "en" ? "KGS" : "сом")); setText(".room-rate-note", c.note); setText(".room-rate-cta", c.cta); setText(".rooms-footer a[href^='tel:']", c.footer);
  document.title = `${room.name} · ${locale === "en" ? "Three Crowns" : "Үч Таажы"}`;
  const meta = document.querySelector<HTMLMetaElement>('meta[name="description"]'); if (meta) meta.content = locale === "en" ? `${room.name} at Three Crowns Resort & SPA: ${room.capacity}. Seasonal rates and live availability for your dates.` : `${room.name} · Үч Таажы Resort & SPA: ${room.capacity}. Сезондук баалар жана даталар боюнча актуалдуу бош орундар.`;
}

function apply(locale: PublicLocale) {
  document.documentElement.lang = locale === "kg" ? "ky" : locale;
  if (locale === "ru") return;
  const pathname = window.location.pathname.replace(/\/$/, "") || "/";
  if (pathname === "/") localizeHome(locale);
  else if (pathname === "/rooms") localizeRoomsIndex(locale);
  else if (pathname.startsWith("/rooms/")) localizeRoomDetail(locale, decodeURIComponent(pathname.split("/").pop() || ""));
}

export default function PublicUiI18nRuntime() {
  useEffect(() => {
    const run = () => apply(resolveClientLocale());
    run();
    window.addEventListener("three-crowns:content-ready", run);
    return () => window.removeEventListener("three-crowns:content-ready", run);
  }, []);
  return null;
}
