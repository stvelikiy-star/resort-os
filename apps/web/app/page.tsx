import BookingWidget from "../components/BookingWidget";

const roomCategories = [
  ["01", "Одноместный цоколь", "1 гость · компактный вариант · без балкона"],
  ["02", "Двухместный стандарт, цоколь", "2 гостя · стандартный вариант · без балкона"],
  ["03", "Одноместный улучшенный", "1 гость · улучшенная категория"],
  ["04", "Двухместный улучшенный", "2 гостя · улучшенная категория"],
  ["05", "Стандарт в коттеджном доме", "2 гостя · размещение в коттеджной части"],
  ["06", "Полулюкс без балкона", "2 гостя · категория полулюкс · без балкона"],
  ["07", "Люкс двухместный", "2 гостя · категория люкс"],
  ["08", "Люкс трёхместный", "3 гостя · категория люкс"],
  ["09", "Двухкомнатный полулюкс", "До 4 гостей · две комнаты"],
  ["10", "Двухкомнатный стандарт", "До 4 гостей · две комнаты"],
  ["11", "Апартаменты", "До 4 гостей · просторная категория"],
  ["12", "Апартаменты с кухней", "До 4 гостей · вариант с кухней"],
];

const resortFacts = [
  ["Собственный пляж", "Отдых на берегу Иссык-Куля на территории курорта."],
  ["Пирс 150 метров", "Протяжённый пирс — одна из ключевых особенностей «Трёх Корон»."],
  ["SPA и массаж", "Восстановление и отдых в SPA-формате на территории курорта."],
  ["Открытый бассейн", "Бассейн 15×8 м дополняет отдых у озера."],
  ["12 категорий", "От одноместных номеров до двухкомнатных вариантов и апартаментов."],
  ["Питание по тарифу", "Условия питания показываются при поиске и зависят от выбранных дат и тарифа."],
];

const bookingSteps = [
  ["01", "Выберите даты", "Укажите заезд, выезд и количество гостей."],
  ["02", "Посмотрите свободные варианты", "Сайт получает актуальную доступность и стоимость из системы отеля."],
  ["03", "Оставьте заявку", "Выберите подходящую категорию и оставьте контакт для менеджера."],
  ["04", "Менеджер подтвердит бронь", "Менеджер свяжется с вами, согласует детали и предоплату."],
];

const hotelJsonLd = {
  "@context": "https://schema.org",
  "@type": "LodgingBusiness",
  name: "Три Короны Resort & SPA",
  url: "https://3korony.com",
  email: "3koronykg@mail.ru",
  telephone: "+996558085002",
  address: {
    "@type": "PostalAddress",
    addressLocality: "Чолпон-Ата",
    addressRegion: "Иссык-Кульская область",
    addressCountry: "KG",
  },
  amenityFeature: [
    { "@type": "LocationFeatureSpecification", name: "Собственный пляж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Пирс 150 м", value: true },
    { "@type": "LocationFeatureSpecification", name: "SPA", value: true },
    { "@type": "LocationFeatureSpecification", name: "Массаж", value: true },
    { "@type": "LocationFeatureSpecification", name: "Открытый бассейн 15×8 м", value: true },
  ],
};

