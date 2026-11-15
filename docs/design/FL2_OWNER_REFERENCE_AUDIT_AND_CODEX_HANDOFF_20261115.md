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
| Исходный генплан Future Luxury 2.0 и текст предложений Gemini | **Нет среди доступных материалов** (репозиторий, вложения). Не восстанавливались по догадкам; используется только порядок этапов, названный владельцем продукта (§5.0), и перечень требований Gemini из его сообщения (§5.1) |
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

### Новые элементы эталона (уже входят в согласованный дизайн)
Повторного утверждения не требуют: панель «Быстрые переходы» (навигация только к существующим вкладкам), существующий 30-дневный график on-books (данные уже были в Control V2) и skeleton-загрузка. Не вошло и **не реализовано**: см. §5.1 (требования Gemini).

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

Правило владения: у каждого файла один владелец. `fl2-foundation.css` и `components/fl2/Fl2.tsx` — только владелец основы; Codex меняет их лишь отдельным мини-PR `foundation`. Порядок CSS в `layout.tsx` — только C1. Все задания — после merge #472. **Пересечения выполняются строго последовательно**, непересекающиеся — допустимо параллельно.

Неизменные ограничения для всех заданий: логотип — только утверждённый круглый PNG (`apps/admin/public/marina-smart-approved.png`, SHA-256 `24678424…f15356`), не перерисовывать; все существующие функции и RBAC (`canAccess`, `moduleEnabled`, роли) сохраняются; Backend/БД/интеграции WhatsApp/AI не менять; **генерацию PIN не добавлять**; на экранах только данные существующих API.

### 5.0 Сопоставление с генпланом Future Luxury 2.0
Исходный генплан недоступен; ниже — этапы в порядке, названном владельцем.

