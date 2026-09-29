export type SiteLocale = "ru" | "kg" | "kz" | "en";

export type SiteContent = {
  hero?: Record<string, string>;
  booking?: Record<string, string>;
  advantages?: Record<string, string>;
  conference?: Record<string, string>;
  rooms?: Record<string, string>;
  territory?: Record<string, string>;
  amenities?: Record<string, string>;
  groups?: Record<string, string>;
  contacts?: Record<string, string>;
  final?: Record<string, string>;
  seo?: Record<string, string>;
};

type SiteContentResponse = {
  locale: SiteLocale;
  content: SiteContent;
  published_version: number;
  source: "DATABASE" | "DEFAULT";
};

export const fallbackSiteContent: Record<SiteLocale, SiteContent> = {
  ru: {
    hero: {
      eyebrow: "Три Короны · Resort & SPA · Чолпон-Ата",
      title: "Иссык-Куль. Ваш отдых начинается здесь.",
      copy: "Курорт у самой воды: собственный пляж, 150-метровый пирс, SPA, открытый бассейн и 12 категорий размещения.",
      primary_cta: "Проверить свободные номера",
      secondary_cta: "Смотреть номерной фонд",
    },
    booking: { eyebrow: "Бронирование без лишних шагов", title: "Сначала даты. Потом — лучший вариант.", intro: "Укажите даты и состав гостей. Система покажет свободные категории и стоимость за весь период." },
    advantages: { eyebrow: "Почему Три Короны", title: "От номера до воды — один маршрут", intro: "Номер, зелёная территория, бассейн, SPA, собственный пляж и пирс складываются в один понятный сценарий отдыха." },
    conference: {
      eyebrow: "Конференции и банкеты",
      title: "Конференц-зал для мероприятий от 20 до 120 гостей",
      copy: "Отдельное пространство для конференций, деловых встреч, презентаций и групповых мероприятий. Конференц-зал также может быть подготовлен под банкет.",
      capacity: "20–120 гостей",
      banquet: "Банкетная рассадка доступна в конференц-зале",
      menu: "Банкетное меню и формат обслуживания согласовываются индивидуально",
      cta: "Обсудить мероприятие",
    },
    groups: { eyebrow: "Групповые заезды", title: "Команды, сборы и корпоративные поездки", copy: "Подберём размещение под состав группы и заранее согласуем питание, трансфер и режим проживания." },
    contacts: { phone: "+996 558 08 50 02", whatsapp: "+996 558 08 50 02", email: "3koronykg@mail.ru", address: "Иманбай Молдо, Чолпон-Ата 722315, Кыргызстан" },
    seo: { title: "Три Короны — Resort & SPA на Иссык-Куле", description: "Три Короны Resort & SPA в Чолпон-Ате: 84 номера, конференц-зал на 20–120 гостей, собственный пляж, пирс 150 м, SPA и открытый бассейн." },
  },
  kg: {
    hero: { eyebrow: "Үч Таажы · Resort & SPA · Чолпон-Ата", title: "Ысык-Көл. Эс алууңуз ушул жерден башталат.", copy: "Көл жээгиндеги эс алуу жайы: өз пляжы, 150 метрлик пирс, SPA, ачык бассейн жана жайгашуунун 12 категориясы.", primary_cta: "Бош номерлерди текшерүү", secondary_cta: "Номерлерди көрүү" },
    booking: { eyebrow: "Жөнөкөй брондоо", title: "Адегенде даталар. Андан кийин — ылайыктуу вариант.", intro: "Келүү-кетүү даталарын жана коноктордун санын көрсөтүңүз. Система бош категорияларды жана мезгилдин баасын көрсөтөт." },
    advantages: { eyebrow: "Эмне үчүн Үч Таажы", title: "Номерден көлгө чейин — бир маршрут", intro: "Номер, жашыл аймак, бассейн, SPA, өз пляжы жана пирс эс алуунун бирдиктүү сценарийин түзөт." },
    conference: {
      eyebrow: "Конференциялар жана банкеттер",
      title: "20дан 120га чейин конок үчүн конференц-зал",
      copy: "Конференциялар, иш жолугушуулар, презентациялар жана топтук иш-чаралар үчүн өзүнчө мейкиндик. Конференц-зал банкет өткөрүүгө да даярдалат.",
      capacity: "20–120 конок",
      banquet: "Конференц-залда банкеттик отургузуу мүмкүн",
      menu: "Банкеттик меню жана тейлөө форматы өзүнчө макулдашылат",
      cta: "Иш-чараны талкуулоо",
    },
    groups: { eyebrow: "Топтук келүүлөр", title: "Командалар, спорттук жыйындар жана корпоративдик сапарлар", copy: "Топтун курамына жараша жайгашууну тандап, тамактануу, трансфер жана жашоо режимин алдын ала макулдашабыз." },
    contacts: { phone: "+996 558 08 50 02", whatsapp: "+996 558 08 50 02", email: "3koronykg@mail.ru", address: "Иманбай Молдо, Чолпон-Ата 722315, Кыргызстан" },
    seo: { title: "Үч Таажы — Ысык-Көлдөгү Resort & SPA", description: "Чолпон-Атадагы Үч Таажы Resort & SPA: 84 номер, 20–120 конокко конференц-зал, өз пляжы, 150 м пирс, SPA жана ачык бассейн." },
  },
  kz: {
    hero: { eyebrow: "Үш Тәж · Resort & SPA · Шолпан-Ата", title: "Ыстықкөл. Демалысыңыз осы жерден басталады.", copy: "Көл жағасындағы курорт: жеке жағажай, 150 метрлік пирс, SPA, ашық бассейн және орналастырудың 12 санаты.", primary_cta: "Бос бөлмелерді тексеру", secondary_cta: "Бөлмелерді көру" },
    booking: { eyebrow: "Қарапайым брондау", title: "Алдымен күндер. Содан кейін — лайықты нұсқа.", intro: "Келу-кету күндерін және қонақтар санын көрсетіңіз. Жүйе бос санаттарды және кезең құнын көрсетеді." },
    advantages: { eyebrow: "Неліктен Үш Тәж", title: "Бөлмеден көлге дейін — бір бағыт", intro: "Бөлме, жасыл аумақ, бассейн, SPA, жеке жағажай және пирс біртұтас демалыс сценарийін құрайды." },
    conference: {
      eyebrow: "Конференциялар мен банкеттер",
      title: "20-дан 120 қонаққа дейінгі іс-шараларға арналған конференц-зал",
      copy: "Конференциялар, іскерлік кездесулер, презентациялар және топтық іс-шараларға арналған жеке кеңістік. Конференц-залды банкетке де дайындауға болады.",
      capacity: "20–120 қонақ",
      banquet: "Конференц-залда банкет форматы қолжетімді",
      menu: "Банкет мәзірі мен қызмет көрсету форматы жеке келісіледі",
      cta: "Іс-шараны талқылау",
    },
    groups: { eyebrow: "Топтық келулер", title: "Командалар, жиындар және корпоративтік сапарлар", copy: "Топ құрамына сай орналастыруды таңдап, тамақтану, трансфер және тұру режимін алдын ала келісеміз." },
    contacts: { phone: "+996 558 08 50 02", whatsapp: "+996 558 08 50 02", email: "3koronykg@mail.ru", address: "Иманбай Молдо, Шолпан-Ата 722315, Қырғызстан" },
    seo: { title: "Үш Тәж — Ыстықкөлдегі Resort & SPA", description: "Шолпан-Атадағы Үш Тәж Resort & SPA: 84 бөлме, 20–120 қонаққа арналған конференц-зал, жеке жағажай, 150 м пирс, SPA және ашық бассейн." },
  },
  en: {
    hero: { eyebrow: "Three Crowns · Resort & SPA · Cholpon-Ata", title: "Issyk-Kul. Your stay starts here.", copy: "A lakeside resort with a private beach, a 150-metre pier, SPA, outdoor pool and 12 accommodation categories.", primary_cta: "Check available rooms", secondary_cta: "Explore rooms" },
    booking: { eyebrow: "Straightforward booking", title: "Choose your dates. Then choose your best option.", intro: "Enter your dates and party size. The system will show available categories and the total stay price." },
    advantages: { eyebrow: "Why Three Crowns", title: "From your room to the lake — one easy route", intro: "Rooms, landscaped grounds, pool, SPA, private beach and pier form one seamless resort experience." },
    conference: {
      eyebrow: "Conferences & banquets",
      title: "Conference hall for events from 20 to 120 guests",
      copy: "A dedicated venue for conferences, business meetings, presentations and group events. The conference hall can also be arranged for a banquet.",
      capacity: "20–120 guests",
      banquet: "Banquet seating is available in the conference hall",
      menu: "Banquet menu and service format are agreed individually",
      cta: "Discuss your event",
    },
    groups: { eyebrow: "Group stays", title: "Teams, training camps and corporate trips", copy: "We help match accommodation to your group and coordinate meals, transfers and the stay schedule in advance." },
    contacts: { phone: "+996 558 08 50 02", whatsapp: "+996 558 08 50 02", email: "3koronykg@mail.ru", address: "Imanbay Moldo, Cholpon-Ata 722315, Kyrgyzstan" },
    seo: { title: "Three Crowns — Resort & SPA on Issyk-Kul", description: "Three Crowns Resort & SPA in Cholpon-Ata: 84 rooms, a conference hall for 20–120 guests, private beach, 150 m pier, SPA and outdoor pool." },
  },
};

export async function getPublishedSiteContent(locale: SiteLocale = "ru"): Promise<SiteContentResponse> {
  const fallback: SiteContentResponse = { locale, content: fallbackSiteContent[locale], published_version: 0, source: "DEFAULT" };
  const baseUrl = (process.env.CORE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  try {
    const response = await fetch(`${baseUrl}/api/v1/site/content?locale=${locale}`, { next: { revalidate: 60 } });
    if (!response.ok) return fallback;
    const payload = (await response.json()) as SiteContentResponse;
    return payload?.content ? payload : fallback;
  } catch {
    return fallback;
  }
}
