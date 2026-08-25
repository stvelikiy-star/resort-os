import BookingWidget from "../components/BookingWidget";

const roomCategories = [
  ["01", "Одноместный цоколь", "Для 1 гостя · без балкона"],
  ["02", "Двухместный стандарт, цоколь", "Для 2 гостей · без балкона"],
  ["03", "Одноместный улучшенный", "Для 1 гостя"],
  ["04", "Двухместный улучшенный", "Для 2 гостей"],
  ["05", "Стандарт в коттеджном доме", "Для 2 гостей · коттеджная зона"],
  ["06", "Полулюкс без балкона", "Для 2 гостей"],
  ["07", "Люкс двухместный", "Для 2 гостей"],
  ["08", "Люкс трехместный", "Для 3 гостей"],
  ["09", "Двухкомнатный полулюкс", "Для 4 гостей"],
  ["10", "Двухкомнатный стандарт", "Для 4 гостей"],
  ["11", "Апартаменты", "Для 4 гостей"],
  ["12", "Квартиры / апартаменты с кухней", "Для 4 гостей"],
];

const amenities = [
  ["Собственный пляж", "Отдых на берегу Иссык-Куля и 150-метровый пирс."],
  ["SPA и массаж", "SPA-зона, массаж и сауна на территории курорта."],
  ["Бассейн", "Открытый бассейн 15×8 м."],
  ["Питание", "Основной и летний ресторан, летняя кухня."],
  ["Для отдыха", "Бильярд, спортивные и детские зоны."],
  ["Для мероприятий", "Конференц-пространства для групповых и деловых заездов."],
];

export default function HomePage() {
  return (
    <>
      <header className="site-header">
        <nav className="wrap nav">
          <a className="brand" href="#top" aria-label="Три Короны">
            <span className="brand-mark">III</span>
            <span><b>ТРИ КОРОНЫ</b><small>Resort & SPA · Issyk-Kul</small></span>
          </a>
          <div className="desktop-nav"><a href="#rooms">Номера</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#gallery">Галерея</a></div>
          <a className="nav-cta desktop-nav" href="#booking">Проверить даты</a>
          <details className="mobile-nav"><summary>Меню</summary><div><a href="#rooms">Номера</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#gallery">Галерея</a><a href="#booking">Бронирование</a></div></details>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <div className="wrap hero-content">
            <span className="eyebrow">Три Короны · Resort & SPA</span>
            <h1>Иссык-Куль.<br />Отдых у самой воды.</h1>
            <p>84 номера, собственный пляж, 150-метровый пирс, SPA и курортная территория в Чолпон-Ате.</p>
            <div className="hero-actions"><a className="primary-button gold" href="#booking">Проверить свободные номера</a><a className="ghost-button" href="#rooms">Категории номеров</a></div>
          </div>
        </section>

        <div className="wrap booking-lift"><BookingWidget /></div>

        <section className="section intro-section">
          <div className="wrap intro-grid">
            <div><span className="eyebrow dark">Три Короны</span><h2 className="display-title">Курорт на берегу Иссык-Куля</h2></div>
            <p className="lead">Выберите даты и количество гостей — система покажет доступные категории и стоимость на выбранный период. После отправки заявки менеджер свяжется с вами для подтверждения и предоплаты.</p>
          </div>
          <div className="wrap facts"><div><b>84</b><span>номера</span></div><div><b>220</b><span>мест</span></div><div><b>150 м</b><span>пирс</span></div><div><b>12</b><span>категорий</span></div><div><b>15×8 м</b><span>открытый бассейн</span></div></div>
        </section>

        <section className="section rooms-section" id="rooms">
          <div className="wrap">
            <span className="eyebrow dark">Проживание</span><h2 className="display-title">12 категорий номеров</h2><p className="section-copy">От компактных цокольных номеров до двухкомнатных вариантов, апартаментов и квартир с кухней. Точная стоимость зависит от дат проживания и рассчитывается при поиске.</p>
            <div className="room-groups">{roomCategories.map(([num, title, text]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{text}</p><a href="#booking">Проверить даты →</a></article>)}</div>
          </div>
        </section>

        <section className="resort-image" id="resort"><div className="wrap overlay-copy"><span className="eyebrow">Пляж и пирс</span><h2 className="display-title light">Собственный пляж<br />на Иссык-Куле</h2><div className="resort-stats"><span>Пирс 150 м</span><span>Собственный пляж</span><span>Чолпон-Ата</span><span>Отдых у воды</span></div></div></section>

        <section className="section spa-section" id="spa"><div className="wrap spa-grid"><div><span className="eyebrow dark">SPA & Wellness</span><h2 className="display-title">Время восстановиться</h2><p className="lead">SPA, массаж, сауна, бассейн и отдых рядом с озером дополняют курортный формат «Трёх Корон».</p></div><div className="spa-photo"><div><small>Курортная инфраструктура</small><b>SPA · бассейн · отдых</b></div></div></div></section>

        <section className="section services-section"><div className="wrap"><span className="eyebrow dark">На территории</span><h2 className="display-title">Всё для отдыха в одном месте</h2><div className="service-grid">{amenities.map(([title, text]) => <article key={title}><b>{title}</b><p>{text}</p></article>)}</div></div></section>

        <section className="section gallery-section" id="gallery"><div className="wrap"><span className="eyebrow dark">Галерея</span><h2 className="display-title">Атмосфера «Трёх Корон»</h2><p className="section-copy">Озеро, пляж, территория и пространства курорта — всё, ради чего приезжают отдыхать в Чолпон-Ату.</p><div className="gallery-grid"><div className="g1" /><div className="g2" /><div className="g3" /><div className="g4" /></div></div></section>

        <section className="final-cta"><div className="wrap final-row"><div><span className="eyebrow">Бронирование</span><h2 className="display-title light">Выберите даты<br />и проверьте наличие.</h2></div><a className="primary-button gold" href="#booking">Проверить даты</a></div></section>
      </main>
      <a className="mobile-book" href="#booking">Проверить даты</a>
    </>
  );
}
