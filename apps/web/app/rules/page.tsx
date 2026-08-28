import type { Metadata } from "next";
import Image from "next/image";

import SiteHeader from "../../components/SiteHeader";
import { normalizePublicLocale, PublicLocale } from "../../lib/publicLocale";

type RulesPageProps = { searchParams: Promise<{ lang?: string | string[] }> };
type Rule = { title: string; text: string };

const COPY: Record<PublicLocale, { title: string; description: string; eyebrow: string; heroTitle: string; heroCopy: string; section: string; sectionTitle: string; sectionCopy: string; noteTitle: string; note: string; footer: string; rules: Rule[] }> = {
  ru: {
    title: "Правила проживания",
    description: "Правила проживания в отеле Три Короны: выезд, гости, уборка, отмена бронирования и ответственность за имущество.",
    eyebrow: "Три Короны · Правила отеля",
    heroTitle: "Правила проживания",
    heroCopy: "Ключевые условия проживания собраны в одном месте, чтобы до заезда было понятно, как устроены выезд, посещение гостями, уборка и отмена.",
    section: "Правила",
    sectionTitle: "10 важных условий",
    sectionCopy: "Правила перенесены из действующей памятки отеля. Если ситуация требует индивидуального решения, применимость условия подтверждает менеджер.",
    noteTitle: "Важно",
    note: "Эта страница информирует о правилах отеля. Сайт и AI не выполняют автоматические штрафы, удержания или возвраты: финансовое действие подтверждает уполномоченный сотрудник.",
    footer: "Бронирование: +996 558 08 50 02",
    rules: [
      { title: "Курение", text: "Курить в номерах строго запрещено." },
      { title: "Поздний выезд", text: "При выезде после 12:00 за каждый следующий час предусмотрена доплата 1 000 сом." },
      { title: "Досрочный выезд", text: "При выезде раньше забронированной даты удерживаются +1 сутки; за остальные дни предусмотрен возврат денежных средств с удержанием налога 10% с оставшейся суммы." },
      { title: "Животные", text: "Проживание с животными запрещено." },
      { title: "Посетители до 22:00", text: "Пребывание гостей, не проживающих в отеле, разрешено до 22:00." },
      { title: "Дополнительные гости", text: "При заселении в номер свыше количества человек, заявленного при бронировании, размещение оплачивается дополнительно по действующим тарифам." },
      { title: "Посетители после 22:00", text: "Гости, находящиеся в номерах после 22:00, считаются проживающими и оплачиваются дополнительно согласно прайс-листу." },
      { title: "Отмена бронирования", text: "Без удержания — за 5 календарных дней до планируемого прибытия. При отмене за 4 дня удерживается 25% стоимости за сутки, за 3 дня — 50%, за 2 дня — 75%, за 1 день и в день заезда предоплата не возвращается." },
      { title: "Уборка и бельё", text: "Уборка номера производится по заявке гостя. Замена белья — каждые 3 дня. Ежедневная уборка и замена белья оплачиваются дополнительно: 1 500 сом." },
      { title: "Имущество отеля", text: "Утеря и порча имущества отеля оплачиваются согласно действующему прейскуранту." },
    ],
  },
  kg: {
    title: "Жашоо эрежелери",
    description: "Үч Таажы мейманканасында жашоо эрежелери: чыгуу, коноктор, тазалоо, бронду жокко чыгаруу жана мүлк үчүн жоопкерчилик.",
    eyebrow: "Үч Таажы · Мейманкананын эрежелери",
    heroTitle: "Жашоо эрежелери",
    heroCopy: "Негизги жашоо шарттары бир жерде топтолду: чыгуу убактысы, коноктордун келүүсү, тазалоо жана бронду жокко чыгаруу тартиби.",
    section: "Эрежелер",
    sectionTitle: "10 маанилүү шарт",
    sectionCopy: "Эрежелер мейманкананын учурдагы эскертмесинен көчүрүлдү. Жеке жагдайда шарттын колдонулушун менеджер тактайт.",
    noteTitle: "Маанилүү",
    note: "Бул барак маалыматтык мүнөздө. Сайт жана AI айыптарды, кармоолорду же кайтарууларды автоматтык түрдө жүргүзбөйт; каржылык аракетти ыйгарым укуктуу кызматкер ырастайт.",
    footer: "Брондоо: +996 558 08 50 02",
    rules: [
      { title: "Тамеки тартуу", text: "Номерлерде тамеки тартууга катуу тыюу салынат." },
      { title: "Кеч чыгуу", text: "12:00дөн кийин чыкканда ар бир кийинки саат үчүн 1 000 сом кошумча төлөм каралган." },
      { title: "Эрте чыгуу", text: "Брондолгон күндөн эрте чыкканда +1 сутка кармалат; калган күндөр үчүн сумманын калган бөлүгүнөн 10% салык кармалып, акча кайтаруу каралган." },
      { title: "Жаныбарлар", text: "Жаныбарлар менен жашоого тыюу салынат." },
      { title: "22:00гө чейинки коноктор", text: "Мейманканада жашабаган коноктордун келүүсүнө 22:00гө чейин уруксат берилет." },
      { title: "Кошумча коноктор", text: "Брондоодо көрсөтүлгөн адам санынан көп жайгашкан учурда кошумча жайгашуу учурдагы тарифтер боюнча төлөнөт." },
      { title: "22:00дөн кийинки коноктор", text: "22:00дөн кийин номерде калган коноктор жашоочу катары эсептелип, прайс-лист боюнча кошумча төлөнөт." },
      { title: "Бронду жокко чыгаруу", text: "Келүүгө 5 календардык күн калганда кармоосуз. 4 күн калганда бир сутканын баасынын 25%, 3 күндө 50%, 2 күндө 75% кармалат; 1 күн калганда жана келүү күнү алдын ала төлөм кайтарылбайт." },
      { title: "Тазалоо жана шейшеп", text: "Номер коноктун өтүнүчү боюнча тазаланат. Шейшеп ар 3 күндө алмаштырылат. Күн сайын тазалоо жана шейшеп алмаштыруу — кошумча 1 500 сом." },
      { title: "Мейманкананын мүлкү", text: "Мейманкананын мүлкүн жоготуу же бузуу учурдагы прейскурант боюнча төлөнөт." },
    ],
  },
  en: {
    title: "Hotel Rules",
    description: "Three Crowns hotel rules covering checkout, visitors, housekeeping, cancellation and responsibility for hotel property.",
    eyebrow: "Three Crowns · Hotel rules",
    heroTitle: "Hotel rules",
    heroCopy: "The main stay conditions are collected in one place so checkout, visitor access, housekeeping and cancellation terms are clear before arrival.",
    section: "Rules",
    sectionTitle: "10 important conditions",
    sectionCopy: "These rules are transcribed from the hotel’s current guest notice. Where an individual situation needs interpretation, the manager confirms how a rule applies.",
    noteTitle: "Important",
    note: "This page is informational. The website and AI do not automatically issue penalties, deductions or refunds; any financial action must be confirmed by an authorised staff member.",
    footer: "Reservations: +996 558 08 50 02",
    rules: [
      { title: "Smoking", text: "Smoking in guest rooms is strictly prohibited." },
      { title: "Late checkout", text: "For checkout after 12:00, an additional 1,000 KGS applies for each subsequent hour." },
      { title: "Early departure", text: "When departing before the booked date, one additional day is retained; the remaining days are subject to a refund with 10% tax withheld from the remaining amount." },
      { title: "Pets", text: "Staying with animals is prohibited." },
      { title: "Visitors before 22:00", text: "Visitors who are not staying at the hotel are permitted until 22:00." },
      { title: "Additional guests", text: "If more people stay in the room than declared at booking, the additional accommodation is charged according to the current tariffs." },
      { title: "Visitors after 22:00", text: "Visitors remaining in rooms after 22:00 are treated as staying guests and are charged according to the current price list." },
      { title: "Cancellation", text: "No deduction applies when cancelled 5 calendar days before planned arrival. Cancellation 4 days before arrival retains 25% of one day’s price, 3 days — 50%, 2 days — 75%; 1 day before arrival and on arrival day, the prepayment is non-refundable." },
      { title: "Housekeeping and linen", text: "Room cleaning is provided on guest request. Linen is changed every 3 days. Daily cleaning and linen replacement are available for an additional 1,500 KGS." },
      { title: "Hotel property", text: "Loss of or damage to hotel property is charged according to the current price list." },
    ],
  },
};

