import BookingWidget from "../components/BookingWidget";
import ResortGallery from "../components/ResortGallery";
import SiteHeader from "../components/SiteHeader";

const roomCategories = [
  ["01", "Одноместный, цоколь", "1 гость", "Без балкона"], ["02", "Двухместный стандарт, цоколь", "2 гостя", "Без балкона"], ["03", "Одноместный улучшенный", "1 гость", "Улучшенная категория"], ["04", "Двухместный улучшенный", "2 гостя", "Улучшенная категория"], ["05", "Стандарт в коттеджном доме", "2 гостя", "Коттеджная часть"], ["06", "Полулюкс без балкона", "2 гостя", "Без балкона"], ["07", "Люкс двухместный", "2 гостя", "Категория люкс"], ["08", "Люкс трёхместный", "3 гостя", "Категория люкс"], ["09", "Двухкомнатный полулюкс", "До 4 гостей", "Две комнаты"], ["10", "Двухкомнатный стандарт", "До 4 гостей", "Две комнаты"], ["11", "Апартаменты", "До 4 гостей", "Просторная категория"], ["12", "Апартаменты с кухней", "До 4 гостей", "С кухней"],
];

const bookingSteps = [
  ["01", "Выберите даты", "Заезд, выезд и состав гостей задают реальный поиск по инвентарю."],
  ["02", "Сравните варианты", "Наличие и стоимость приходят из системы отеля для выбранного периода."],
  ["03", "Отправьте заявку", "Передайте менеджеру выбранную категорию и контакты прямо из результатов поиска."],
  ["04", "Подтвердите условия", "Менеджер согласует детали и предоплату. Только после подтверждения бронь становится действующей."],
];

const seasonRates = [
  { dates: "1 июня — 6 июля", label: "Начало сезона", range: "3 000–13 000 сом", note: "за номер / сутки" },
  { dates: "7 июля — 25 августа", label: "Высокий сезон", range: "4 000–15 500 сом", note: "за номер / сутки" },
  { dates: "26 августа — 15 сентября", label: "Бархатный сезон", range: "3 000–13 000 сом", note: "за номер / сутки" },
];

const galleryImages = [
  { src: "/media/three-crowns/hero-resort.webp", alt: "Корпуса и зелёная территория отеля Три Короны", label: "Территория" },
  { src: "/media/three-crowns/room-double.webp", alt: "Двухместный номер отеля Три Короны", label: "Проживание" },
  { src: "/media/three-crowns/lake-night.webp", alt: "Ночной Иссык-Куль у отеля Три Короны", label: "Иссык-Куль ночью" },
  { src: "/media/three-crowns/conference.webp", alt: "Конференц-зал отеля Три Короны", label: "Конференц-зал" },
];

const hotelJsonLd = {
  "@context": "https://schema.org", "@type": "LodgingBusiness", name: "Три Короны Resort & SPA", url: "https://3korony.com",
  email: "3koronykg@mail.ru", telephone: "+996558085002",
  address: { "@type": "PostalAddress", addressLocality: "Чолпон-Ата", addressRegion: "Иссык-Кульская область", addressCountry: "KG" },
  amenityFeature: [
    { "@type": "LocationFeatureSpecification", name: "Собственный пляж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Пирс 150 м", value: true },
    { "@type": "LocationFeatureSpecification", name: "SPA", value: true },
    { "@type": "LocationFeatureSpecification", name: "Массаж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Открытый бассейн 15×8 м", value: true },
  ],
};

