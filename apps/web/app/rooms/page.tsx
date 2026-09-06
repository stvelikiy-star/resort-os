import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import BookingWidget from "../../components/BookingWidget";
import SiteHeader from "../../components/SiteHeader";
import { formatPublicNumber, getLocalizedRoomCopy, normalizePublicLocale, PublicLocale, withPublicLocale } from "../../lib/publicLocale";
import { getPublicRoomMedia } from "../../lib/publicRoomMedia";
import { roomCategories } from "../../lib/roomCatalog";

type RoomsPageProps = { searchParams: Promise<{ lang?: string | string[] }> };

const ROOM_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp";

const COPY = {
  ru: {
    title: "Номера и апартаменты", description: "12 категорий размещения в Три Короны Resort & SPA: площадь, вместимость, сезонные цены и проверка свободных вариантов на выбранные даты.",
    heroEyebrow: "Проживание · 12 категорий", heroTitle: <>Номер под ваш<br />ритм отдыха</>, heroCopy: "От компактных вариантов для одного-двух гостей до просторных двухкомнатных категорий и апартаментов. Сравните формат, цену и проверьте, что свободно на ваши даты.", browse: "Смотреть категории", dates: "Проверить даты",
    catalog: "Каталог", catalogTitle: <>12 категорий.<br />Выберите свою.</>, catalogCopy: "Сравнивайте вместимость, площадь и сезонную стоимость. Детали конкретного размещения и дополнительные места можно уточнить у менеджера перед подтверждением брони.", peak: "Высокий сезон", suffix: "сом / сутки", details: "Подробнее о категории →", photoReady: "Реальные фото категории", photoPending: "Фото категории готовятся",
    truth1Title: "Стоимость зависит от дат.", truth1: "Сезонный прайс помогает сравнить категории, а точная сумма за весь период показывается после проверки выбранных дат.", truth2Title: "Заявка ≠ подтверждённая бронь.", truth2: "После отправки заявки номер автоматически не блокируется. Менеджер согласует условия и предоплату; действующая бронь появляется только после менеджерского подтверждения.", footer: "Бронирование: +996 558 08 50 02", brand: "Три Короны · Resort & SPA",
  },
  kg: {
    title: "Номерлер жана апартаменттер", description: "Үч Таажы Resort & SPAдагы жайгашуунун 12 категориясы: аянты, сыйымдуулугу, сезондук баалары жана тандалган даталарга бош орундарды текшерүү.",
    heroEyebrow: "Жайгашуу · 12 категория", heroTitle: <>Сиздин эс алуу<br />ритмиңизге ылайык номер</>, heroCopy: "Бир-эки конок үчүн компакттуу варианттардан кең эки бөлмөлүү категорияларга жана апартаменттерге чейин. Форматты, бааны салыштырып, даталарыңызга эмне бош экенин текшериңиз.", browse: "Категорияларды көрүү", dates: "Даталарды текшерүү",
    catalog: "Каталог", catalogTitle: <>12 категория.<br />Өзүңүздүкүн тандаңыз.</>, catalogCopy: "Сыйымдуулукту, аянтты жана сезондук бааны салыштырыңыз. Конкреттүү номердин деталдарын жана кошумча орундарды бронду ырастоодон мурун менеджерден тактоого болот.", peak: "Жогорку сезон", suffix: "сом / түн", details: "Категория жөнүндө толук →", photoReady: "Категориянын чыныгы сүрөттөрү", photoPending: "Категориянын сүрөттөрү даярдалууда",
    truth1Title: "Баасы даталарга жараша өзгөрөт.", truth1: "Сезондук прайс категорияларды салыштырууга жардам берет, ал эми бүт мезгилдин так суммасы тандалган даталар текшерилгенден кийин көрсөтүлөт.", truth2Title: "Өтүнмө ≠ ырасталган бронь.", truth2: "Өтүнмө жөнөтүлгөндөн кийин номер автоматтык түрдө кармалбайт. Менеджер шарттарды жана алдын ала төлөмдү макулдашат; активдүү бронь менеджер ырастагандан кийин гана пайда болот.", footer: "Брондоо: +996 558 08 50 02", brand: "Үч Таажы · Resort & SPA",
  },
  en: {
    title: "Rooms and Apartments", description: "12 accommodation categories at Three Crowns Resort & SPA with capacity, area, seasonal rates and live availability for selected dates.",
    heroEyebrow: "Accommodation · 12 categories", heroTitle: <>A room for your<br />holiday rhythm</>, heroCopy: "From compact options for one or two guests to spacious two-room categories and apartments. Compare the format and price, then check what is free for your dates.", browse: "Browse categories", dates: "Check dates",
    catalog: "Catalogue", catalogTitle: <>12 categories.<br />Choose yours.</>, catalogCopy: "Compare capacity, area and seasonal rates. Details of the exact room and extra-bed options can be confirmed with the manager before the reservation is finalised.", peak: "High season", suffix: "KGS / night", details: "Category details →", photoReady: "Real category photos", photoPending: "Category photos are being prepared",
    truth1Title: "Price depends on dates.", truth1: "Seasonal rates help compare categories; the exact full-stay amount is shown after checking your chosen dates.", truth2Title: "Request ≠ confirmed reservation.", truth2: "Submitting a request does not automatically hold a room. The manager agrees the terms and prepayment; an active reservation appears only after manager confirmation.", footer: "Reservations: +996 558 08 50 02", brand: "Three Crowns · Resort & SPA",
  },
} satisfies Record<PublicLocale, Record<string, unknown>>;