export default function HomePage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(hotelJsonLd) }} />
      <header className="site-header">
        <nav className="wrap nav">
          <a className="brand" href="#top" aria-label="Три Короны">
            <span className="brand-mark">III</span>
            <span><b>ТРИ КОРОНЫ</b><small>Resort & SPA · Issyk-Kul</small></span>
          </a>
          <div className="desktop-nav"><a href="#rooms">Номера</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#booking-how">Как забронировать</a></div>
          <a className="nav-cta desktop-nav" href="#booking">Проверить даты</a>
          <details className="mobile-nav"><summary>Меню</summary><div><a href="#rooms">Номера</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#booking-how">Как забронировать</a><a href="#booking">Бронирование</a></div></details>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="wrap hero-content">
            <span className="eyebrow">Три Короны · Resort & SPA</span>
            <h1>Иссык-Куль.<br />Отдых у самой воды.</h1>
            <p>Курорт в Чолпон-Ате: 84 номера, собственный пляж, 150-метровый пирс, SPA и открытый бассейн.</p>
            <div className="hero-actions"><a className="primary-button gold" href="#booking">Проверить свободные номера</a><a className="ghost-button" href="#rooms">12 категорий номеров</a></div>
            <div className="hero-proof"><span>Чолпон-Ата</span><span>Собственный пляж</span><span>SPA & массаж</span><span>Бассейн 15×8 м</span></div>
          </div>
        </section>

        <div className="wrap booking-lift"><BookingWidget /></div>

        <section className="section intro-section">
          <div className="wrap intro-grid">
            <div><span className="eyebrow dark">Три Короны</span><h2 className="display-title">Курортный отдых на берегу Иссык-Куля</h2></div>
            <p className="lead">Выберите даты — сайт покажет доступные категории и актуальную стоимость на выбранный период. После заявки менеджер свяжется с вами и подтвердит дальнейшие детали бронирования.</p>
          </div>
          <div className="wrap facts"><div><b>84</b><span>номера</span></div><div><b>220</b><span>мест</span></div><div><b>150 м</b><span>пирс</span></div><div><b>12</b><span>категорий</span></div><div><b>15×8 м</b><span>открытый бассейн</span></div></div>
        </section>

        <section className="section rooms-section" id="rooms">
          <div className="wrap">
            <div className="section-heading-row"><div><span className="eyebrow dark">Проживание</span><h2 className="display-title">12 категорий номеров</h2></div><a className="text-link" href="#booking">Проверить цены на даты →</a></div>
            <p className="section-copy">От компактных одноместных вариантов до двухкомнатных номеров, апартаментов и категории с кухней. Точная стоимость и питание зависят от выбранных дат и показываются в поиске.</p>
            <div className="room-groups">{roomCategories.map(([num, title, text]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{text}</p><a href="#booking">Наличие и цена →</a></article>)}</div>
          </div>
        </section>

        <section className="resort-image" id="resort"><div className="wrap overlay-copy"><span className="eyebrow">Берег Иссык-Куля</span><h2 className="display-title light">Собственный пляж<br />и 150-метровый пирс</h2><div className="resort-stats"><span>Пирс 150 м</span><span>Собственный пляж</span><span>Чолпон-Ата</span><span>Иссык-Куль</span></div></div></section>

        <section className="section spa-section" id="spa"><div className="wrap spa-grid"><div><span className="eyebrow dark">SPA & Wellness</span><h2 className="display-title">Отдых и восстановление</h2><p className="lead">SPA и массаж дополняют отдых у озера. На территории также работает открытый бассейн 15×8 м.</p><a className="primary-button" href="#booking">Выбрать даты</a></div><div className="spa-photo"><div><small>Курортная инфраструктура</small><b>SPA · массаж · бассейн</b></div></div></div></section>

        <section className="section services-section"><div className="wrap"><span className="eyebrow dark">Курорт</span><h2 className="display-title">Главное для отдыха</h2><div className="service-grid">{resortFacts.map(([title, text]) => <article key={title}><b>{title}</b><p>{text}</p></article>)}</div></div></section>

        <section className="section booking-steps-section" id="booking-how">
          <div className="wrap">
            <span className="eyebrow dark">Бронирование</span><h2 className="display-title">От выбора дат до подтверждения менеджером</h2>
            <div className="booking-steps">{bookingSteps.map(([num, title, text]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
            <div className="booking-truth"><strong>Важно:</strong><span>отправленная заявка ещё не является действующей бронью. Бронь подтверждает менеджер после согласования условий и предоплаты.</span></div>
          </div>
        </section>

        <section className="section gallery-section" id="gallery"><div className="wrap"><span className="eyebrow dark">Три Короны</span><h2 className="display-title">Озеро, территория и отдых</h2><p className="section-copy">Финальный медиапакет будет использовать фотографии самого курорта; структура галереи уже подготовлена для широкоформатных кадров и удобного просмотра.</p><div className="gallery-grid"><div className="g1" /><div className="g2" /><div className="g3" /><div className="g4" /></div></div></section>

        <section className="contact-band"><div className="wrap contact-band-grid"><div><span className="eyebrow dark">Нужна помощь с выбором?</span><h2>Свяжитесь с менеджером</h2><p>Если даты или категория требуют уточнения, менеджер поможет подобрать вариант.</p></div><div className="contact-actions"><a className="primary-button" href="tel:+996558085002">+996 558 08 50 02</a><a className="outline-button" href="mailto:3koronykg@mail.ru">3koronykg@mail.ru</a></div></div></section>

        <section className="final-cta"><div className="wrap final-row"><div><span className="eyebrow">Проверка наличия</span><h2 className="display-title light">Выберите даты<br />и найдите свой номер.</h2></div><a className="primary-button gold" href="#booking">Проверить даты</a></div></section>
      </main>

      <footer className="site-footer">
        <div className="wrap footer-grid">
          <div><span className="eyebrow">Три Короны</span><h2>Resort & SPA · Чолпон-Ата</h2><p>Иссык-Кульская область, Кыргызстан</p></div>
          <div><small>Бронирование</small><a href="tel:+996558085002">+996 558 08 50 02</a><small>Менеджеры</small><a href="tel:+996558085008">+996 558 08 50 08</a></div>
          <div><small>Email</small><a href="mailto:3koronykg@mail.ru">3koronykg@mail.ru</a><small>Сайт</small><a href="https://3korony.com">3korony.com</a></div>
        </div>
      </footer>
      <a className="mobile-book" href="#booking">Проверить даты</a>
    </>
  );
}
