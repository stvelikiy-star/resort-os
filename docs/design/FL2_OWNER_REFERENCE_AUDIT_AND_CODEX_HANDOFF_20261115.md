# MARINA SMART — Future Luxury 2.0: аудит, эталон OWNER Dashboard и задания Codex

Ветка: `design/marina-fl2-owner-reference-20261115`, база — вершина PR #468 (`f6868b4`). Без merge/deploy. Backend, БД, WhatsApp/AI, рабочие окружения не затронуты.

## 0. Граница проверенного (читать первым)

| Что | Статус |
|---|---|
| Web Admin OWNER Dashboard, Dark/Light, 1440 / 768 / 390 px, реальный рендер Chromium на **синтетическом мок-Core** | ПРОВЕРЕНО (скриншоты в `docs/design/evidence/fl2-owner-reference/`) |
| Остальные разделы Web Admin | НЕ рендерились; оценка только по коду и манифесту |
| Staff (`apps/staff`) | НЕ рендерился; смотрел только список файлов #468 |
| Mobile | Код и тесты; визуально и на устройстве/эмуляторе НЕ проверено (см. #471) |
| Физический Android, TalkBack, реальный экран | НЕ проверено |
| Предложения Gemini и «генеральный план» | **Не поступили** в приложениях к задаче — не учтены |
| Реальные данные отеля | Не использовались. Все числа на скриншотах синтетические (`QA Resort (synthetic)`) |

Технические проверки (tsc, build, guard-скрипты) не равны визуальной готовности.

## 1. Строгий аудит

### 1.1 Эталон OWNER Dashboard до изменений (Web, вершина #468)
| # | Дефект | Серьёзность |
|---|---|---|
| A1 | Hero занимает ~⅓ первого экрана без информации; на телефоне — почти весь | Высокая |
| A2 | 7 KPI в сетке 4+3 с пустой «сиротой»; все плитки одного веса — загрузка не выделена | Высокая |
| A3 | У KPI нет иконок; нет иерархии «состояние → требует решения → детали» | Средняя |
| A4 | Блок «WhatsApp / AI» — пустая панель только с кнопкой | Средняя |
| A5 | Нет графика на первом экране; график 30 дней (реальные on-books) ниже сгиба и в тёмном блоке | Высокая |
| A6 | Нет быстрых переходов; пути к разделам только через верхнюю навигацию | Средняя |
| A7 | Light: старые блоки Executive Pack / Control V2 / Operations остаются тёмными — тема не едина | Высокая |
| A8 | Skeleton отсутствует: текст «Загрузка…» заменяет всю страницу | Средняя |

### 1.2 Сопоставление с образцами (PNG Web + Mobile, ZIP 70 SVG)
| Элемент образца | Решение | Причина |
|---|---|---|
| Hero с фото курорта | НЕ сделано | Нет утверждённых локальных фото; не выдумывать |
| Линия «Доходы» по дням, «Выручка по направлениям» | НЕ сделано | Нет таких рядов в API; цифры образца — иллюстрация |
| Шахматка на Dashboard | НЕ сделано | Отдельный раздел PMS (задача C3) |
| Сайдбар из 6 групп | НЕ сделано | Владелец AdminShell → C1 |
| Поиск ⌘K, hover-превью брони, FAB/Bottom Sheet, «Новая бронь/Добавить гостя/Отправить уведомление» | НЕ сделано | Новые функции, не эталон (§3) |
| KPI-карточки с иконкой Lucide, glass, кольцо загрузки, график, список задач | СДЕЛАНО | На существующих данных |

ZIP: 74 файла = 70 SVG (52 Web = 26 разделов × Dark/Light; 18 Mobile = 9 кабинетов × Dark/Light) + README, манифест, GALLERY.html и утверждённый логотип PNG. В манифесте KPI-значения заменены прочерками — используется как макет композиции, не как источник данных.

### 1.3 Логотип
Единственный источник — утверждённый круглый PNG. SHA-256 вложения = `apps/admin/public/marina-smart-approved.png` = `24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356`. Не менять и не перерисовывать (образцы PNG содержат другой, нарисованный знак — **не использовать**).

### 1.4 Конфликт PR #471 ↔ #468 (риск перезаписи)
#471 (Mobile motion, `design/marina-fl2-mobile-premium-20261111`) создан до #468. #468 переписал `FadeIn`, `AnimatedProgressBar`, `PressScale` в `apps/mobile/src/components/ui.tsx` — тот же файл. Мерж #471 как есть затрёт или конфликтует. **Требуется rebase #471 на `f6868b4` (задача C9a), не наоборот.**

## 2. Что реализовано (общая основа + эталон)

Файлы (добавлены/изменены — только Web Admin):
- `apps/admin/app/fl2-foundation.css` (новый): токены `--mx-*` Dark/Light, компоненты `.mx-*`, motion (transform/opacity, 120–700 мс, выкл. при Reduced Motion). Opt-in: всё под `html[data-marina-ui="future-luxury"]`, Legacy не затронут. Контраст всех текстовых пар ≥ 4.5:1 (расчёт в репозитории: Dark 8.1–15.1, Light 5.1–16.2).
- `apps/admin/components/fl2/Fl2.tsx` (новый): `Card, Kpi, Badge, Meter, Ring, StackedBar, AreaChart, Skeleton, ErrorBox, useReady`.
- `apps/admin/components/fl2/OwnerCommandCenter.tsx` (новый): композиция эталона.
- `DashboardBoard.tsx`: проп `fl2`; для OWNER + Future Luxury рендерит эталон, остальные роли и Legacy — прежняя вёрстка. Экспортированы типы.
- `AdminShell.tsx`: передаёт `fl2={uiPreference === "future-luxury"}`. `layout.tsx`: подключение CSS последним.
- `package.json` / lock: `lucide-react@0.511.0` (точная версия; единственная новая зависимость, из задания «Lucide»).
- `scripts/design/fl2-owner-mock-core.mjs`, `fl2-owner-capture.mjs`: QA-харнесс (мок Core + Playwright). Только для снимков, в продукт не импортируется.

Все существующие действия сохранены: «Обновить», переходы в PMS / Ресепшен / Заявки / Финансы / Задачи / Входящие / WhatsApp-AI, три блока Owner (Executive Pack, Control V2, Operations) ниже без изменений.

Данные: только `/admin/dashboard` и `/admin/intelligence/owner-brief` (on-books по датам; подпись «не прогноз спроса»). Пустое/ошибка/загрузка — честные состояния, повтор запроса для графика. AI-состояний не добавлено, PIN TTHotel не добавлен.

Состояния: skeleton (загрузка), ErrorBox + «Повторить» (ошибка Core), empty (нет задач/заездов/точек графика).

Доступность: график `role=img` + управление стрелками (readout), кольцо/индикатор `progressbar` с точным значением, цели ≥ 44 px в новом блоке, фокус `outline` 3 px, Reduced Motion.

### Новые UX-функции (отдельно от переработки, требуют решения владельца продукта)
1. Панель «Быстрые переходы» (только навигация к существующим вкладкам).
2. 30-дневный график on-books с readout по наведению/клавиатуре (данные уже были в Control V2, визуализация новая).
3. Skeleton-загрузка.

## 3. Проверки

| Проверка | Результат |
|---|---|
| `tsc --noEmit` (admin) | OK |
| `next build` (admin) | OK |
| 10 guard-скриптов `design:fl2:*` + owner-pms-skin, operations, reception, guest-touchpoints, operations-workspaces | PASS (10/10) |
| Горизонтальный overflow 1440/768/390 × Dark/Light | 0 px (6/6) |
| Ошибки консоли страницы | 0 (6/6) |
| Поведение (Chromium, prod-сборка) | 10/10: ring и meter сходятся к 72% (значение сервера), клик «Шахматка» уводит с Dashboard, Reduced Motion отключает анимации и transitions, Legacy сохраняет старую вёрстку и WhatsApp/AI, стрелки двигают readout графика, цели ≥ 44 px в новом блоке |
| Контраст токенов | 18/18 пар ≥ 4.5:1 |

Не проверено: реальные данные, Safari/Firefox, TalkBack/VoiceOver, медленная сеть, 200% zoom.

## 4. Известные дефекты (не исправлены, переданы Codex)
- D1 Light: старые Owner-блоки остаются тёмными (A7).
- D2 В старых Owner-блоках 5 кнопок ниже 44 px.
- D3 Плавающий «Помощник» перекрывает контент справа внизу (desktop и phone); на телефоне также переключатель языка слева внизу (виден только в этой dev-проверке — проверить в prod).
- D4 Hero eyebrow показывает имя отеля капсом — длинное имя переносится на 2 строки на телефоне.
- D5 `Command Center` не локализован (RU/KG/EN в Web не централизованы).

## 5. Задания Codex

Правило владения: каждый файл имеет одного владельца. `fl2-foundation.css` и `components/fl2/Fl2.tsx` — **только владелец основы** (этот PR); Codex меняет их лишь отдельным мини-PR с пометкой `foundation`. Порядок подключения CSS в `layout.tsx` — только C1. Все задания делаются **после** мержа этого PR; параллельно допустимы задания с непересекающимися файлами.

### C1. Web-оболочка и навигация (6 групп)
- Файлы: `AdminShell.tsx`, `admin-nav-polish.css`, `fl2-premium-visual.css`, новый `fl2-shell.css`, `layout.tsx`.
- Зависимости: этот PR.
- Результат: группы Операции / Гости / Деньги / Команда / Рост / Настройки без потери 26 вкладок, RBAC и прав модулей; закрепление активного раздела; исправить D3 (смещение «Помощника» и безопасная область).
- Проверки: `design:fl2:audit` (26 вкладок), tsc, build, снимки по `fl2-owner-capture.mjs` для всех ролей, клавиатурная навигация.

### C2. Тема Light для старых Owner-блоков
- Файлы: `OwnerExecutivePack.tsx`, `OwnerControlV2.tsx`, `OwnerOperationsPerformance.tsx` и их CSS (`owner-*.css`, `fl2-owner-*.css`).
- Зависимости: этот PR; не пересекается с C1.
- Результат: единый Dark/Light на `--mx-*` и `.mx-*`; цели ≥ 44 px (D2); данные и правдивые подписи не менять.
- Проверки: guard `design:fl2:owner`, контраст ≥ 4.5, снимки Dark/Light/phone.

### C3. PMS: шахматка и карточка брони
- Файлы: `PMSChessboard*`, `PmsBookingModal*`, их CSS.
- Результат: основа и состояния (loading/empty/error); сохранить HOLD, оплаты, назначение номера. Hover-превью брони — отдельный PR как новая функция.
- Проверки: `design:fl2:owner-pms-skin`, e2e действий брони.

### C4. Reception / Requests / Groups / Rates
- Файлы: `Reception*`, `Requests*`, `Groups*`, `Rates*`, их CSS. Не пересекается с C3/C5.
- Проверки: `design:fl2:reception`, все действия сохранены.

### C5. Guests / Services / Marketing / Growth
- Файлы: `Guests*`, `Services*`, `Offers*`, `Marketing*`, `Growth*`.
- Проверки: `design:fl2:guest-touchpoints`.

### C6. Finance / Reports
- Файлы: `Finance*`, `Reports*`, их CSS.
- Правила: график только на подтверждённых рядах; денежные цифры не пересчитывать.
- Проверки: `design:fl2:operations`, сверка сумм с API.

### C7. Content / Inbox / WhatsApp-AI / Settings
- Файлы: `Content*`, `Inbox*`, `WhatsApp*`, `Settings*`.
- Правила: AI показывает только достоверное состояние (подключено / нет данных / ошибка); интеграции не менять; PIN TTHotel не добавлять.

### C8. Staff
- Файлы: `apps/staff/**`.
- Результат: основа в рабочих кабинетах; состояния; Reduced Motion.
- Проверки: tests Staff, снимки (в этой сессии Staff не рендерился).

### C9a. Mobile: перенос #471 на вершину #468 (первым в Mobile)
- Файлы: ветка #471; `apps/mobile/src/components/ui.tsx`, `Future.tsx`, `theme/motion.ts`.
- Результат: rebase на `f6868b4`, при конфликте в `ui.tsx` сохранить логику #468 (PressScale и пр.) и добавить синхронный Motion-снимок #471; 53 набора jest проходят.
- Проверки: tsc, eslint, jest, `expo export --platform android`.

### C9b. Mobile: кабинеты и Motion
- Файлы: `apps/mobile/app/**`, `src/components/**` (кроме C9a).
- Зависимость: C9a.
- Результат: основа во всех ролях (OWNER…AGENT), единый TabIcon/BottomSheet; завершение Motion; проверка на устройстве/эмуляторе Android (не выдавать unit-тесты за визуальную проверку).

### C10. Поиск ⌘K (новая функция)
- Файлы: новые `components/fl2/CommandPalette.tsx`, подключение в `AdminShell.tsx` (после C1).
- Результат: поиск только по существующим API (гость/бронь/номер/задача); без выдуманных результатов.

### C11. QA-харнесс и состояния
- Файлы: `scripts/design/**`.
- Результат: расширить `fl2-owner-capture.mjs` на все разделы/роли, состояния loading/empty/error, 200% zoom, Reduced Motion; CI-шаг со снимками как артефактом.

Матрица владения: C1 {AdminShell, shell/nav CSS, layout.tsx} · C2 {Owner*} · C3 {PMS*} · C4 {Reception/Requests/Groups/Rates} · C5 {Guests…Growth} · C6 {Finance/Reports} · C7 {Content/Inbox/WhatsApp/Settings} · C8 {apps/staff} · C9 {apps/mobile} · C10 {CommandPalette} · C11 {scripts/design}. Пересечений нет; общий код основы — только через отдельный `foundation` PR.

## 6. Воспроизвести снимки
```
node scripts/design/fl2-owner-mock-core.mjs &          # синтетический Core :8000
CORE_API_URL=http://127.0.0.1:8000 npx next dev -p 3001 # из apps/admin
node scripts/design/fl2-owner-capture.mjs out after     # Playwright, Dark/Light × 3 ширины
```
