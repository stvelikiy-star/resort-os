import Image from "next/image";
import Link from "next/link";

import BookingWidget from "../components/BookingWidget";
import SiteHeader from "../components/SiteHeader";
import { ownerApprovedGuestFacts, TWO_GIS_REVIEWS_URL } from "../lib/ownerApprovedGuestFacts";
import { formatKgs, roomCategories } from "../lib/roomCatalog";

const ownerFacts = ownerApprovedGuestFacts.ru;

const advantages = [
  { index: "01", title: "Первая линия Иссык-Куля", text: "Отдых строится вокруг озера: берег, собственный пляж и длинный пирс находятся внутри курортного маршрута.", image: "/media/three-crowns/lake-night.webp" },
  { index: "02", title: "Собственный пляж", text: "Не нужно планировать отдельную поездку к воде — пляж становится естественным продолжением территории.", image: "/media/three-crowns/hero-resort.webp" },
  { index: "03", title: "Пирс 150 метров", text: "Одна из главных визуальных точек курорта: прогулки, воздух Иссык-Куля и открытая перспектива воды.", image: "/media/three-crowns/lake-night.webp" },
  { index: "04", title: "SPA и массаж", text: "После активного дня можно переключиться на спокойный формат отдыха и восстановление.", image: "/media/three-crowns/hero-resort.webp" },
  { index: "05", title: "Бассейн 15×8 м", text: "Открытый бассейн дополняет отдых у озера и подходит для дневного курортного ритма.", image: "/media/three-crowns/hero-resort.webp" },
  { index: "06", title: "12 категорий размещения", text: "От компактных одноместных номеров до двухкомнатных категорий и апартаментов с кухней.", image: "/media/three-crowns/room-double.webp" },
];

const territoryJourney = [
  ["01", "Заезд и размещение", "Начните отдых без лишней суеты: выберите категорию заранее, проверьте наличие по датам и согласуйте детали с менеджером."],
  ["02", "Территория курорта", "После заселения весь основной сценарий отдыха складывается внутри одной территории — номер, бассейн, SPA и путь к воде."],
  ["03", "Открытый бассейн", "Бассейн 15×8 м — отдельная дневная зона для спокойного отдыха между прогулками и поездками."],
  ["04", "SPA и массаж", "Вечером можно сменить активность на восстановление и более спокойный темп."],
  ["05", "Собственный пляж", "Главная точка летнего дня — берег Иссык-Куля без необходимости выезжать за пределы курорта."],
  ["06", "Пирс длиной 150 метров", "Финал маршрута — длинный пирс, открытая вода и тот самый масштаб Иссык-Куля, ради которого сюда возвращаются."],
];

const amenityCards = [
  ["Отдых у воды", "Собственный пляж, пирс 150 м и открытый бассейн 15×8 м формируют полноценный водный сценарий внутри курорта."],
  ["SPA & Recovery", "SPA и массаж помогают дополнить пляжный отдых восстановлением и спокойным вечером."],
  ["Для семей", "Большой выбор категорий позволяет подобрать размещение для одного гостя, пары или семьи до четырёх человек."],
  ["Длинные заезды", "Апартаменты увеличенной площади и категория с кухней удобны, когда вы приезжаете не на одну-две ночи."],
  ["Связь с менеджером", "Если не хочется разбираться самостоятельно, менеджер поможет подобрать категорию, даты и дополнительные услуги."],
  [ownerFacts.included.title, ownerFacts.included.text],
];

const reviewThemes = ownerFacts.reviews.cards.map((review, index) => ({
  score: String(index + 1).padStart(2, "0"),
  ...review,
}));

const extraServices = ownerFacts.services.cards;

const groupFormats = [
  ["Корпоративные заезды", "Размещение команды, единая коммуникация с организатором и согласование программы пребывания."],
  ["Спортивные сборы", "Подбираем номерной фонд под состав группы и заранее обсуждаем режим проживания и питания."],
  ["Специальное меню", "Для спортивных и организованных групп можно заранее обсудить отдельные требования к рациону и графику питания."],
  ["Группы и мероприятия", "Помогаем собрать проживание, питание, трансфер и дополнительные активности в одну понятную программу."],
];

