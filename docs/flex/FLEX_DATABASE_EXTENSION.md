# MARINA SMART FLEX 2.0 — расширение схемы БД

Дополняет `FLEX_DATABASE_DESIGN.md`. Только проект; миграции не созданы. Существующие таблицы не меняются.

## 1. Изменения относительно FLEX 1
| FLEX 1 | FLEX 2.0 |
|---|---|
| `flex_modules`, `flex_plan_modules`, `flex_module_prices` | + `flex_features`, `flex_skus`, `flex_prices` (версионные), `flex_feature_limits`, `flex_bundles`, `flex_bundle_items`, `flex_promotions` |
| `flex_subscription_modules` | → `flex_subscription_items` |
| `flex_invoices` immut. | + `flex_credit_notes` |
| `flex_payments` (ручные) | + `flex_payment_intents`, `flex_payment_events`, `flex_payment_allocations`, `flex_account_balance`, `flex_refunds` |
| — | агенты: `flex_agents` … (см. AGENT_COMMISSION) |
| — | аналитика: `flex_events`, `flex_usage_events`, `flex_metrics_daily`, `flex_subscription_state_history` |

## 2. Ключевые таблицы
```
flex_features         (key PK, moduleKey FK, name, enforcement CHECK in ('SERVER_GATE','USAGE_METER','NONE'), status)
flex_skus             (id, featureKey FK NULL, moduleKey FK NULL, code UNIQUE, name, priceKind CHECK in
                       ('FLAT_MONTH','PER_UNIT','TIERED','USAGE','ONE_TIME','SEASON'), version int, status)
flex_prices           (id, skuId FK, currency, amount, tiers jsonb NULL, validFrom, validTo, UNIQUE(skuId, validFrom))
flex_feature_limits   (id, skuId FK, metric text, included numeric, overagePrice numeric NULL, hardCap numeric NULL, period)
flex_subscription_items(id, subscriptionId FK, skuId FK, qty numeric, unitPrice numeric, currency, discountPct,
                       startsAt, endsAt, season text NULL, state CHECK in ('ACTIVE','READ_ONLY','OFF'), source, agentId NULL, createdBy)
flex_usage_events     (id, propertyId, featureKey, qty numeric, at timestamptz, idemKey UNIQUE)
flex_payment_intents  (id, invoiceId FK, provider, providerRef, amount, currency, qrPayload, status, expiresAt, idemKey UNIQUE)
flex_payment_events   (id, provider, providerEventId, rawBody bytea, receivedAt, status CHECK in ('NEW','APPLIED','DUPLICATE','QUARANTINE'),
                       UNIQUE(provider, providerEventId))
flex_payments         (id, propertyId, provider, providerPaymentId, amount, currency, paidAt, status, UNIQUE(provider, providerPaymentId))
flex_payment_allocations(id, paymentId FK, invoiceId FK, amount numeric CHECK >0)
flex_subscription_state_history(id, propertyId, fromState, toState, reason, actor, at)
flex_notifications    (id, propertyId, invoiceId NULL, kind, channel, status, UNIQUE(invoiceId, kind))
```

## 3. Изоляция (tenant/RBAC/RLS)
- Все `flex_*` таблицы отеля содержат `tenantId`+`propertyId`; FK составной на `properties(tenantId,id)`.
- Включить RLS на `flex_*`: политика `propertyId = current_setting('flex.property_id')::uuid` для роли отеля; платформенная роль и агент — отдельные политики (агент — через `flex_agent_properties`).
- Установка `flex.property_id` в начале транзакции из trusted-контекста (`trusted_property_id`); без контекста запросы возвращают 0 строк (fail-closed).
- Права: `flex_payment_events`, `flex_change_log`, `flex_events` — INSERT only (триггер запрещает UPDATE/DELETE).

## 4. Индексы
`flex_subscription_items(subscriptionId, state)`, `flex_payments(propertyId, paidAt)`, `flex_usage_events(propertyId, featureKey, at)`, `flex_events(ts)`, партиционирование `flex_usage_events`/`flex_events` по месяцам.

## 5. Миграция и откат
Только добавление таблиц; данные существующих отелей не изменяются; backfill «GRANDFATHERED» — отдельный скрипт, идемпотентный; откат — удаление `flex_*` (зависимостей из существующих таблиц нет, кроме опционального `UNIQUE(tenantId,id)` на `properties`, которое откатывается индексом).

## 6. Приёмка
Тест RLS (отель A не видит B ни в одной таблице `flex_*`); уникальности платежей; триггеры immutability; нагрузочный тест на 500 SKU и 1000 отелей.
