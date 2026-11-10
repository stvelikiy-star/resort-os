# MARINA SMART · Lucide icon vocabulary

Единый набор имен для PMS + Mobile. Иконка сообщает функцию, а не право доступа.
Наличие иконки/таба никогда не заменяет серверную проверку роли, property и module grant.
Mobile использует установленный `lucide-react-native`; web пока не имеет Lucide-зависимости,
поэтому этот документ не требует менять существующие web-экраны или добавлять пакет.

## Базовое применение

- Navigation: `23`, stroke `1.9`; active stroke `2.5`. Action: `22`; metric: `24`.
- Использовать Lucide name без переименования и одну функцию — одну основную метафору.
- Декоративные emoji, заполненные glyph и смешивание разных icon packs не вводить.
- Иконка без видимой подписи допустима только для общеизвестного действия и требует
  accessibility label. Статусы всегда имеют текст; цвет и иконка — дополнение.

## Функции PMS и операций

| Функция | Lucide | Где/для кого |
|---|---|---|
| Обзор | `LayoutDashboard` | OWNER, MANAGER |
| Ресепшен | `ConciergeBell` | RECEPTION, OWNER/MANAGER при grant |
| PMS / календарь | `CalendarDays` | OWNER, MANAGER, RECEPTION, AGENT при PMS grant |
| Номер / размещение | `BedDouble` | PMS, housekeeping, reservation detail |
| Гость | `UserRound` / `Users` | один гость / группа гостей |
| Бронь подтверждена | `CalendarCheck2` | reservation status/metric |
| Ожидание / hold | `Clock3` / `CalendarClock` | короткий таймер / календарное ожидание |
| Check-in / check-out | `LogIn` / `LogOut` | действия/состояния размещения |
| Ключ / доступ | `KeyRound` | ключ номера; не общий security status |
| Inbox / сообщение | `MessageCircle` | коммуникации и inbox |
| Задачи | `ClipboardCheck` | список операционных задач |
| Заявки / ремонт | `Wrench` | maintenance/request, TECHNICIAN |
| Уборка | `Sparkles` | HOUSEKEEPING, MAID |
| Restaurant / dining | `UtensilsCrossed` | dining workspace, WAITER |
| Кухня | `ChefHat` | kitchen workspace, COOK |
| Команда / управление | `UsersRound` | staff/admin, OWNER/MANAGER |
| Финансы | `Wallet` | finance; только при соответствующем grant |
| Профиль | `CircleUserRound` | все роли |
| Ещё | `Grid2X2` | overflow navigation, не dashboard |
| Поиск / добавить / закрыть | `Search` / `Plus` / `X` | стандартные действия |
| Назад / далее | `ChevronLeft` / `ChevronRight` | навигация и drill-down |
| Открыть раздел | `ArrowUpRight` | переход, не external-link claim |

## Статусы и обратная связь

| Смысл | Lucide | Правило |
|---|---|---|
| Успешно / готово | `CircleCheck` или `CheckCircle2` | не смешивать внутри одного списка |
| Предупреждение | `AlertTriangle` | warning/attention, обязательно с текстом |
| Ошибка | `AlertCircle` | error state, обязательно с пояснением |
| Ограничение доступа | `LockKeyhole` | permission denied, не offline |
| Проверено / защищено | `ShieldCheck` | только реальная проверка/защита |
| Риск / security alert | `ShieldAlert` | реальный alert, не декор |
| Offline | `CloudOff` | подтверждённое отсутствие связи |
| Неизвестно / помощь | `CircleHelp` или `HelpCircle` | выбрать один вариант в компоненте |
| Отправить | `Send` | сообщение/форму, не «сохранить» |

## Ролевой фокус

`OWNER` и `MANAGER`: `LayoutDashboard`, `UsersRound`, `Wallet`, затем иконка модуля.
`RECEPTION`: `ConciergeBell`, `CalendarDays`, `MessageCircle`. `AGENT`: `CalendarDays`;
не показывать admin/finance без grant. `MAID`: `Sparkles`, `BedDouble`, `ClipboardCheck`.
`TECHNICIAN`: `Wrench`, `ClipboardCheck`. `COOK`: `ChefHat`, `CookingPot`, `ListChecks`.
`WAITER`/`DINING_STAFF`: `UtensilsCrossed`. `STORE_STAFF`: `Package` только для реально
подключённой store-функции. `CONTENT_MANAGER` и `BEACH_PARTNER` — legacy vocabulary:
не придумывать рабочие пространства или иконки без подтверждённого продукта.

Канонический tab mapping хранится в `apps/mobile/src/theme/moduleIcons.ts` и используется
тремя mobile-компонентами:
`overview→LayoutDashboard`, `reception→ConciergeBell`, `pms→CalendarDays`,
`inbox→MessageCircle`, `dining→UtensilsCrossed`, `kitchen→ChefHat`,
`tasks→ClipboardCheck`, `rooms→BedDouble`, `requests→Wrench`,
`admin→UsersRound`, `profile→CircleUserRound`.

Для будущего web-адаптера тот же контракт имён и semantic roles зафиксирован без
runtime-зависимости в `apps/web/lib/module-icon-manifest.ts`. Он не подключён к рабочим
экранам. Соответствие 11 `TabKey`, уникальность и mobile/web parity проверяет
`node scripts/validate-module-icons.mjs`.