const hotelJsonLd = {
  "@context": "https://schema.org",
  "@type": "LodgingBusiness",
  name: "Три Короны Resort & SPA",
  url: "https://3korony.com",
  email: "3koronykg@mail.ru",
  telephone: "+996558085002",
  address: { "@type": "PostalAddress", streetAddress: "Иманбай Молдо", addressLocality: "Чолпон-Ата", postalCode: "722315", addressRegion: "Иссык-Кульская область", addressCountry: "KG" },
  amenityFeature: [
    { "@type": "LocationFeatureSpecification", name: "Собственный пляж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Пирс 150 м", value: true },
    { "@type": "LocationFeatureSpecification", name: "SPA", value: true },
    { "@type": "LocationFeatureSpecification", name: "Массаж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Открытый бассейн 15×8 м", value: true },
  ],
};

export default function HomePage() {
  const loopingAdvantages = [...advantages, ...advantages];

  return <>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(hotelJsonLd) }} />
    <SiteHeader />
    <main className="landing-v3" id="top">
      <section className="v3-hero" aria-labelledby="hero-title">
        <div className="v3-hero-media" aria-hidden="true">
          <video autoPlay muted loop playsInline preload="metadata" poster="/media/three-crowns/hero-resort.webp">
            <source src="/media/three-crowns/hero-resort.mp4" type="video/mp4" />
          </video>
        </div>
        <div className="v3-hero-shade" aria-hidden="true" />
        <div className="wrap v3-hero-content">
          <p className="eyebrow light">Три Короны · Resort & SPA · Чолпон-Ата</p>
          <h1 id="hero-title">Иссык-Куль.<br />Ваш отдых начинается здесь.</h1>
          <p className="v3-hero-copy">Курорт у самой воды: собственный пляж, 150-метровый пирс, SPA, открытый бассейн и 12 категорий размещения. Выберите даты — дальше мы поможем собрать отдых под вас.</p>
          <div className="v3-hero-actions"><a className="button button-accent" href="#booking">Проверить свободные номера</a><Link className="button button-quiet" href="/rooms">Смотреть номерной фонд</Link></div>
          <div className="v3-hero-meta" aria-label="Ключевые факты"><span><b>84</b> номера</span><span><b>12</b> категорий</span><span><b>150 м</b> пирс</span><span><b>15×8 м</b> бассейн</span></div>
        </div>
        <a className="v3-scroll-cue" href="#booking" aria-label="Перейти к бронированию"><span>Начать</span><i>↓</i></a>
      </section>

      <section className="v3-booking" aria-labelledby="booking-experience-title">
        <div className="wrap v3-booking-heading"><div><p className="eyebrow">Бронирование без лишних шагов</p><h2 className="display-title" id="booking-experience-title">Сначала даты.<br />Потом — лучший вариант.</h2></div><div className="v3-booking-intro-copy"><p>Укажите даты и состав гостей. Система покажет свободные категории и стоимость за весь период. Если понадобится помощь — менеджер подключится на любом этапе.</p><div className="v3-booking-trust"><span>Актуальное наличие</span><span>Стоимость за период</span><span>Помощь менеджера</span></div></div></div>
        <div className="wrap v3-booking-stage"><div className="v3-booking-main"><BookingWidget /></div><aside className="v3-booking-help" aria-label="Помощь с бронированием"><div><p className="eyebrow light">Нужна помощь?</p><h3>Подберём номер вместе</h3><p>Расскажите, кто едет, на сколько дней и какой отдых вы хотите. Менеджер поможет сравнить категории и дополнительные услуги.</p></div><div className="v3-help-actions"><a href="tel:+996558085002">Позвонить · +996 558 08 50 02</a><a href="https://wa.me/996558085008" target="_blank" rel="noreferrer">Написать в WhatsApp ↗</a></div><div className="v3-booking-rule"><strong>Важно</strong><p>Номер автоматически не блокируется после заявки. Подтверждённая бронь оформляется менеджером после согласования условий и предоплаты.</p></div></aside></div>
      </section>

      <section className="v3-advantages" aria-labelledby="advantages-title">
        <div className="wrap v3-section-head"><div><p className="eyebrow">Почему Три Короны</p><h2 className="display-title" id="advantages-title">От номера<br />до воды — один маршрут</h2></div><p>Преимущества курорта не спрятаны в длинном списке. Они становятся последовательностью дня: проснуться, выйти на территорию, дойти до воды, отдохнуть у бассейна и закончить вечер в SPA.</p></div>
        <div className="v3-advantage-marquee" aria-label="Преимущества курорта"><div className="v3-advantage-track">{loopingAdvantages.map((item, index) => <article className="v3-advantage-card" key={`${item.index}-${index}`} aria-hidden={index >= advantages.length}><div className="v3-advantage-image"><Image src={item.image} alt="" fill sizes="380px" /></div><div className="v3-advantage-body"><span>{item.index}</span><h3>{item.title}</h3><p>{item.text}</p></div></article>)}</div></div>
      </section>

      <section className="v3-rooms" id="rooms" aria-labelledby="rooms-title">
        <div className="wrap v3-section-head"><div><p className="eyebrow">Номерной фонд</p><h2 className="display-title" id="rooms-title">Все 12 категорий.<br />Выбирайте спокойно.</h2></div><div><p>От компактных одноместных вариантов до просторных двухкомнатных категорий и апартаментов. Сравните вместимость, площадь и сезонную стоимость, а затем откройте нужную категорию и проверьте даты.</p><Link className="text-link" href="/rooms">Открыть полный каталог →</Link></div></div>
        <div className="wrap v3-room-grid">{roomCategories.map((room) => <Link className="v3-room-card" href={`/rooms/${room.slug}`} key={room.slug}><div className="v3-room-card-photo"><Image src="/media/three-crowns/room-double.webp" alt={room.name} fill sizes="(max-width: 760px) 88vw, (max-width: 1100px) 44vw, 31vw" /></div><div className="v3-room-card-body"><div className="v3-room-card-top"><span>{room.index}</span><span>{room.capacity} · {room.area}</span></div><h3>{room.name}</h3><p>{room.summary}</p><div className="v3-room-card-price"><small>Высокий сезон</small><strong>{formatKgs(room.rates.peak)} сом / сутки</strong></div><b>Смотреть категорию →</b></div></Link>)}</div>
      </section>

      <section className="v3-territory" id="resort" aria-labelledby="territory-title">
        <div className="wrap v3-section-head light-head"><div><p className="eyebrow light">Территория курорта</p><h2 className="display-title light" id="territory-title">От первого шага<br />до конца пирса</h2></div><p>Пройдите весь маршрут курорта — от размещения и дневного отдыха до собственного пляжа и длинного пирса, который выходит в открытое пространство Иссык-Куля.</p></div>
        <div className="wrap v3-territory-film">
          <video autoPlay muted loop playsInline preload="metadata" poster="/media/three-crowns/hero-resort.webp"><source src="/media/three-crowns/territory.mp4" type="video/mp4" /></video>
          <div className="v3-film-caption"><span>Три Короны · территория</span><strong>Корпуса, зелень и внутренний маршрут курорта</strong></div>
        </div>
        <div className="wrap v3-territory-route">{territoryJourney.map(([index, title, text]) => <article key={index}><span>{index}</span><div><h3>{title}</h3><p>{text}</p></div></article>)}</div>
      </section>

      <section className="v3-amenities" id="experience" aria-labelledby="amenities-title">
        <div className="wrap v3-amenities-layout">
          <div className="v3-amenities-copy"><p className="eyebrow">Озеро и отдых у воды</p><h2 className="display-title" id="amenities-title">Иссык-Куль — часть<br />каждого дня.</h2><p className="lead">Собственный пляж, пирс длиной 150 метров и открытая вода задают ритм отдыха. Здесь можно провести спокойный день у берега или добавить больше движения и водных впечатлений.</p><div className="v3-water-tags"><span>Собственный пляж</span><span>Пирс 150 м</span><span>Открытый бассейн 15×8 м</span></div><a className="button button-dark" href="#booking">Проверить даты</a></div>
          <figure className="v3-amenities-photo v3-lake-film">
            <video autoPlay muted loop playsInline preload="metadata" poster="/media/three-crowns/lake-night.webp"><source src="/media/three-crowns/lake.mp4" type="video/mp4" /></video>
            <figcaption><span>Иссык-Куль</span><strong>Пляж · пирс · вода · летние впечатления</strong></figcaption>
          </figure>
        </div>
        <div className="wrap v3-amenity-grid">{amenityCards.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="v3-reviews" id="reviews" aria-labelledby="reviews-title">
        <div className="wrap v3-section-head"><div><p className="eyebrow">{ownerFacts.reviews.eyebrow}</p><h2 className="display-title" id="reviews-title">{ownerFacts.reviews.title}</h2></div><p>{ownerFacts.reviews.intro}</p></div>
        <div className="wrap v3-review-grid">{reviewThemes.map((review) => <article key={review.score}><span>{review.score}</span><h3>{review.title}</h3><p>{review.text}</p></article>)}</div>
        <div className="wrap v3-hero-actions" data-owner-review-actions><a className="button button-dark" href={TWO_GIS_REVIEWS_URL} target="_blank" rel="noreferrer">{ownerFacts.reviews.readCta}</a><a className="button button-outline" href={TWO_GIS_REVIEWS_URL} target="_blank" rel="noreferrer">{ownerFacts.reviews.leaveCta}</a></div>
        <div className="wrap v3-extra-services"><div className="v3-extra-heading"><p className="eyebrow light">{ownerFacts.services.eyebrow}</p><h3>{ownerFacts.services.title}</h3><p>{ownerFacts.services.intro}</p></div><div className="v3-extra-grid">{extraServices.map((service, index) => <article key={service.code} data-service-code={service.code}><span>{String(index + 1).padStart(2, "0")}</span><h4>{service.title}</h4><p>{service.text}</p>{service.cta && service.href ? <a className="text-link" href={service.href} target={service.href.startsWith("http") ? "_blank" : undefined} rel={service.href.startsWith("http") ? "noreferrer" : undefined}>{service.cta} →</a> : null}</article>)}</div></div>
      </section>

      <section className="v3-groups" id="groups" aria-labelledby="groups-title">
        <div className="v3-groups-media" aria-hidden="true"><Image src="/media/three-crowns/hero-resort.webp" alt="" fill sizes="100vw" /></div><div className="v3-groups-shade" aria-hidden="true" />
        <div className="wrap v3-groups-content"><div className="v3-groups-intro"><p className="eyebrow light">Групповые заезды</p><h2 className="display-title light" id="groups-title">Команды, сборы<br />и корпоративный отдых</h2><p>Для организованных групп важен не только номер. Нужно заранее собрать размещение, график, питание, транспорт и коммуникацию с одним ответственным менеджером. Именно так мы предлагаем строить групповой заезд.</p><a className="button button-accent" href="https://wa.me/996558085008" target="_blank" rel="noreferrer">Обсудить групповой заезд</a></div><div className="v3-group-grid">{groupFormats.map(([title, text], index) => <article key={title}><span>{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{text}</p></article>)}</div></div>
      </section>

      <section className="v3-contacts" id="contacts" aria-labelledby="contacts-title">
        <div className="wrap v3-contact-head"><div><p className="eyebrow">Контакты и дорога</p><h2 className="display-title" id="contacts-title">Чолпон-Ата.<br />Берег Иссык-Куля.</h2><p>Три Короны Resort & SPA находится в Чолпон-Ате по адресу Иманбай Молдо, 722315. Откройте карту, постройте маршрут или свяжитесь с менеджером — поможем с приездом и проживанием.</p></div><div className="v3-contact-actions"><a href="tel:+996558085002"><span>Бронирование</span><strong>+996 558 08 50 02</strong></a><a href="https://wa.me/996558085008" target="_blank" rel="noreferrer"><span>WhatsApp / менеджер</span><strong>+996 558 08 50 08</strong></a><a href="mailto:3koronykg@mail.ru"><span>Email</span><strong>3koronykg@mail.ru</strong></a></div></div>
        <div className="wrap v3-map-layout"><div className="v3-map-card"><iframe title="Три Короны Resort & SPA на Google Maps" src="https://www.google.com/maps?q=Imanbay%20Moldo%2C%20Cholpon-Ata%20722315%2C%20Kyrgyzstan&output=embed" loading="lazy" referrerPolicy="no-referrer-when-downgrade" allowFullScreen /></div><div className="v3-arrival-card"><p className="eyebrow">Перед поездкой</p><h3>Сохраните контакты — остальное поможем организовать</h3><p>Напишите менеджеру, если нужен подбор номера, групповое размещение, трансфер или дополнительная программа по Иссык-Кулю.</p><div><a className="button button-dark" href="#booking">Выбрать даты</a><a className="text-link" href="https://www.google.com/maps/search/?api=1&query=Imanbay%20Moldo%2C%20Cholpon-Ata%20722315%2C%20Kyrgyzstan" target="_blank" rel="noreferrer">Открыть Google Maps ↗</a></div></div></div>
      </section>

      <section className="v3-final-cta"><div className="wrap v3-final-layout"><div><p className="eyebrow light">Три Короны · Resort & SPA</p><h2>Выберите даты.<br />Иссык-Куль уже ждёт.</h2></div><div><p>Проверьте свободные категории и стоимость проживания на ваш период.</p><a className="button button-accent" href="#booking">Проверить номера</a></div></div></section>
    </main>
    <footer className="home-footer"><div className="wrap home-footer-inner"><strong>Три Короны · Resort & SPA</strong><div className="home-footer-links"><Link href="/rooms">Номера</Link><a href="/#resort">Территория</a><a href="/#groups">Группам</a><a href="/#contacts">Контакты</a></div></div></footer>
    <a className="mobile-book" href="#booking">Проверить свободные номера</a>
  </>;
}