| Этап генплана | Задания | Статус |
|---|---|---|
| 1. Единые токены/компоненты Dark/Light | основа (#472, готово); C1; C2 | основа готова, C1–C2 не начаты |
| 2. Эталоны OWNER / PMS / Mobile | OWNER — #472 (готово); C3 (PMS); C9a (Mobile: #471 + #468) | OWNER готов, остальное не начато |
| 3. Остальные Web / Staff / Guest | C4, C5, C6, C7, C8; **C12 Guest (`apps/web`) — пробел, добавлен** | не начато |
| 4. Mobile всех ролей | C9b | не начато, после C9a |
| 5. Motion | Web — в основе; Mobile — C9a (#471) и C9b | Mobile Motion в #471 (не перенесён) |
| 6. Визуальная и функциональная приёмка | C11, затем ручная проверка владельцем на устройствах | не начато |
| вне этапов | C10 (⌘K) — после C1 и решения владельца | не начато |

### 5.1 Требования Gemini (пропущенные ранее)
Статус всех строк: **НЕ РЕАЛИЗОВАНО** (в этом PR не делается). Данные — только из существующих API; выдуманных значений нет.

| Требование | Задание | Зависимости | Критерий готовности |
|---|---|---|---|
| Превью брони (hover на desktop, касание/Bottom Sheet на телефоне) | C3 (Web), C9b (Mobile) | C3 после C1; Mobile после C9a; поля — из ответа шахматки/брони | Гость, даты, номер, статус, оплата — без новых запросов, где данные уже есть; не открывает действия сверх прав роли; клавиатура и Esc |
| Поиск ⌘K | C10 | C1 (AdminShell); существующие эндпоинты поиска гостя/брони/номера — наличие проверить до старта | Результаты только из API и только разрешённые RBAC; «ничего не найдено» честно; фокус-ловушка, Esc |
| Реальные статусы AI | C7 (Web), C9b (Mobile) | Существующий статус-ответ Core/WhatsApp; если его нет — показывать только «нет данных», backend не менять | Только «подключено / нет данных / ошибка / отключено» из ответа; без «онлайн»-декора |
| Контраст графиков | foundation-мини-PR (`Fl2.tsx` AreaChart, `fl2-foundation.css`), затем C6 | Предшествует C6 | Линии/области ≥ 3:1 к фону, подписи ≥ 4.5:1, не только цветом; Dark и Light |
| Ролевая навигация | C1 (Web), C9b (Mobile) | RBAC неизменен; C1 до C2–C7 | 6 групп без потери 26 вкладок; каждая роль видит только свои разделы, как сейчас |
| FAB / Bottom Sheet | C9b (Mobile), C1 (Web на телефоне) | C9a; действия только существующие | Действия FAB = существующие маршруты/права; цели ≥ 44 px; Reduced Motion |

### 5.2 Реальные пути и порядок выполнения C1–C11
Порядок (сверху вниз; пересечения — последовательно):

1. **C1** Web-оболочка. Файлы: `apps/admin/components/AdminShell.tsx` (MODULE_TABS ~стр. 55, навигация ~стр. 328–364), `apps/admin/app/admin-nav-polish.css`, `fl2-premium-visual.css`, новый `fl2-shell.css`, `apps/admin/app/layout.tsx`.
2. **C2** Light для Owner-блоков. `OwnerExecutivePack.tsx`, `OwnerControlV2.tsx`, `OwnerOperationsPerformance.tsx`, `OwnerOccupancyMatrix.tsx`; CSS `owner-executive.css`, `owner-control-v2.css`, `owner-intelligence.css`, `owner-corrections.css`, `fl2-owner-composition.css`, `fl2-owner-dashboard.css`. Общий `fl2-owner-pms-finish.css` с C3 → C2 раньше C3.
3. **C3** PMS. `PMSGrid.tsx`, `PMSGridV2.tsx`, `PMSGridV9.tsx`, `PMSOwnerGrid.tsx`, `PMSUniversalBoard.tsx`, `PMSOperationsCockpitV9.tsx`, `PMSControlSnapshotV9.tsx`, `PMSBulkGuardV9.tsx`, `PMSIntegrationRailV10.tsx`, `PMSNewReservationModal.tsx`, `ChessboardReservationModal.tsx`, `ReservationFolioPanel.tsx`, `RoomDetailModal.tsx`, `RoomBlocksPanel.tsx`; CSS `chessboard*.css`, `fl2-pms-composition.css`, `fl2-owner-pms-finish.css`, `room-detail.css`, `pms-owner-workflow-corrections.css`. Сохранить HOLD, оплаты, назначение номера.
4. **C4** Reception / Requests / Groups / Rates. `ReceptionWorkspace.tsx`, `ReceptionBoard.tsx`, `ReservationsBoard.tsx`, `RequestsBoard.tsx`, `GroupBookingBoard.tsx`, `RateManagementBoard.tsx`, `ChannelManagerBoard.tsx`, `AgentsBoard.tsx`; CSS `reception*.css`, `fl2-reception-visual.css`, `fl2-bookings-reception-composition.css` (общий с C3 → после C3).
5. **C5** Guests / Services / Marketing / Growth. `GuestHistoryBoard.tsx`, `GuestCrmEnrichmentPanel.tsx`, `GuestServicesCenter.tsx`, `GuestServiceSettingsBoard.tsx`, `GuestOffersBoard.tsx`, `MarketingBoard.tsx`, `GrowthControlBoard.tsx`; CSS `guest-*.css`, `marketing.css`, `growth-control.css`, `fl2-guest-touchpoints.css`, `fl2-guest-finance.css` (общий с C6 → C5 раньше C6).
6. **C6** Finance / Reports. `HotelFinanceBoard.tsx`, `NfcFinanceBoard.tsx`, `ReportsBoard.tsx`; CSS `finance.css`, `hotel-finance.css`, `nfc.css`, `reports.css`, `fl2-finance-owner-composition.css`. Предшествует foundation-мини-PR по контрасту графиков.
7. **C7** Content / Inbox / WhatsApp-AI / Settings / Dining / QR. `SiteContentBoard.tsx`, `SiteMediaBoard.tsx`, `InboxBoard.tsx`, `WhatsAppWorkspace.tsx`, `WhatsAppConnection.tsx`, `MarinaAiAssistant.tsx`, `HotelRulesBoard.tsx`, `HotelSetupBoard.tsx`, `DiningManagementBoard.tsx`, `RoomQrBoard.tsx`, `ServicePointsBoard.tsx`, `OperationsBoard.tsx`, `StaffBoard.tsx`; CSS `inbox.css`, `hotel-setup.css`, `room-qr.css`, `service-points.css`, `fl2-operations-knowledge-growth.css`, `fl2-operational-web.css`.
8. **C8** Staff. `apps/staff/app/{globals.css,shift-v2.css,page.tsx}`, `apps/staff/app/waiter/page.tsx`, `apps/staff/app/kitchen/**`, `apps/staff/components/*` (Waiter*, Kitchen*, Chef*, Dining*, StaffShiftV2, BeachTerminal, MarinaAiAssistant).
9. **C12** Guest (`apps/web`). `apps/web/app/{guest,g/[token],p/[token]}`, `guest-*.css`, `home-v2.css`, `luxury-director.css`, `mobile-hardening.css`. Пробел в исходном списке C1–C11; номер C12, чтобы не менять существующие.
10. **C9a** Mobile: совместить #471 с #468 **без потери исправлений** (отдельное задание). Ветка #471 `design/marina-fl2-mobile-premium-20261111`, rebase на `f6868b4`. Конфликт: `apps/mobile/src/components/ui.tsx` (`FadeIn`, `AnimatedProgressBar`, `PressScale` — сохранить логику #468 и добавить Motion-снимок #471). Затронуты также `Future.tsx`, `src/theme/{motion,tokens}.ts`, `components/Motion.tsx`, `__tests__/motion-system.test.tsx`. Критерии: tsc, eslint, jest (53 набора), `expo export --platform android`; diff функций #468 не потерян. Может выполняться параллельно с C1–C8 (только `apps/mobile`), но строго до C9b.
11. **C9b** Mobile всех ролей и Motion. `apps/mobile/app/(app)/*` (overview, pms, reception, requests, rooms, tasks, dining, kitchen, inbox, admin, more, profile), `apps/mobile/app/{ai,finance,holds,meal-plans,new-booking,new-request,scan}.tsx`, `src/components/{OwnerControlDashboard,PmsBookingSheet,RoleProfileWorkspaces,WaiterOperations,KitchenProductionPlanner,...}.tsx`. После C9a. Не выдавать unit-тесты за проверку на устройстве.
12. **C10** ⌘K: новый `apps/admin/components/fl2/CommandPalette.tsx` + подключение в `AdminShell.tsx` — после C1 и после решения владельца по поиску.
13. **C11** QA-харнесс: `scripts/design/**` — расширить `fl2-owner-capture.mjs` на все разделы/роли, loading/empty/error, 200% zoom, Reduced Motion; шаг CI со снимками. После C1–C9b; вместе с ручной приёмкой владельцем.

Совпадение файлов проверяется по именам; перед стартом каждого задания выполнить `grep` по импортам CSS в `layout.tsx` и компонентах, чтобы убедиться в отсутствии пересечений с активным заданием.

### 5.3 Первое задание Codex — C1
- Файлы: см. п.1 выше.
- Сделать: 6 групп навигации (Операции / Гости / Деньги / Команда / Рост / Настройки) поверх существующих 26 вкладок и `canAccess/moduleEnabled`; активный раздел закреплён; исправить D3 (смещение «Помощника», безопасная область); ролевая навигация без изменения RBAC.
- Приёмка: все вкладки доступны тем же ролям, что и до изменений (сверка таблицей роль × вкладка); `npm run design:fl2:audit` (26 вкладок), tsc, `next build`; `npm test` в корне (Control Center contract) — зелёный; снимки `fl2-owner-capture.mjs` Dark/Light × 1440/768/390: overflow 0, консоль 0; клавиатурная навигация; Legacy-режим без изменений.
- Нельзя: менять `Fl2.tsx`/`fl2-foundation.css`, логотип, backend, добавлять PIN. Если изменяется `apps/admin/package.json`, обновить доверенный blob в `control-center-verify.mjs` штатно (`git hash-object apps/admin/package.json`), не отключая проверку.

## 6. Воспроизвести снимки
```
node scripts/design/fl2-owner-mock-core.mjs &          # синтетический Core :8000
CORE_API_URL=http://127.0.0.1:8000 npx next dev -p 3001 # из apps/admin
node scripts/design/fl2-owner-capture.mjs out after     # Playwright, Dark/Light × 3 ширины
```
