import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import BookingWidget from "../../../components/BookingWidget";
import SiteHeader from "../../../components/SiteHeader";
import { formatPublicNumber, getLocalizedRoomCopy, normalizePublicLocale, PublicLocale, withPublicLocale } from "../../../lib/publicLocale";
import { getPublicRoomMedia } from "../../../lib/publicRoomMedia";
import { getRoomCategory, publicRatePeriods, roomCategories } from "../../../lib/roomCatalog";

type RoomPageProps = { params: Promise<{ slug: string }>; searchParams: Promise<{ lang?: string | string[] }> };

const ROOM_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp";

const COPY = {
  ru: {
    all: "← Все категории", category: "Категория", brand: "Три Короны", availability: "Наличие — по выбранным датам", photoReady: "Реальное фото категории", photoGeneric: "Общий вид курорта · фото категории готовятся", about: "О категории", title: <>Ваш формат<br />отдыха у озера</>, tail: "Перед бронированием менеджер поможет уточнить детали конкретного номера и дополнительные места, если они нужны.", placement: "Размещение", area: "Площадь", how: "Как забронировать", safety: "Выберите даты ниже и посмотрите доступность и итоговую стоимость. Отправленная заявка не блокирует номер автоматически: подтверждённая бронь создаётся менеджером после согласования условий и предоплаты.", summer: "Летний прайс · 2026", periods: ["1 июня — 6 июля", "7 июля — 25 августа", "26 августа — 15 сентября"], currency: "сом", note: "Цена указана за номер / сутки по сезонному периоду. Точная сумма за весь отдых рассчитывается после выбора дат.", cta: "Проверить даты", footer: "Бронирование: +996 558 08 50 02", descriptionTail: "Сезонные цены и проверка свободных вариантов по датам.", openGraphTail: "Проверьте наличие и стоимость проживания на свои даты.", imageAlt: "Три Короны Resort & SPA",
  },
  kg: {
    all: "← Бардык категориялар", category: "Категория", brand: "Үч Таажы", availability: "Бош орун — тандалган даталар боюнча", photoReady: "Категориянын чыныгы сүрөтү", photoGeneric: "Курорттун жалпы көрүнүшү · категориянын сүрөттөрү даярдалууда", about: "Категория жөнүндө", title: <>Көл жээгиндеги<br />сиздин эс алуу форматы</>, tail: "Брондоодон мурун менеджер конкреттүү номердин деталдарын жана керек болсо кошумча орундарды тактоого жардам берет.", placement: "Жайгашуу", area: "Аянты", how: "Кантип брондоо керек", safety: "Төмөндө даталарды тандап, бош орунду жана акыркы сумманы көрүңүз. Жөнөтүлгөн өтүнмө номерди автоматтык түрдө кармабайт: ырасталган бронь шарттар жана алдын ала төлөм макулдашылгандан кийин менеджер тарабынан түзүлөт.", summer: "Жайкы прайс · 2026", periods: ["1-июнь — 6-июль", "7-июль — 25-август", "26-август — 15-сентябрь"], currency: "сом", note: "Баасы сезондук мезгил боюнча номер / түн үчүн көрсөтүлгөн. Бүт эс алуунун так суммасы даталарды тандагандан кийин эсептелет.", cta: "Даталарды текшерүү", footer: "Брондоо: +996 558 08 50 02", descriptionTail: "Сезондук баалар жана даталар боюнча бош орундарды текшерүү.", openGraphTail: "Даталарыңызга бош орунду жана жашоонун баасын текшериңиз.", imageAlt: "Үч Таажы Resort & SPA",
  },
  en: {
    all: "← All categories", category: "Category", brand: "Three Crowns", availability: "Availability — for your selected dates", photoReady: "Real category photo", photoGeneric: "General resort view · category photos are being prepared", about: "About this category", title: <>Your way to stay<br />by the lake</>, tail: "Before booking, the manager can help confirm details of the exact room and any extra-bed requirements.", placement: "Accommodation", area: "Area", how: "How to book", safety: "Choose dates below to see availability and the full price. A submitted request does not automatically hold the room: a confirmed reservation is created by the manager after the terms and prepayment are agreed.", summer: "Summer rates · 2026", periods: ["1 June — 6 July", "7 July — 25 August", "26 August — 15 September"], currency: "KGS", note: "The price is per room / night for the seasonal period. The exact full-stay total is calculated after you choose dates.", cta: "Check dates", footer: "Reservations: +996 558 08 50 02", descriptionTail: "Seasonal rates and live availability for selected dates.", openGraphTail: "Check availability and the total stay price for your dates.", imageAlt: "Three Crowns Resort & SPA",
  },
} satisfies Record<PublicLocale, Record<string, unknown>>;