async function pageLocale(searchParams: RoomsPageProps["searchParams"]): Promise<PublicLocale> {
  const params = await searchParams;
  const raw = Array.isArray(params.lang) ? params.lang[0] : params.lang;
  return normalizePublicLocale(raw);
}

export async function generateMetadata({ searchParams }: RoomsPageProps): Promise<Metadata> {
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  const title = String(copy.title);
  const description = String(copy.description);
  return {
    title,
    description,
    alternates: {
      canonical: locale === "ru" ? "/rooms" : `/rooms?lang=${locale}`,
      languages: { "ru-RU": "/rooms", "ky-KG": "/rooms?lang=kg", "en-US": "/rooms?lang=en" },
    },
    openGraph: {
      title: `${title} · ${locale === "en" ? "Three Crowns" : locale === "kg" ? "Үч Таажы" : "Три Короны"}`,
      description,
      url: locale === "ru" ? "/rooms" : `/rooms?lang=${locale}`,
      locale: locale === "en" ? "en_US" : locale === "kg" ? "ky_KG" : "ru_RU",
      images: [{ url: ROOM_MEDIA_FALLBACK, alt: locale === "en" ? "Three Crowns Resort & SPA" : locale === "kg" ? "Үч Таажы Resort & SPA" : "Три Короны Resort & SPA" }],
    },
  };
}

export default async function RoomsPage({ searchParams }: RoomsPageProps) {
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  return <>
    <SiteHeader />
    <main className="rooms-page" id="top">
      <section className="rooms-hero" aria-labelledby="rooms-page-title">
        <div className="rooms-hero-media" aria-hidden="true"><Image src={ROOM_MEDIA_FALLBACK} alt="" fill priority sizes="100vw" /></div>
        <div className="rooms-hero-shade" aria-hidden="true" />
        <div className="wrap rooms-hero-content">
          <p className="eyebrow light">{String(copy.heroEyebrow)}</p>
          <h1 id="rooms-page-title">{copy.heroTitle as React.ReactNode}</h1>
          <p className="rooms-hero-copy">{String(copy.heroCopy)}</p>
          <div className="rooms-hero-actions"><a className="button button-accent" href="#catalog">{String(copy.browse)}</a><a className="button button-quiet" href="#booking">{String(copy.dates)}</a></div>
        </div>
      </section>

      <section className="catalog-section" id="catalog" aria-labelledby="catalog-title">
        <div className="wrap catalog-heading">
          <div><p className="eyebrow">{String(copy.catalog)}</p><h2 className="display-title" id="catalog-title">{copy.catalogTitle as React.ReactNode}</h2></div>
          <p>{String(copy.catalogCopy)}</p>
        </div>
        <div className="wrap room-catalog-grid">
          {roomCategories.map((room) => {
            const localized = getLocalizedRoomCopy(room.slug, locale) ?? { name: room.name, capacity: room.capacity, summary: room.summary };
            const media = getPublicRoomMedia(room.slug);
            return <article className={`room-catalog-card ${media ? "has-approved-media" : "media-pending"}`} key={room.slug}>
              <div className="room-catalog-media">
                {media ? <Image src={media.hero} alt={localized.name} fill sizes="(max-width: 620px) 86vw, (max-width: 1080px) 50vw, 34vw" /> : <div className="room-media-pending-panel" aria-label={String(copy.photoPending)}><span>{room.index}</span><strong>{String(copy.photoPending)}</strong></div>}
                <span className="room-media-status">{String(media ? copy.photoReady : copy.photoPending)}</span>
              </div>
              <div className="room-catalog-body">
                <div className="room-catalog-card-top"><span className="room-catalog-index">{room.index}</span><span className="room-catalog-meta">{localized.capacity} · {room.area}</span></div>
                <h2>{localized.name}</h2>
                <p>{localized.summary}</p>
                <div className="room-catalog-price"><span>{String(copy.peak)}</span><strong>{formatPublicNumber(room.rates.peak, locale)} {String(copy.suffix)}</strong></div>
                <Link className="text-link" href={withPublicLocale(`/rooms/${room.slug}`, locale)}>{String(copy.details)}</Link>
              </div>
            </article>;
          })}
        </div>
        <div className="wrap catalog-truth">
          <div><strong>{String(copy.truth1Title)}</strong><p>{String(copy.truth1)}</p></div>
          <div><strong>{String(copy.truth2Title)}</strong><p>{String(copy.truth2)}</p></div>
        </div>
      </section>

      <div className="wrap catalog-booking"><BookingWidget /></div>
    </main>
    <footer className="rooms-footer"><div className="wrap rooms-footer-inner"><strong>{String(copy.brand)}</strong><a href="tel:+996558085002">{String(copy.footer)}</a></div></footer>
  </>;
}
