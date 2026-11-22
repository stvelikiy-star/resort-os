# MARINA SMART FLEX 2.0 — агентская система и комиссии

Только проект. Проценты и правила в документе — **параметры**, значения определяет владелец.

## 1. Существующая реализация (и конфликт имён)
В `resort-os` уже есть `BookingAgent` (модель `booking_agents`, привязана к `propertyId` и броням) и `StaffRole.AGENT`. Это **агенты отеля по бронированиям**, их данные принадлежат отелю. Продавцы MARINA — другая сущность: платформенная, вне отеля. Поэтому:
- таблицы `flex_agents`, отдельный вход (как `flex_platform_users`), отдельные роли;
- **не** использовать `BookingAgent`, `StaffRole.AGENT`, `staff_users`;
- в UI и коде везде «Агент MARINA» / «партнёр продаж», чтобы не путать.

## 2. Модель данных (расширение)
```
flex_agents             (id, name, contact, status, parentAgentId NULL, createdAt)
flex_agent_users        (id, agentId FK, username UNIQUE, passwordHash, isActive)
flex_agent_properties   (id, agentId, propertyId, role CHECK in ('ORIGINATOR','MANAGER'), validFrom, validTo, createdBy)
flex_agent_item_origin  (subscriptionItemId PK, agentId, source CHECK in ('AGENT_SALE','SELF','PLATFORM'), at)  -- кто подключил функцию
flex_commission_rules   (id, agentId NULL=по умолчанию, scope CHECK in ('BASE','SKU','MODULE','ALL'), skuKey NULL,
                         kind CHECK in ('ONE_TIME','RECURRING'), pctBps int CHECK 0..10000, fixedAmount, months int NULL,
                         validFrom, validTo, createdBy)
flex_commission_entries (id, agentId, propertyId, paymentAllocationId FK, ruleId FK, base numeric, amount numeric,
                         kind, status CHECK in ('ACCRUED','APPROVED','PAID','REVERSED'), reversalOf NULL, createdAt,
                         UNIQUE(paymentAllocationId, ruleId))   -- защита от двойного начисления
flex_agent_payouts      (id, agentId, amount, method, paidAt, evidence, markedBy, status)
flex_agent_payout_lines (payoutId, commissionEntryId, amount)
flex_agent_kpi_daily    (agentId, day, properties_active, mrr_originated, collected, commission_accrued, churned)
```
Баланс агента = Σ(`APPROVED`) − Σ(выплаты) (вычисляется).

## 3. Правила начисления
- Начисление **только** по подтверждённым аллокациям платежей (слой C биллинга); счёт, QR и «ожидается» комиссии не порождают.
- База: сумма аллокации, относящаяся к позиции (за вычетом налогов/скидок — определить), × процент правила. Для частичной оплаты — пропорционально.
- Приоритет правил: SKU агента → модуль агента → общее правило агента → умолчание платформы. Побеждает самое узкое.
- Разовое (ONE_TIME): за первое подтверждённое подключение функции. Регулярное (RECURRING): с каждого подтверждённого ежемесячного платежа, на срок `months` или бессрочно — **решение владельца**.
- Смена агента отеля: только новая запись `flex_agent_properties` с датой; прошлые начисления не пересчитываются.
- Возврат/кредит-нота → отрицательная запись `REVERSED` (с `reversalOf`), баланс может уйти в минус (удержание из следующей выплаты).
- Отмена до оплаты — комиссии нет.

## 4. Пример (иллюстрация; проценты условные)
Отель оплатил 11 950: база 10 000, функция A 1 350, B 600. Правила: база 10 %, A 20 % разово + 5 % регулярно, B 0.
- 1-й платёж: база 1 000; A 270 (разово) → 1 270 (A регулярно не считаем в 1-й раз).
- Следующий месяц: база 1 000; A 5 % × 1 350 = 67,5 → 1 067,5.
- Возврат 1 350 за A: −270 (разово) возвращается, регулярная часть пересчитывается пропорционально возврату.

## 5. Доступ агента (минимум данных)
Видит: свои отели (название, статус подписки, подключённые SKU, суммы своих комиссий, статус оплаты счёта в агрегированном виде). **Не видит**: брони, гостей, платежи гостей, финансы отеля, персонал, цены других агентов. Реализация — отдельные API-пути `/api/v1/agent/*`, отдельный токен, запросы только через `flex_agent_properties`, тесты на утечку.

## 6. Кабинет агента
Мои отели; подключённые функции и кто подключил; комиссии (начислено/утверждено/выплачено/удержано); история выплат; KPI (активные отели, MRR, удержание, отток); рейтинг (по полученным, а не по обещанным деньгам).

## 7. Риски / приёмка
Риски: двойное начисление, комиссия с возвращённых платежей, конфликт «кто подключил», раскрытие данных отеля. Приёмка: уникальность начисления на аллокацию; возврат создаёт сторно; агент не получает 200 на чужой отель; баланс сходится с суммой выплат и записей; изменение правил не пересчитывает прошлое.