export function generateStaticParams() {
  return roomCategories.map((room) => ({ slug: room.slug }));
}

async function pageLocale(searchParams: RoomPageProps["searchParams"]): Promise<PublicLocale> {
  const params = await searchParams;
  const raw = Array.isArray(params.lang) ? params.lang[0] : params.lang;
  return normalizePublicLocale(raw);
}

export async function generateMetadata({ params, searchParams }: RoomPageProps): Promise<Metadata> {
  const { slug } = await params;
  const room = getRoomCategory(slug);
  if (!room) return {};
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  const localized = getLocalizedRoomCopy(slug, locale) ?? { name: room.name, capacity: room.capacity, summary: room.summary };
  const media = getPublicRoomMedia(slug);
  const url = locale === "ru" ? `/rooms/${room.slug}` : `/rooms/${room.slug}?lang=${locale}`;
  const description = `${localized.name} · ${copy.brand}: ${localized.capacity}, ${room.area}. ${String(copy.descriptionTail)}`;
  return {
    title: localized.name,
    description,
    alternates: {
      canonical: url,
      languages: {
        "ru-RU": `/rooms/${room.slug}`,
        "ky-KG": `/rooms/${room.slug}?lang=kg`,
        "en-US": `/rooms/${room.slug}?lang=en`,
      },
    },
    openGraph: {
      title: `${localized.name} · ${String(copy.brand)}`,
      description: `${localized.capacity} · ${room.area}. ${String(copy.openGraphTail)}`,
      url,
      locale: locale === "en" ? "en_US" : locale === "kg" ? "ky_KG" : "ru_RU",
      images: [{ url: media?.hero ?? ROOM_MEDIA_FALLBACK, alt: media ? localized.name : String(copy.imageAlt) }],
    },
  };
}

export default async function RoomCategoryPage({ params, searchParams }: RoomPageProps) {
  const { slug } = await params;
  const room = getRoomCategory(slug);
  if (!room) notFound();
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  const localized = getLocalizedRoomCopy(slug, locale) ?? { name: room.name, capacity: room.capacity, summary: room.summary };
  const media = getPublicRoomMedia(slug);
  const hero = media?.hero ?? ROOM_MEDIA_FALLBACK;

  return <>
    <SiteHeader />
    <main className="rooms-page" id="top">
      <section className={`room-detail-hero ${media ? "has-approved-room-media" : "uses-resort-fallback"}`} aria-labelledby="room-detail-title">
        <div className="room-detail-hero-media" aria-hidden="true"><Image src={hero} alt="" fill priority sizes="100vw" /></div>
        <div className="room-detail-hero-shade" aria-hidden="true" />
        <div className="wrap room-detail-hero-content">
          <Link className="room-detail-back" href={withPublicLocale("/rooms", locale)}>{String(copy.all)}</Link>
          <p className="eyebrow light">{String(copy.category)} {room.index} · {String(copy.brand)}</p>
          <h1 id="room-detail-title">{localized.name}</h1>
          <div className="room-detail-kicker"><span>{localized.capacity}</span><span>{room.area}</span><span>{String(copy.availability)}</span><span className="room-photo-truth">{String(media ? copy.photoReady : copy.photoGeneric)}</span></div>
        </div>
      </section>

      <section className="room-detail-main">
        <div className="wrap room-detail-layout">
          <div className="room-detail-copy">
            <p className="eyebrow">{String(copy.about)}</p>
            <h2 className="display-title">{copy.title as React.ReactNode}</h2>
            <p className="lead">{localized.summary} {String(copy.tail)}</p>
            <div className="room-detail-facts"><div><span>{String(copy.placement)}</span><strong>{localized.capacity}</strong></div><div><span>{String(copy.area)}</span><strong>{room.area}</strong></div></div>
            <div className="room-detail-safety"><strong>{String(copy.how)}</strong><p>{String(copy.safety)}</p></div>
          </div>

          <aside className="room-rate-card" aria-label={String(copy.summer)}>
            <p>{String(copy.summer)}</p>
            {publicRatePeriods.map((period, index) => <div className="room-rate-row" key={period.key}><span>{String((copy.periods as string[])[index])}</span><strong>{formatPublicNumber(room.rates[period.key], locale)} {String(copy.currency)}</strong></div>)}
            <p className="room-rate-note">{String(copy.note)}</p>
            <a className="button button-accent room-rate-cta" href="#booking">{String(copy.cta)}</a>
          </aside>
        </div>
      </section>

      <div className="wrap room-detail-booking"><BookingWidget /></div>
    </main>
    <footer className="rooms-footer"><div className="wrap rooms-footer-inner"><strong>{String(copy.brand)} · Resort & SPA</strong><a href="tel:+996558085002">{String(copy.footer)}</a></div></footer>
  </>;
}