async function pageLocale(searchParams: RulesPageProps["searchParams"]): Promise<PublicLocale> {
  const params = await searchParams;
  const raw = Array.isArray(params.lang) ? params.lang[0] : params.lang;
  return normalizePublicLocale(raw);
}

export async function generateMetadata({ searchParams }: RulesPageProps): Promise<Metadata> {
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  const url = locale === "ru" ? "/rules" : `/rules?lang=${locale}`;
  return {
    title: copy.title,
    description: copy.description,
    alternates: { canonical: url, languages: { "ru-RU": "/rules", "ky-KG": "/rules?lang=kg", "en-US": "/rules?lang=en" } },
  };
}

export default async function RulesPage({ searchParams }: RulesPageProps) {
  const locale = await pageLocale(searchParams);
  const copy = COPY[locale];
  return <>
    <SiteHeader />
    <main className="rooms-page" id="top">
      <section className="rooms-hero" aria-labelledby="rules-title">
        <div className="rooms-hero-media" aria-hidden="true"><Image src="/media/three-crowns/room-double.webp" alt="" fill priority sizes="100vw" /></div>
        <div className="rooms-hero-shade" aria-hidden="true" />
        <div className="wrap rooms-hero-content">
          <p className="eyebrow light">{copy.eyebrow}</p>
          <h1 id="rules-title">{copy.heroTitle}</h1>
          <p className="rooms-hero-copy">{copy.heroCopy}</p>
        </div>
      </section>

      <section className="catalog-section" aria-labelledby="rules-list-title">
        <div className="wrap catalog-heading">
          <div><p className="eyebrow">{copy.section}</p><h2 className="display-title" id="rules-list-title">{copy.sectionTitle}</h2></div>
          <p>{copy.sectionCopy}</p>
        </div>
        <div className="wrap room-catalog-grid">
          {copy.rules.map((rule, index) => <article className="room-catalog-card" key={rule.title}>
            <div className="room-catalog-card-top"><span className="room-catalog-index">{String(index + 1).padStart(2, "0")}</span></div>
            <h2>{rule.title}</h2>
            <p>{rule.text}</p>
          </article>)}
        </div>
        <div className="wrap catalog-truth"><div><strong>{copy.noteTitle}</strong><p>{copy.note}</p></div></div>
      </section>
    </main>
    <footer className="rooms-footer"><div className="wrap rooms-footer-inner"><strong>{locale === "en" ? "Three Crowns · Resort & SPA" : locale === "kg" ? "Үч Таажы · Resort & SPA" : "Три Короны · Resort & SPA"}</strong><a href="tel:+996558085002">{copy.footer}</a></div></footer>
  </>;
}
