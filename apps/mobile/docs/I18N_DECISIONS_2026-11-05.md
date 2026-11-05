# MARINA SMART MOBILE — localization decisions (5 November 2026)

Scope: `apps/mobile`. The unified UI strings are in `src/i18n`; strings below are display-only and cannot change backend values, server roles, or identifiers.

## 8 dictionary decisions (`ru.ts`, `kg.ts`, `kz.ts`)

| Key | Decision | Rationale |
| --- | --- | --- |
| `nav.profile` | **Translate KG** from “Профиль” to “Жеке кабинет”; KZ retains “Профиль” intentionally | Natural Kyrgyz user-facing navigation; Kazakh product-wide convention preserved |
| `login.username` | **Translate KG/KZ** from “Логин” to “Колдонуучунун аты” / “Пайдаланушы аты” | Natural user label, credentials/API key unchanged |
| `roles.AGENT` | **Keep** “Агент” RU/KG/KZ | Established travel-industry role, no change to `AGENT` enum |
| `roles.TECHNICIAN` | **Keep** “Техник” RU/KG/KZ | Common occupational term |
| `mt.cats.PLUMBING` | **Keep** “Сантехника” RU/KG/KZ | Recognized maintenance category, backend code unchanged |
| `mt.cats.HVAC` | **Keep** “Кондиционер” RU/KG/KZ | Same common equipment term |
| `profile.version` | **Keep** RU/KG “Версия”, KZ “Нұсқа” | Established terminology for app build version |
| `profile.system` | **Keep** RU “Системная”, KG “Системалык”, KZ “Жүйелік” | Already localized; same setting meaning |

## 5 mobileCopy decisions

| Key | Decision |
| --- | --- |
| `admin` | **Translate KG/KZ** “Команда” → “Кызматкерлер” / “Қызметкерлер” |
| `profile` | **Keep** “Профиль” in compact mobile tab across RU/KG/KZ for consistent short UI; distinct `nav.profile` KG is explicitly “Жеке кабинет” |
| `phone` | **Keep** “Телефон” in RU/KG/KZ; standard telephone-field label |
| `demoLabel` | **Keep** “ДЕМО” across RU/KG/KZ as a product-mode marker, never a LIVE badge |
| `staffOverview` | **Translate KG/KZ** “Команда” → “Кызматкерлер” / “Қызметкерлер” |

`LIVE PMS` is preserved verbatim in all four languages as a product technical-state label; it is now a shared i18n key. Original AI and weekday translations are moved into `mobileCopy.ts` **without wording changes**.

The automated parity test guarantees equal keys and non-empty values but **is not a human linguistic certification**. Native Android layout QA remains NOT TESTED until a physical-device run.