export default function HomePage() {
  return <>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(hotelJsonLd) }} />
    <SiteHeader />
    <main id="top">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-shade" aria-hidden="true" />
        <div className="wrap hero-content">
          <p className="eyebrow light">Три Короны · Resort & SPA · Чолпон-Ата</p>
          <h1 id="hero-title">Иссык-Куль.<br />Отдых у самой воды.</h1>
          <p className="hero-copy">84 номера, собственный пляж, 150-метровый пирс, SPA и открытый бассейн — всё главное для курортного отдыха собрано в одном месте.</p>
          <div className="hero-actions"><a className="button button-accent" href="#booking">Проверить свободные номера</a><a className="button button-quiet" href="#rooms">Смотреть категории</a></div>
          <div className="hero-facts" aria-label="Ключевые факты"><span>Чолпон-Ата</span><span>84 номера</span><span>Собственный пляж</span><span>Пирс 150 м</span></div>
        </div>
        <a className="hero-scroll" href="#booking" aria-label="Перейти к поиску номеров"><span>Проверка наличия</span><i aria-hidden="true">↓</i></a>
      </section>

      <div className="wrap booking-lift"><BookingWidget /></div>

      <section className="section intro-section" aria-labelledby="intro-title">
        <div className="wrap intro-layout"><div><p className="eyebrow">Три Короны</p><h2 className="display-title" id="intro-title">Курортный ритм<br />у большого озера</h2></div><div className="intro-copy"><p>Здесь главный ориентир — Иссык-Куль. Пляж, длинный пирс, зелёная территория, проживание и wellness-инфраструктура складываются в понятный сценарий отдыха.</p><a className="text-link" href="#resort">Посмотреть курорт →</a></div></div>
        <div className="wrap stat-line" aria-label="Факты о курорте"><div><strong>84</strong><span>номера</span></div><div><strong>220</strong><span>гостевых мест</span></div><div><strong>12</strong><span>категорий</span></div><div><strong>150 м</strong><span>пирс</span></div><div><strong>15×8 м</strong><span>открытый бассейн</span></div></div>
      </section>

      <section className="section rate-section" id="rates" aria-labelledby="rates-title">
        <div className="wrap section-heading compact"><div><p className="eyebrow">Официальный прайс · 2026</p><h2 className="display-title" id="rates-title">Три периода.<br />Цена по вашим датам.</h2></div><div className="section-aside"><p>Прайс-лист 2026 указывает стоимость размещения на базе завтрака. Для бронирования сайт всегда пересчитывает конкретную категорию и даты через Resort Core.</p><a className="text-link" href="#booking">Рассчитать проживание →</a></div></div>
        <div className="wrap rate-bands">{seasonRates.map((rate, index) => <article key={rate.dates} className={index === 1 ? "is-peak" : ""}><span>{String(index + 1).padStart(2, "0")}</span><p>{rate.label}</p><h3>{rate.dates}</h3><strong>{rate.range}</strong><small>{rate.note} · завтрак включён</small></article>)}</div>
        <div className="wrap rate-note"><strong>Важно</strong><p>Диапазон выше — ориентир по официальному прайсу 2026. Финальная стоимость зависит от категории, выбранных ночей и статуса тарифа в системе.</p></div>
      </section>

      <section className="section rooms-section" id="rooms" aria-labelledby="rooms-title">
        <div className="wrap section-heading"><div><p className="eyebrow">Проживание</p><h2 className="display-title" id="rooms-title">От компактного номера<br />до апартаментов</h2></div><div className="section-aside"><p>12 категорий — от одноместных номеров до апартаментов и вариантов с кухней.</p><a className="text-link" href="#booking">Проверить мои даты →</a></div></div>
        <div className="wrap accommodation-editorial"><figure className="accommodation-photo"><img src="/media/three-crowns/room-double.webp" alt="Двухместный номер отеля Три Короны" loading="lazy" /><figcaption><span>Реальные номера «Три Короны»</span><small>Категория и точная конфигурация конкретного номера подтверждаются при бронировании.</small></figcaption></figure><div className="room-list" role="list">{roomCategories.map(([num,title,capacity,note]) => <article className="room-row" key={num} role="listitem"><span className="room-index">{num}</span><div><h3>{title}</h3><p>{capacity} · {note}</p></div><a href="#booking" aria-label={`Проверить наличие: ${title}`}>Наличие <span aria-hidden="true">↗</span></a></article>)}</div></div>
      </section>

      <section className="resort-feature" id="resort" aria-labelledby="resort-title"><div className="resort-feature-image" aria-hidden="true" /><div className="resort-feature-shade" aria-hidden="true" /><div className="wrap resort-feature-content"><p className="eyebrow light">Берег Иссык-Куля</p><h2 className="display-title light" id="resort-title">Собственный пляж.<br />Пирс длиной 150 метров.</h2><p>Пространство у воды — одна из ключевых особенностей «Трёх Корон».</p><div className="feature-tags" aria-label="Инфраструктура у воды"><span>Собственный пляж</span><span>Пирс 150 м</span><span>Открытый бассейн 15×8 м</span></div></div></section>

      <section className="section wellness-section" id="spa" aria-labelledby="spa-title"><div className="wrap wellness-layout"><div className="wellness-copy"><p className="eyebrow">SPA & Wellness</p><h2 className="display-title" id="spa-title">Время замедлиться</h2><p className="lead">SPA и массаж дополняют отдых у озера. На территории также есть открытый бассейн 15×8 м.</p><a className="button button-dark" href="#booking">Выбрать даты</a></div><figure className="wellness-photo"><img src="/media/three-crowns/hero-resort.webp" alt="Зелёная территория отеля Три Короны" loading="lazy" /><figcaption><span>Курортная территория</span><strong>Озеро · SPA · отдых</strong></figcaption></figure></div></section>

      <section className="section amenities-section" aria-labelledby="amenities-title"><div className="wrap"><div className="section-heading compact"><div><p className="eyebrow">На территории</p><h2 className="display-title" id="amenities-title">Отдых, работа<br />и бытовой комфорт</h2></div><p className="section-aside">Новые материалы отеля подтверждают конференц-зал, бильярд, прачечную и зоны отдыха на территории.</p></div><div className="amenity-list"><article><span>01</span><h3>Собственный пляж</h3></article><article><span>02</span><h3>SPA и массаж</h3></article><article><span>03</span><h3>Бильярд</h3></article><article><span>04</span><h3>Конференц-зал</h3></article><article><span>05</span><h3>Прачечная</h3></article><article><span>06</span><h3>Открытый бассейн 15×8 м</h3></article></div></div></section>

      <section className="section groups-section" aria-labelledby="groups-title"><div className="wrap groups-layout"><div><p className="eyebrow light">Группы и события</p><h2 className="display-title light" id="groups-title">Есть пространство<br />для совместных поездок.</h2></div><div><p>Конференц-зал позволяет отдельно работать с корпоративными и групповыми запросами. Условия и размещение группы рассчитываются менеджером.</p><a className="button button-accent" href="tel:+996558085002">Обсудить групповую поездку</a></div></div></section>

      <section className="section gallery-section" id="gallery" aria-labelledby="gallery-title"><div className="wrap section-heading"><div><p className="eyebrow">Атмосфера</p><h2 className="display-title" id="gallery-title">Озеро, номера,<br />курортный день</h2></div><p className="section-aside">Первые ключевые кадры уже переведены на собственный медиапакет отеля: территория, реальные номера, конференц-зал и ночной Иссык-Куль.</p></div><ResortGallery images={galleryImages} /></section>

      <section className="section booking-story" id="booking-how" aria-labelledby="booking-story-title"><div className="wrap"><div className="booking-story-head"><p className="eyebrow light">Бронирование без иллюзий</p><h2 className="display-title light" id="booking-story-title">Сначала реальная доступность.<br />Потом подтверждение.</h2><p>Сайт не создаёт отдельную «красивую» availability. Поиск опирается на инвентарь Resort Core.</p></div><div className="booking-steps">{bookingSteps.map(([num,title,text]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{text}</p></article>)}</div><div className="booking-truth"><strong>Важно</strong><p>Отправленная заявка не блокирует номер и не является действующей бронью. Для действующей брони требуется подтверждение условий и предоплаты менеджером.</p></div></div></section>

      <section className="section contact-section" id="contacts" aria-labelledby="contacts-title"><div className="wrap contact-layout"><div><p className="eyebrow">Контакты</p><h2 className="display-title" id="contacts-title">Чолпон-Ата.<br />Иссык-Куль.</h2><p className="lead">Нужна помощь с датами, категорией или групповой поездкой — можно сразу связаться с командой бронирования.</p></div><div className="contact-list"><a href="tel:+996558085002"><span>Бронирование</span><strong>+996 558 08 50 02</strong></a><a href="https://wa.me/996558085008" target="_blank" rel="noreferrer"><span>WhatsApp менеджера</span><strong>+996 558 08 50 08</strong></a><a href="mailto:3koronykg@mail.ru"><span>Email</span><strong>3koronykg@mail.ru</strong></a><div><span>Местоположение</span><strong>Чолпон-Ата, Иссык-Кульская область, Кыргызстан</strong></div></div></div></section>

      <section className="final-cta" aria-labelledby="final-title"><div className="wrap final-cta-layout"><div><p className="eyebrow light">Ваши даты</p><h2 className="display-title light" id="final-title">Посмотрите, что свободно<br />именно сейчас.</h2></div><a className="button button-accent" href="#booking">Проверить наличие</a></div></section>
    </main>

    <footer className="site-footer"><div className="wrap footer-top"><a className="footer-brand" href="#top"><strong>ТРИ КОРОНЫ</strong><span>Resort & SPA · Issyk-Kul</span></a><nav aria-label="Навигация в подвале"><a href="#rooms">Номера</a><a href="#rates">Прайс 2026</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#gallery">Галерея</a><a href="#contacts">Контакты</a></nav></div><div className="wrap footer-bottom"><span>© 2026 Три Короны Resort & SPA</span><div><a href="tel:+996558085002">+996 558 08 50 02</a><a href="mailto:3koronykg@mail.ru">3koronykg@mail.ru</a></div></div></footer>
    <a className="mobile-book" href="#booking">Проверить свободные номера</a>
  </>;
}
