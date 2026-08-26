import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import BookingWidget from "../../components/BookingWidget";
import SiteHeader from "../../components/SiteHeader";
import { formatKgs, roomCategories } from "../../lib/roomCatalog";

export const metadata: Metadata = {
  title: "Номера и апартаменты",
  description: "12 категорий размещения в Три Короны Resort & SPA: площадь, вместимость, официальный сезонный прайс и проверка реальной доступности через систему отеля.",
  alternates: { canonical: "/rooms" },
  openGraph: {
    title: "Номера и апартаменты · Три Короны",
    description: "Сравните 12 категорий и проверьте реальную стоимость на выбранные даты.",
    url: "/rooms",
    images: [{ url: "/media/three-crowns/room-double.webp", alt: "Номер в Три Короны Resort & SPA" }],
  },
};

export default function RoomsPage() {
  return <>
    <SiteHeader />
    <main className="rooms-page" id="top">
      <section className="rooms-hero" aria-labelledby="rooms-page-title">
        <div className="rooms-hero-media" aria-hidden="true"><Image src="/media/three-crowns/room-double.webp" alt="" fill priority sizes="100vw" /></div>
        <div className="rooms-hero-shade" aria-hidden="true" />
        <div className="wrap rooms-hero-content">
          <p className="eyebrow light">Проживание · 12 категорий</p>
          <h1 id="rooms-page-title">Номер под ваш<br />сценарий отдыха</h1>
          <p className="rooms-hero-copy">От компактных одноместных вариантов до двухкомнатных категорий и апартаментов. Сначала сравните формат, затем проверьте реальные свободные номера и итоговую стоимость на свои даты.</p>
          <div className="rooms-hero-actions"><a className="button button-accent" href="#catalog">Смотреть категории</a><a className="button button-quiet" href="#booking">Проверить даты</a></div>
        </div>
      </section>

      <section className="catalog-section" id="catalog" aria-labelledby="catalog-title">
        <div className="wrap catalog-heading">
          <div><p className="eyebrow">Каталог</p><h2 className="display-title" id="catalog-title">12 категорий.<br />Без лишних обещаний.</h2></div>
          <p>Показываем только подтверждённые параметры категории: базовую вместимость, площадь и официальный сезонный прайс 2026. Конфигурацию конкретного номера и дополнительные места подтверждает менеджер.</p>
        </div>
        <div className="wrap room-catalog-grid">
          {roomCategories.map((room) => <article className="room-catalog-card" key={room.slug}>
            <div className="room-catalog-card-top"><span className="room-catalog-index">{room.index}</span><span className="room-catalog-meta">{room.capacity} · {room.area}</span></div>
            <h2>{room.name}</h2>
            <p>{room.summary}</p>
            <div className="room-catalog-price"><span>Высокий сезон</span><strong>{formatKgs(room.rates.peak)} сом / сутки</strong></div>
            <Link className="text-link" href={`/rooms/${room.slug}`}>Подробнее о категории →</Link>
          </article>)}
        </div>
        <div className="wrap catalog-truth">
          <div><strong>Цена на сайте — ориентир по официальному прайсу.</strong><p>Точная стоимость проживания считается Resort Core для выбранного периода и доступного инвентаря.</p></div>
          <div><strong>Заявка ≠ подтверждённая бронь.</strong><p>После отправки заявки номер автоматически не блокируется. Менеджер согласует условия и предоплату; действующая бронь появляется только после менеджерского подтверждения.</p></div>
        </div>
      </section>

      <div className="wrap catalog-booking"><BookingWidget /></div>
    </main>
    <footer className="rooms-footer"><div className="wrap rooms-footer-inner"><strong>Три Короны · Resort & SPA</strong><a href="tel:+996558085002">Бронирование: +996 558 08 50 02</a></div></footer>
  </>;
}
