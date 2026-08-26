import Image from "next/image";
import Link from "next/link";

import ActionRuntime from "../components/ActionRuntime";
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
  ["02", "Увидьте живое наличие", "Resort Core возвращает фактическую доступность и итоговую стоимость для выбранного периода."],
  ["03", "Отправьте заявку", "Выбранная категория и контакты передаются менеджеру. Номер автоматически не блокируется."],
  ["04", "Подтвердите бронь", "После согласования условий и предоплаты менеджер создаёт действующую подтверждённую бронь."],
];

const galleryImages = [
  { src: "/media/three-crowns/hero-resort.webp", alt: "Территория Три Короны Resort & SPA", label: "Территория" },
  { src: "/media/three-crowns/room-double.webp", alt: "Номер в Три Короны Resort & SPA", label: "Номерной фонд" },
  { src: "/media/three-crowns/lake-night.webp", alt: "Иссык-Куль у Три Короны Resort & SPA", label: "Иссык-Куль" },
];

const ticker = ["84 номера", "12 категорий", "Собственный пляж", "Пирс 150 м", "SPA", "Бассейн 15×8 м", "Чолпон-Ата", "Иссык-Куль"];

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
    <ActionRuntime />
    <SiteHeader />

    <main className="home-page action-home" id="top">
      <section className="action-hero" aria-labelledby="hero-title">
        <div className="action-hero-media" aria-hidden="true">
          <Image src="/media/three-crowns/hero-resort.webp" alt="" fill priority sizes="100vw" />
        </div>
        <div className="action-hero-noise" aria-hidden="true" />
        <div className="wrap action-hero-content">
          <p className="action-hero-kicker" data-reveal>Resort & SPA · Чолпон-Ата</p>
          <h1 className="action-hero-title" id="hero-title" data-reveal data-delay="1">Три Короны.<em>Иссык-Куль.</em></h1>
          <div className="action-hero-bottom" data-reveal data-delay="2">
            <div>
              <p className="action-hero-copy">Отдых у самой воды: 84 номера, собственный пляж, 150-метровый пирс, SPA и открытый бассейн. Свободные варианты проверяются по реальному инвентарю отеля.</p>
              <div className="action-hero-actions">
                <a className="button button-accent" href="#booking">Проверить мои даты</a>
                <Link className="button button-quiet" href="/rooms">Смотреть 12 категорий</Link>
              </div>
            </div>
            <a className="action-hero-orbit" href="#story" aria-label="Прокрутить к истории курорта"><span>Scroll<br />to explore ↓</span></a>
          </div>
          <div className="action-hero-index" aria-hidden="true">CHOLPON-ATA · ISSYK-KUL</div>
        </div>
      </section>

      <div className="action-ticker" aria-hidden="true">
        <div className="action-ticker-track">
          {[...ticker, ...ticker].map((item, index) => <span key={`${item}-${index}`}>{item}</span>)}
        </div>
      </div>

      <section className="action-booking-wrap" aria-label="Проверка доступности">
        <div className="wrap"><BookingWidget /></div>
      </section>

      <section className="action-section action-intro" id="story" aria-labelledby="story-title">
        <div className="wrap action-intro-grid">
          <div className="action-intro-number" data-reveal>
            <strong>84</strong>
            <span>номера в инвентаре курорта</span>
          </div>
          <div className="action-intro-story" data-reveal data-delay="1">
            <p className="eyebrow">Три Короны</p>
            <h2 id="story-title">День начинается <em>у воды.</em></h2>
            <p>Пляж и длинный пирс задают ритм дня, SPA и массаж — спокойный вечер, а 12 категорий размещения позволяют выбрать формат от компактного номера до апартаментов.</p>
            <div className="action-proof" aria-label="Ключевые факты курорта">
              <div><strong>12</strong><span>категорий</span></div>
              <div><strong>150 м</strong><span>пирс</span></div>
              <div><strong>15×8 м</strong><span>бассейн</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="action-section action-rooms" id="rooms" aria-labelledby="rooms-title">
        <div className="wrap action-section-head">
          <div data-reveal>
            <p className="eyebrow">Проживание</p>
            <h2 className="display-title" id="rooms-title">12 категорий.<br />Один курортный ритм.</h2>
          </div>
          <div className="action-section-copy" data-reveal data-delay="1">
            <p>Показываем только подтверждённые параметры: вместимость, площадь и официальный сезонный прайс. Точное наличие по датам приходит из Resort Core.</p>
            <Link className="text-link" href="/rooms">Открыть полный каталог →</Link>
          </div>
        </div>

        <div className="action-room-rail-wrap" data-reveal data-delay="2">
          <div className="wrap action-room-rail-label"><span>Листайте горизонтально</span><span>01 — 12</span></div>
          <div className="action-room-rail" role="list" aria-label="Категории номеров">
            {roomCategories.map((room) => (
              <article className="action-room-card" data-index={room.index} key={room.slug} role="listitem">
                <div className="action-room-card-top"><span>{room.index}</span><span>{formatKgs(room.rates.peak)} сом · high season</span></div>
                <div>
                  <h3>{room.name}</h3>
                  <div className="action-room-card-meta"><span>{room.capacity}</span><span>{room.area}</span></div>
                  <Link className="action-room-card-link" href={`/rooms/${room.slug}`} aria-label={`Подробнее: ${room.name}`}><span>Открыть категорию</span><b>↗</b></Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="action-section action-rates" id="rates" aria-labelledby="rates-title">
        <div className="wrap action-section-head">
          <div data-reveal>
            <p className="eyebrow">Официальный летний прайс · 2026</p>
            <h2 className="display-title" id="rates-title">Три периода.<br />Цена без тумана.</h2>
          </div>
          <div className="action-section-copy" data-reveal data-delay="1">
            <p>Матрица ниже — официальный ориентир за номер в сутки. Итог проживания по конкретным ночам рассчитывает система отеля.</p>
            <a className="text-link" href="#booking">Рассчитать мои даты →</a>
          </div>
        </div>

        <div className="wrap action-season-grid" data-reveal data-delay="2">
          {seasonRates.map((rate) => <article className={`action-season-card ${rate.peak ? "is-peak" : ""}`} key={rate.dates}>
            <span>{rate.index} · {rate.label}</span>
            <h3>{rate.dates}</h3>
            <p>официальный сезонный период</p>
            <strong>{rate.range}</strong>
          </article>)}
        </div>

        <div className="wrap" data-reveal>
          <details className="action-rate-details">
            <summary>Показать полный прайс по 12 категориям</summary>
            <table className="action-rate-table">
              <thead><tr><th>Категория</th><th>1.06–6.07</th><th>7.07–25.08</th><th>26.08–15.09</th></tr></thead>
              <tbody>{roomCategories.map((room) => <tr key={room.slug}><th>{room.name}</th><td>{formatKgs(room.rates.early)} сом</td><td>{formatKgs(room.rates.peak)} сом</td><td>{formatKgs(room.rates.late)} сом</td></tr>)}</tbody>
            </table>
          </details>
          <div className="action-rate-note"><strong>Важно</strong><span>Точный продаваемый тариф, питание и итоговая стоимость конкретного периода возвращаются системой отеля при поиске доступности.</span></div>
        </div>
      </section>

      <section className="action-water" id="resort" aria-labelledby="resort-title">
        <div className="action-water-media" aria-hidden="true"><Image src="/media/three-crowns/lake-night.webp" alt="" fill sizes="100vw" /></div>
        <div className="action-water-ghost" aria-hidden="true">150</div>
        <div className="wrap action-water-content">
          <p className="eyebrow light" data-reveal>Берег Иссык-Куля</p>
          <h2 id="resort-title" data-reveal data-delay="1">150 метров<br />в сторону озера.</h2>
          <div className="action-water-bottom" data-reveal data-delay="2">
            <p>Собственный пляж и пирс длиной 150 метров — ключевая часть отдыха в «Трёх Коронах». Пространство у воды работает как главный визуальный и эмоциональный центр курорта.</p>
            <div className="action-water-tags"><span>Собственный пляж</span><span>Пирс 150 м</span><span>Бассейн 15×8 м</span></div>
          </div>
        </div>
      </section>

      <section className="action-section action-wellness" id="experience" aria-labelledby="wellness-title">
        <div className="wrap action-wellness-grid">
          <div className="action-wellness-copy" data-reveal>
            <p className="eyebrow">SPA & Wellness</p>
            <h2 id="wellness-title">Сбавить темп.<br /><em>Не впечатления.</em></h2>
            <p>В подтверждённую инфраструктуру входят SPA, массаж и открытый бассейн 15×8 м. Остальные сервисы публикуем только после проверки их актуальной операционной доступности.</p>
            <div className="action-wellness-list"><span>SPA</span><span>Массаж</span><span>Открытый бассейн</span></div>
            <a className="button button-dark" href="#booking">Выбрать даты</a>
          </div>
          <div className="action-wellness-visual" data-reveal data-delay="1">
            <figure className="action-wellness-photo"><Image src="/media/three-crowns/hero-resort.webp" alt="Территория Три Короны Resort & SPA" fill sizes="(max-width: 760px) 100vw, 60vw" /></figure>
            <div className="action-wellness-float"><strong>15×8</strong><span>метров · открытый бассейн</span></div>
          </div>
        </div>
      </section>

      <section className="action-section action-gallery home-gallery" id="gallery" aria-labelledby="gallery-title">
        <div className="wrap action-section-head">
          <div data-reveal><p className="eyebrow">Галерея</p><h2 className="display-title" id="gallery-title">Увидеть место.<br />Почувствовать масштаб.</h2></div>
          <div className="action-section-copy" data-reveal data-delay="1"><p>Сейчас на сайте используются локальные материалы проекта. Галерею расширяем только собственными и подтверждёнными фотографиями курорта.</p></div>
        </div>
        <div data-reveal data-delay="2"><ResortGallery images={galleryImages} /></div>
      </section>

      <section className="action-section action-journey" aria-labelledby="journey-title">
        <div className="wrap action-section-head">
          <div data-reveal><p className="eyebrow">Бронирование</p><h2 className="display-title" id="journey-title">От дат<br />до подтверждения.</h2></div>
          <div className="action-section-copy" data-reveal data-delay="1"><p>Без фиктивной доступности и ложной «брони». Сайт сначала проверяет реальный инвентарь, затем передаёт заявку менеджеру.</p></div>
        </div>
        <div className="wrap action-step-grid" data-reveal data-delay="2">
          {bookingSteps.map(([index, title, text]) => <article className="action-step" data-step={index} key={index}><span>{index}</span><h3>{title}</h3><p>{text}</p></article>)}
        </div>
      </section>

      <section className="action-section action-contacts" id="contacts" aria-labelledby="contacts-title">
        <div className="wrap action-section-head">
          <div data-reveal><p className="eyebrow">Контакты</p><h2 className="display-title" id="contacts-title">Связаться.<br />И ехать к воде.</h2></div>
          <div className="action-section-copy" data-reveal data-delay="1"><p>Три Короны Resort & SPA находится в Чолпон-Ате, Иссык-Кульская область. Для бронирования используйте подтверждённый телефон или email.</p></div>
        </div>
        <div className="wrap action-contact-grid" data-reveal data-delay="2">
          <a className="action-contact-card" href="tel:+996558085002"><span>Телефон бронирования</span><strong>+996 558<br />08 50 02</strong><b><span>Позвонить</span><span>↗</span></b></a>
          <a className="action-contact-card" href="mailto:3koronykg@mail.ru"><span>Email</span><strong>3koronykg<br />@mail.ru</strong><b><span>Написать</span><span>↗</span></b></a>
        </div>
      </section>

      <section className="action-final" aria-labelledby="final-title">
        <div className="wrap action-final-grid">
          <div data-reveal>
            <p className="eyebrow light">Ваши даты</p>
            <h2 id="final-title">Свободный номер<br />начинается здесь.</h2>
            <p>Выберите даты — Resort Core вернёт фактически доступные категории и стоимость для выбранного периода.</p>
          </div>
          <div className="action-final-actions" data-reveal data-delay="1">
            <a className="button button-accent" href="#booking">Проверить даты</a>
            <a className="button button-quiet" href="tel:+996558085002">Позвонить менеджеру</a>
          </div>
        </div>
      </section>
    </main>

    <footer className="action-footer"><div className="wrap action-footer-inner"><strong>Три Короны · Resort & SPA</strong><div className="action-footer-links"><Link href="/rooms">Номера</Link><a href="/#booking">Бронирование</a><a href="tel:+996558085002">+996 558 08 50 02</a></div></div></footer>
    <a className="mobile-book" href="#booking">Проверить свободные номера</a>
  </>;
}
