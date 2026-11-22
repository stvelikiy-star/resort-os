# MARINA SMART FLEX — проект PostgreSQL-схемы

Только проект. Миграции не созданы. Существующие таблицы (`tenants`, `properties`, `property_product_settings`, `staff_users`, `audit_logs`) **не изменяются**; все новые таблицы — отдельные, с префиксом `flex_`. Стиль — как в репозитории: `uuid`, `timestamptz`, camelCase-колонки в кавычках, CHECK вместо enum.

## Таблицы
```
flex_modules            (key PK, name, kind CHECK in ('CORE','PAID','FUTURE'), status CHECK in ('AVAILABLE','BETA','PLANNED'),
                         description, createdAt)               -- каталог; новый модуль = новая строка
flex_module_dependencies(moduleKey FK, requiresKey FK, PK(moduleKey,requiresKey), CHECK moduleKey<>requiresKey)
flex_module_paths       (id, pathPrefix UNIQUE, moduleKeys text[])  -- замена SECTION_PATHS из кода, правится без релиза
flex_plans              (id, code UNIQUE, name, basePrice numeric(12,2), currency, status, createdAt)   -- «BASE» = 10 000 KGS/мес
flex_plan_modules       (planId FK, moduleKey FK, PK(planId,moduleKey))                                 -- что входит в план
flex_module_prices      (id, moduleKey FK, billingPeriod CHECK in ('MONTH','SEASON','CUSTOM'), price numeric(12,2),
                         currency, validFrom, validTo)

flex_subscriptions      (id, tenantId FK, propertyId FK, planId FK, status CHECK in
                         ('TRIAL','ACTIVE','GRACE','SUSPENDED','CANCELLED','GRANDFATHERED'),
                         priceOverride numeric NULL, discountPct numeric CHECK 0..100, startsAt, endsAt, graceEndsAt,
                         createdBy, createdAt)   -- одна «текущая» на property: частичный UNIQUE WHERE status IN (...)
flex_subscription_modules(id, subscriptionId FK, moduleKey FK, source CHECK in ('PLAN','PURCHASED','TRIAL','MANUAL'),
                         startsAt, endsAt, priceOverride, note, createdBy)
flex_entitlements       (propertyId FK, moduleKey FK, state CHECK in ('ON','GRACE','READ_ONLY','OFF'),
                         validUntil, reason, computedAt, PK(propertyId,moduleKey))   -- кэш; пересчёт при любом изменении подписки
flex_property_flags     (propertyId FK, flagKey, enabled bool, updatedBy, updatedAt, PK(propertyId,flagKey))

flex_offers             (id, propertyId, items jsonb, totalPrice, validUntil, status, createdBy)     -- индивидуальные КП
flex_requests           (id, propertyId, kind CHECK in ('CONNECT','RENEW','DISCONNECT'), moduleKey, period, status, createdBy, decidedBy)

flex_invoices           (id, propertyId, number UNIQUE, periodStart, periodEnd, total, currency, status CHECK in
                         ('DRAFT','ISSUED','PAID','VOID'), issuedAt)    -- ISSUED/PAID неизменяемы
flex_invoice_lines      (id, invoiceId FK, moduleKey, description, qty, unitPrice, amount)
flex_payments           (id, invoiceId FK, amount, method CHECK in ('MANUAL_TRANSFER','CASH','OTHER'), paidAt,
                         evidence text, markedBy)    -- ручная отметка; провайдеры позже
flex_change_log         (id, propertyId, actorId, actorKind CHECK in ('PLATFORM','OWNER','SYSTEM'), action, before jsonb, after jsonb, createdAt)
flex_platform_users     (id, username UNIQUE, passwordHash, role CHECK in ('SUPER_ADMIN','BILLING'), isActive)  -- отдельно от staff_users
```

## Правила целостности
- Все таблицы с отелем несут `tenantId`+`propertyId` и составной FK на `properties(tenantId,id)` (уникальный индекс уже есть: `properties(tenantId, code)`; добавить `UNIQUE(tenantId,id)` — единственное изменение существующей таблицы, делается отдельной согласованной миграцией).
- Entitlement считается функцией `flex_recompute(propertyId)` из подписки + пробных + ручных + зависимостей; ядро всегда `ON`.
- `flex_invoices` после `ISSUED` и `flex_payments`, `flex_change_log` — только вставка (триггер запрещает UPDATE/DELETE), как уже сделано для оплат рекламы в KÖL и журналов owner-accounting.
- Деньги — `numeric(12,2)`, валюта явная; конвертации не изобретать.
- Права: роль приложения получает SELECT/INSERT на эти таблицы; `flex_platform_users` и тарифы недоступны ролям отеля.

## Миграция существующих данных (безопасный откат)
1. Создать таблицы пустыми (откат = `DROP TABLE flex_*`, существующие данные не затронуты).
2. Для каждого существующего property создать подписку `GRANDFATHERED` с модулями из `enabledModules` + все ядро. Цены/ограничения не применяются.
3. `FLEX_ENFORCEMENT=OFF` → `SHADOW` (только лог) → `ENFORCE` по отелям, по одному.
