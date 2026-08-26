import Image from "next/image";
import Link from "next/link";

import BookingWidget from "../components/BookingWidget";
import ResortGallery from "../components/ResortGallery";
import SiteHeader from "../components/SiteHeader";
import { formatKgs, roomCategories } from "../lib/roomCatalog";

const seasonRates = [
  { index: "01", dates: "1 июня — 6 июля", label: "Начало сезона", range: "3 000–13 000 сом" },
  { index: "02", dates: "7 июля — 25 августа", label: "Высокий сезон", range: "4 000–15 500 сом", peak: true },
  { index: "03", dates: "26 августа — 15 сентября", label: "Бархатный сезон", range: "3 000–13 000 сом" },
];

const bookingSteps = [
  ["01", "Выберите даты", "Заезд, выезд и состав гостей задают поиск по реальному инвентарю отеля."],
  ["02", "Сравните варианты", "Resort Core возвращает фактическую доступность и итоговую стоимость для выбранного периода."],
  ["03", "Отправьте заявку", "Выбранная категория и контакты передаются менеджеру. Номер автоматически не блокируется."],
  ["04", "Подтвердите условия", "После согласования условий и предоплаты менеджер создаёт действующую подтверждённую бронь."],
];

const galleryImages = [
  { src: "/media/three-crowns/hero-resort.webp", alt: "Территория Три Короны Resort & SPA", label: "Территория" },
  { src: "/media/three-crowns/room-double.webp", alt: "Номер в Три Короны Resort & SPA", label: "Номерной фонд" },
  { src: "/media/three-crowns/lake-night.webp", alt: "Иссык-Куль у Три Короны Resort & SPA", label: "Иссык-Куль" },
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
  return <>
    <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(hotelJsonLd) }} />
    <SiteHeader />
    <main className="home-page" id="top">
      <section className="home-hero" aria-labelledby="hero-title">
        <div className="home-hero-media" aria-hidden="true"><Image src="/media/three-crowns/hero-resort.webp" alt="" fill priority sizes="100vw" /></div>
        <div className="home-hero-shade" aria-hidden="true" />
        <div className="wrap home-hero-content">
          <p className="eyebrow light">Три Короны · Resort & SPA · Чолпон-Ата</p>
          <h1 id="hero-title">Иссык-Куль.<br />Отдых у самой воды.</h1>
          <p className="home-hero-copy">84 номера, 12 категорий, собственный пляж, 150-метровый пирс, SPA и открытый бассейн 15×8 м — с реальной проверкой свободных вариантов по вашим датам.</p>
          <div className="home-hero-actions"><a className="button button-accent" href="#booking">Проверить свободные номера</a><Link className="button button-quiet" href="/rooms">Смотреть 12 категорий</Link></div>
          <div className="home-hero-facts" aria-label="Ключевые факты"><span>Чолпон-Ата</span><span>84 номера</span><span>12 категорий</span><span>Пирс 150 м</span></div>
        </div>
      </section>

      <div className="wrap home-booking-lift"><BookingWidget /></div>

      <section className="home-section home-intro" aria-labelledby="intro-title">
        <div className="wrap home-intro-grid">
          <div><p className="eyebrow">Три Короны</p><h2 className="display-title" id="intro-title">Курортный ритм<br />у большого озера</h2></div>
          <div className="home-intro-copy"><p>Пляж и длинный пирс задают день у воды, SPA и массаж — спокойный вечер, а номерной фонд позволяет выбрать формат от компактной категории до апартаментов.</p><a className="text-link" href="#resort">Посмотреть курорт →</a></div>
        </div>
        <div className="wrap home-facts" aria-label="Подтверждённые факты о курорте">
          <div className="home-fact"><strong>84</strong><span>номерные позиции</span></div>
          <div className="home-fact"><strong>12</strong><span>категорий размещения</span></div>
          <div className="home-fact"><strong>150 м</strong><span>пирс у собственного пляжа</span></div>
          <div className="home-fact"><strong>15×8 м</strong><span>открытый бассейн</span></div>
        </div>
      </section>

      <section className="home-section home-rooms" id="rooms" aria-labelledby="rooms-title">
        <div className="wrap home-section-head">
          <div><p className="eyebrow">Проживание</p><h2 className="display-title" id="rooms-title">От одноместного номера<br />до апартаментов</h2></div>
          <div className="home-head-copy"><p>В каталоге показываем только подтверждённые параметры: базовую вместимость, площадь и сезонный прайс. Конфигурацию конкретного номера и дополнительные места подтверждает менеджер.</p><Link className="text-link" href="/rooms">Открыть полный каталог →</Link></div>
        </div>
        <div className="wrap home-room-editorial">
          <figure className="home-room-photo"><Image src="/media/three-crowns/room-double.webp" alt="Номер из актуального медиапакета Три Короны" fill sizes="(max-width: 980px) 100vw, 50vw" /><figcaption className="home-room-photo-caption">Фото номерного фонда из актуального медиапакета. Для каждой категории отдельные фотографии будут привязаны после загрузки и верификации фотопакета.</figcaption></figure>
          <div className="home-room-list" role="list">{roomCategories.map((room) => <article className="home-room-row" key={room.slug} role="listitem"><span>{room.index}</span><div><h3>{room.name}</h3><p>{room.capacity} · {room.area}</p></div><Link href={`/rooms/${room.slug}`} aria-label={`Подробнее: ${room.name}`}>Подробнее ↗</Link></article>)}</div>
        </div>
        <div className="wrap home-room-all"><p>Наличие конкретной категории зависит от выбранных дат и текущего инвентаря Resort Core.</p><Link className="button button-accent" href="/rooms">Сравнить все категории</Link></div>
      </section>

      <section className="home-section home-rates" id="rates" aria-labelledby="rates-title">
        <div className="wrap home-section-head">
          <div><p className="eyebrow">Официальный летний прайс · 2026</p><h2 className="display-title" id="rates-title">Прозрачный ориентир.<br />Точная сумма — по датам.</h2></div>
          <div className="home-head-copy"><p>Сезонная матрица даёт ориентир за номер в сутки. Итог проживания рассчитывает Core по выбранным ночам и доступной категории.</p><a className="text-link" href="#booking">Рассчитать мои даты →</a></div>
        </div>
        <div className="wrap home-rate-bands">{seasonRates.map((rate) => <article className={`home-rate-band ${rate.peak ? "is-peak" : ""}`} key={rate.dates}><span>{rate.index} · {rate.label}</span><h3>{rate.dates}</h3><p>официальный сезонный период</p><strong>{rate.range}</strong></article>)}</div>
        <div className="wrap home-rate-table-wrap"><table className="home-rate-table"><thead><tr><th>Категория</th><th>1.06–6.07</th><th>7.07–25.08</th><th>26.08–15.09</th></tr></thead><tbody>{roomCategories.map((room) => <tr key={room.slug}><th>{room.name}</th><td>{formatKgs(room.rates.early)} сом</td><td>{formatKgs(room.rates.peak)} сом</td><td>{formatKgs(room.rates.late)} сом</td></tr>)}</tbody></table></div>
        <div className="wrap home-rate-note"><strong>Важно</strong><p>Летняя матрица отражает официальный прайс 2026. Точный продаваемый тариф, питание и итоговая стоимость для конкретного периода возвращаются системой отеля при поиске.</p></div>
      </section>

      <section className="home-water" id="resort" aria-labelledby="resort-title">
        <div className="home-water-media" aria-hidden="true"><Image src="/media/three-crowns/lake-night.webp" alt="" fill sizes="100vw" /></div>
        <div className="home-water-shade" aria-hidden="true" />
        <div className="wrap home-water-content"><p className="eyebrow light">Берег Иссык-Куля</p><h2 className="display-title light" id="resort-title">Собственный пляж.<br />Пирс длиной 150 метров.</h2><p className="home-water-copy">Пространство у воды — ключевая часть отдыха в «Трёх Коронах». Здесь мы показываем только те характеристики курорта, которые входят в текущую подтверждённую публичную базу проекта.</p><div className="home-water-tags"><span>Собственный пляж</span><span>Пирс 150 м</span><span>Открытый бассейн 15×8 м</span></div></div>
      </section>

      <section className="home-section home-wellness" id="experience" aria-labelledby="wellness-title">
        <div className="wrap home-wellness-grid">
          <div className="home-wellness-copy"><p className="eyebrow">SPA & Wellness</p><h2 className="display-title" id="wellness-title">Спокойное продолжение<br />дня у озера</h2><p className="lead">В текущую подтверждённую публичную инфраструктуру входят SPA, массаж и открытый бассейн 15×8 м. Остальные сервисы публикуем только после отдельной проверки их актуальной операционной доступности.</p><div className="home-wellness-tags"><span>SPA</span><span>Массаж</span><span>Бассейн 15×8 м</span></div><a className="button button-dark" href="#booking">Выбрать даты</a></div>
          <figure className="home-wellness-photo"><Image src="/media/three-crowns/hero-resort.webp" alt="Территория Три Короны Resort & SPA" fill sizes="(max-width: 980px) 100vw, 55vw" /><figcaption>Три Короны · Чолпон-Ата · Иссык-Куль</figcaption></figure>
        </div>
      </section>

      <section className="home-section home-gallery" id="gallery" aria-labelledby="gallery-title">
        <div className="wrap home-section-head"><div><p className="eyebrow">Галерея</p><h2 className="display-title" id="gallery-title">Только локальные<br />материалы проекта</h2></div><div className="home-head-copy"><p>Сейчас используются три материализованных фотографии из репозитория. Категорийные фото будут расширены после загрузки собственником полного медиапакета в подготовленную структуру Drive.</p></div></div>
        <ResortGallery images={galleryImages} />
      </section>

      <section className="home-section home-booking-journey" aria-labelledby="journey-title">
        <div className="wrap home-section-head"><div><p className="eyebrow">Как бронируем</p><h2 className="display-title" id="journey-title">Четыре понятных шага</h2></div><div className="home-head-copy"><p>Сайт не создаёт ложную «бронь» до оплаты. Он проверяет живой инвентарь, принимает заявку и передаёт её менеджеру.</p></div></div>
        <div className="wrap home-steps">{bookingSteps.map(([index, title, text]) => <article className="home-step" key={index}><span>{index}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="home-section home-contacts" id="contacts" aria-labelledby="contacts-title">
        <div className="wrap home-section-head"><div><p className="eyebrow">Контакты</p><h2 className="display-title" id="contacts-title">Связаться с бронированием</h2></div><div className="home-head-copy"><p>Три Короны Resort & SPA находится в Чолпон-Ате, Иссык-Кульская область. Для бронирования используйте подтверждённый телефон или email.</p></div></div>
        <div className="wrap home-contact-grid"><a className="home-contact-card" href="tel:+996558085002"><div><span>Телефон бронирования</span><strong>+996 558 08 50 02</strong><p>Нажмите, чтобы позвонить</p></div><b>Позвонить →</b></a><a className="home-contact-card" href="mailto:3koronykg@mail.ru"><div><span>Email</span><strong>3koronykg@mail.ru</strong><p>Чолпон-Ата · Иссык-Куль</p></div><b>Написать →</b></a></div>
      </section>

      <section className="home-final" aria-labelledby="final-title"><div className="wrap home-final-grid"><div><p className="eyebrow light">Ваши даты</p><h2 className="display-title" id="final-title">Проверьте свободные номера<br />в системе отеля</h2><p>Вы увидите только фактически доступные категории и стоимость для выбранного периода.</p></div><div className="home-final-actions"><a className="button button-accent" href="#booking">Проверить даты</a><a className="button button-quiet" href="tel:+996558085002">Позвонить менеджеру</a></div></div></section>
    </main>

    <footer className="home-footer"><div className="wrap home-footer-inner"><strong>Три Короны · Resort & SPA</strong><div className="home-footer-links"><Link href="/rooms">Номера</Link><a href="/#booking">Бронирование</a><a href="tel:+996558085002">+996 558 08 50 02</a></div></div></footer>
    <a className="mobile-book" href="#booking">Проверить свободные номера</a>
  </>;
}
