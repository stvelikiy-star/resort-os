# MARINA SMART FLEX — архитектура

Статус: **только проект**. Код, миграции, RBAC и платные ограничения не менялись. Ветка `docs/marina-flex-architecture-20261122`, от `main` @ 2642eed.

## 1. Результаты аудита (проверено по коду)

| Область | Факт в репозитории | Вывод для FLEX |
|---|---|---|
| Стек | Prisma-схема (51 миграция, 38 моделей), API на FastAPI (`services/api/app`, 126 файлов, ~267 маршрутов, SQL через asyncpg), клиенты: `apps/admin`, `apps/staff`, `apps/web` (Next.js), `apps/mobile` (Expo) | Серверная проверка добавляется в Python API; клиенты только отображают |
| Мультитенантность | Таблица `tenants`, `properties.tenantId NOT NULL` (миграция zz107). `trusted_property_id` берёт property из сессии и проверяет активность tenant **только если** `MARINA_TENANT_CONTEXT_ENABLED=true`; по умолчанию `false` — тогда действует одна `PROPERTY_CODE` из окружения | Модель «tenant → property» есть, но **не включена по умолчанию**. Это зависимость P0 для FLEX |
| RLS в PostgreSQL | В миграциях `ENABLE ROW LEVEL SECURITY` / `POLICY` не найдено | Изоляция держится на запросах приложения (`WHERE propertyId=…`). Для биллинга нужны ограничения в БД и тесты изоляции |
| Модули на отель | `property_product_settings.enabledModules` (JSON), 10 значений по умолчанию (`GROUPS, AGENTS, MARKETING, DINING, OFFERS, GROWTH, CONTENT, ROOM_QR, POINT_QR, INBOX`). Читается и пишется в `hotel_setup.py`, используется в `apps/admin` (AdminShell, HotelSetupBoard) | Это **единственная** точка «включить/выключить модуль». Найдено использование на клиенте и в `hotel_setup.py`; серверной проверки по маршрутам не найдено → **кнопки скрываются, API остаётся доступен** |
| Права сотрудников | `section_permissions.py`: 26 секций (`PMS, RATES, FINANCE, …`), `SECTION_PATHS` сопоставляет префиксы путей секциям, `staff_users.modulePermissions` (zz112). Роли `StaffRole`: OWNER, MANAGER, RECEPTION, AGENT, MAID, TECHNICIAN, STORE_STAFF, DINING_STAFF, COOK, WAITER, CONTENT_MANAGER, BEACH_PARTNER | Готовая точка встраивания: тот же `path → section` можно расширить до `path → module → entitlement` |
| Платформенный уровень | Роли `SUPER_ADMIN`/`PLATFORM_ADMIN` в коде **не найдены**. Есть `MARINA_UBUNTU_FLEET_PLAN` и `compose.marina-fleet.yaml` (развёртывание, не продуктовая роль) | MARINA SUPER ADMIN нужно создать как отдельный контур, не смешивая с `OWNER` отеля |
| Тарифы, подписки, платежи за подписку | Таблиц и кода не найдено. Есть только платежи гостей (`Payment`, NFC) | Реализуется с нуля |
| Платёжные провайдеры | `runtime_capabilities.py`: `payment_operations=false`, `mkassa=false`, `nfc_wallet=false` (fail-closed) | Автосписание подписок **нельзя** считать готовым. Старт — ручное начисление и ручная отметка оплаты |
| Каналы (Booking.com) | `channel_reservations.py`, документ `MARINA_CHANNEL_RESERVATIONS.md`: ручной ввод броней Booking/Airbnb/Ostrovok. **Подключения, опроса, вебхуков и отправки цен нет**, экран это явно говорит | Channel Manager как платный модуль = **не реализован**; в каталоге помечается «в разработке» |
| ИИ | `ai_sales.py`, `marina_assistant.py`, `guest_assistant.py`, `public_ai_admin.py`; флаг `ENABLE_AI_SALES` через окружение (глобально, не по отелю) | Флаги в `runtime_capabilities` глобальны; для FLEX нужны per-hotel |
| Финансы владельца | ~15 модулей `owner_*`, `hotel_finance.py` | Существующая функция, не продукт-подписка |

## 2. Целевая архитектура

Три слоя, слева направо, сервер — единственный источник истины:

1. **Каталог** (платформа): модули, тарифные планы, цены, зависимости. Меняется только MARINA SUPER ADMIN.
2. **Подписка** (tenant/property): что куплено, на какой срок, по какой цене, статус.
3. **Entitlement** (вычисляемое право): «имеет ли property X доступ к модулю M прямо сейчас». Считается сервером из подписки, пробных периодов, ручных выдач, зависимостей и `grace`-периода.

Проверка на сервере (порядок):
`роль/секция сотрудника (уже есть)` **И** `entitlement property на модуль (новое)` **И** `глобальный kill-switch окружения (уже есть)`.
Право доступа = пересечение, а не замена: модуль не куплен → API отвечает `402/403 MODULE_NOT_ENTITLED`, даже если кнопка видна или запрос идёт напрямую.

Точки встраивания:
- Python: dependency/middleware рядом с `has_section_permission`, использующий `section_for_path` → `module_key` (таблица соответствия в БД, не в коде).
- Клиенты (Web/Admin/Staff/Mobile) получают `GET /entitlements/me` для скрытия кнопок. Скрытие — удобство, не защита.
- Feature flags: два вида. (а) окружение/платформа (kill-switch, уже есть), (б) per-property флаги `property_feature_flags` для постепенного включения; флаг не заменяет entitlement.

## 3. Принципы безопасности (из задания)
- Существующие функции и тарифы действующих клиентов не меняются автоматически: всем существующим отелям при миграции выдаётся **grandfathered** план с полным набором уже используемых модулей и нулевым авто-ограничением (`enforcement=OFF`).
- Данные отеля при отключении модуля сохраняются (soft-disable: чтение истории разрешено, новые операции заблокированы, где это безопасно).
- Нельзя отключать ядро (см. каталог): PMS-шахматка, брони, заезд/выезд, фолио, платежи гостей, финансовые документы, аудит, персонал/права.
- Активные брони, платежи и документы не прерываются: модуль в статусе `GRACE`/`READ_ONLY` пока есть незакрытые операции.
- Откат: каждый шаг за флагом `FLEX_ENFORCEMENT` (OFF → SHADOW → ENFORCE); в режиме SHADOW сервер только логирует «был бы отказ».
- Изоляция отелей: все новые таблицы с `tenantId`+`propertyId`, составные внешние ключи, тесты на чужой `propertyId`.

## 4. Вне объёма этого этапа
Реализация, миграции, изменение RBAC, включение ограничений, платёжные провайдеры, подтверждение внешних интеграций.
