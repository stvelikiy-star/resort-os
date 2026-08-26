import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import BookingWidget from "../../../components/BookingWidget";
import SiteHeader from "../../../components/SiteHeader";
import { formatKgs, getRoomCategory, publicRatePeriods, roomCategories } from "../../../lib/roomCatalog";

type RoomPageProps = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return roomCategories.map((room) => ({ slug: room.slug }));
}

export async function generateMetadata({ params }: RoomPageProps): Promise<Metadata> {
  const { slug } = await params;
  const room = getRoomCategory(slug);
  if (!room) return {};

  return {
    title: room.name,
    description: `${room.name} в Три Короны Resort & SPA: ${room.capacity}, ${room.area}. Сезонный прайс и реальная проверка доступности по датам.`,
    alternates: { canonical: `/rooms/${room.slug}` },
    openGraph: {
      title: `${room.name} · Три Короны`,
      description: `${room.capacity} · ${room.area}. Проверьте реальную доступность и итоговую стоимость на свои даты.`,
      url: `/rooms/${room.slug}`,
    },
  };
}

export default async function RoomCategoryPage({ params }: RoomPageProps) {
  const { slug } = await params;
  const room = getRoomCategory(slug);
  if (!room) notFound();

  return <>
    <SiteHeader />
    <main className="rooms-page" id="top">
      <section className="room-detail-hero" aria-labelledby="room-detail-title">
        <div className="wrap">
          <Link className="room-detail-back" href="/rooms">← Все категории</Link>
          <p className="eyebrow light">Категория {room.index} · Три Короны</p>
          <h1 id="room-detail-title">{room.name}</h1>
          <div className="room-detail-kicker"><span>{room.capacity}</span><span>{room.area}</span><span>Проверка наличия через Resort Core</span></div>
        </div>
      </section>

      <section className="room-detail-main">
        <div className="wrap room-detail-layout">
          <div className="room-detail-copy">
            <p className="eyebrow">О категории</p>
            <h2 className="display-title">Понятный формат<br />без неподтверждённых деталей</h2>
            <p className="lead">{room.summary} Точную конфигурацию конкретного номера, дополнительные места и другие детали размещения менеджер подтверждает для выбранных дат.</p>
            <div className="room-detail-facts"><div><span>Базовая вместимость</span><strong>{room.capacity}</strong></div><div><span>Площадь</span><strong>{room.area}</strong></div></div>
            <div className="room-detail-safety"><strong>Как работает бронирование</strong><p>Выберите даты ниже. Система покажет фактическую доступность и стоимость. Отправленная заявка не блокирует номер автоматически: подтверждённая бронь создаётся менеджером после согласования условий и предоплаты.</p></div>
          </div>

          <aside className="room-rate-card" aria-label="Сезонный прайс категории">
            <p>Официальный летний прайс · 2026</p>
            {publicRatePeriods.map((period) => <div className="room-rate-row" key={period.key}><span>{period.label}</span><strong>{formatKgs(room.rates[period.key])} сом</strong></div>)}
            <p className="room-rate-note">Цена указана за номер / сутки по сезонной матрице. Точная сумма за поездку рассчитывается по выбранным ночам в Resort Core.</p>
          </aside>
        </div>
      </section>

      <div className="wrap room-detail-booking" id="booking"><BookingWidget /></div>
    </main>
    <footer className="rooms-footer"><div className="wrap rooms-footer-inner"><strong>Три Короны · Resort & SPA</strong><a href="tel:+996558085002">Бронирование: +996 558 08 50 02</a></div></footer>
  </>;
}
