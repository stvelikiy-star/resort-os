import BookingWidget from "../components/BookingWidget";

const roomGroups = [
  ["01", "Цоколь", "Одноместные и двухместные стандарты"],
  ["02", "Улучшенные", "Одноместные и двухместные категории"],
  ["03", "Коттеджи", "15 двухместных номеров в коттеджном доме"],
  ["04", "Люкс", "Двухместные и трехместные люксы"],
  ["05", "Двухкомнатные", "Стандарты и полулюксы на 4 гостей"],
  ["06", "Апартаменты", "Апартаменты и квартиры с кухней"],
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
            <div><span className="eyebrow dark">Три Короны</span><h2 className="display-title">Курорт, где всё начинается с озера</h2></div>
            <p className="lead">Сайт теперь связан с Resort Core: выбранные даты проверяются по реальному номерному фонду и сезонным тарифам, а заявка попадает в единый контур бронирования.</p>
          </div>
          <div className="wrap facts"><div><b>84</b><span>номера</span></div><div><b>220</b><span>мест</span></div><div><b>150 м</b><span>пирс</span></div><div><b>12</b><span>категорий</span></div><div><b>15×8 м</b><span>открытый бассейн</span></div></div>
        </section>

        <section className="section rooms-section" id="rooms">
          <div className="wrap">
            <span className="eyebrow dark">Проживание</span><h2 className="display-title">Реальный номерной фонд</h2><p className="section-copy">Внутри PMS заведены 84 фактических номера. Точная стоимость рассчитывается по выбранным датам, а не по декоративной цене на карточке.</p>
            <div className="room-groups">{roomGroups.map(([num, title, text]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{text}</p><a href="#booking">Проверить даты →</a></article>)}</div>
          </div>
        </section>

        <section className="resort-image" id="resort"><div className="wrap overlay-copy"><span className="eyebrow">Пляж и пирс</span><h2 className="display-title light">Собственный пляж<br />на Иссык-Куле</h2><div className="resort-stats"><span>Пирс 150 м</span><span>Песчаный пляж</span><span>Чолпон-Ата</span><span>Первая линия</span></div></div></section>

        <section className="section spa-section" id="spa"><div className="wrap spa-grid"><div><span className="eyebrow dark">SPA & Wellness</span><h2 className="display-title">Время восстановиться</h2><p className="lead">SPA, массаж, бассейн и отдых рядом с озером — часть инфраструктуры курорта. Актуальный набор услуг и расписание будут управляться из Resort OS.</p></div><div className="spa-photo"><div><small>Курортная инфраструктура</small><b>SPA · бассейн · отдых</b></div></div></div></section>

        <section className="section services-section"><div className="wrap"><span className="eyebrow dark">На территории</span><h2 className="display-title">Один курорт — один контур управления</h2><div className="service-grid"><article><b>Ресторан и питание</b><p>Питание гостей и будущий контроль столовой.</p></article><article><b>Магазин</b><p>Учёт будет подключён после подтверждения операционной модели.</p></article><article><b>Бильярд</b><p>Платная услуга — будущий модуль ресурсов.</p></article><article><b>Конференции</b><p>Деловые и групповые заезды на территории отеля.</p></article></div></div></section>

        <section className="section gallery-section" id="gallery"><div className="wrap"><span className="eyebrow dark">Галерея</span><h2 className="display-title">Атмосфера «Трёх Корон»</h2><p className="section-copy">Фотографии здесь временные из текущего V5-каркаса. После получения оригинального медиапакета они будут заменены собственными широкоформатными фото.</p><div className="gallery-grid"><div className="g1" /><div className="g2" /><div className="g3" /><div className="g4" /></div></div></section>

        <section className="final-cta"><div className="wrap final-row"><div><span className="eyebrow">Бронирование</span><h2 className="display-title light">Выберите даты.<br />Система проверит реальное наличие.</h2></div><a className="primary-button gold" href="#booking">Проверить даты</a></div></section>
      </main>
      <a className="mobile-book" href="#booking">Проверить даты</a>
    </>
  );
}
