# MARINA FLEX — INVESTOR FINANCE (учёт, формулы, БД)

Только проект. **Все числа в примерах — иллюстрация, не условия.** Проценты, сроки, суммы, лимиты задаются индивидуально в договоре владельцем; юридическую форму договора определяет юрист.

## 1. База расчёта: только фактически полученная подписочная выручка
База = Σ `flex_payment_allocations` (подтверждённые аллокации оплат подписок, слой C биллинга FLEX 2.0) за период, **за вычетом** возвратов и кредит-нот за тот же период. Не входят: выставленные неоплаченные счета, MRR/ARR, прогнозы, платежи гостей отелей, комиссии агентов (если договором не предусмотрено иное), НДС/налоги (определяет договор). Каждая аллокация попадает в расчёт инвестора **один раз**: `UNIQUE(contractId, allocationId)`.

## 2. Параметры договора (персональные)
`principal` (сумма вклада), `currency`, `sharePct` (доля, bps), `baseScope` (ALL | MODULES[] | SKUS[]), `baseDeductions` (список: refunds, taxes, agentCommissions — флаги), `startDate`, `returnPhase` (до возврата вклада), `bonusPhase` (после возврата): `bonusPct` и `bonusDurationMonths` либо `bonusUntil`, `payoutSchedule` (месяц/квартал), `minPayout`, `capTotal` (потолок суммарных выплат, если есть), `statsScope`, `status`, версия договора.

## 3. Формулы
Для периода t:
- `Base_t = Σ alloc_t(в scope) − Σ refunds_t(в scope) − deductions_t`.
- Фаза определяется накопленным `PaidBack = Σ начислений фазы RETURN` (на уровне начислений, не выплат — выбор владельца, см. §8).
- Фаза RETURN: `Accr_t = Base_t × sharePct`, но не более `Remaining = principal − PaidBack_{t-1}`; остаток от `Accr` сверх `Remaining` переходит в фазу BONUS (**разделение на границе**).
- Фаза BONUS (если `now ≤ bonusUntil`): `Accr_t = Base_t × bonusPct` (или `sharePct`, по договору).
- Корректировка/возврат: отдельная запись с отрицательной суммой, ссылка на исходное начисление.
- Потолок: `Σ Accr ≤ capTotal` (если задан).
- Состояния денег: `ACCRUED` (начислено) → `AVAILABLE` (доступно к выплате: по расписанию, после закрытия периода и сверки, ≥ `minPayout`) → `PAID` (выплачено, подтверждено документом). `Available_balance = Σ AVAILABLE − Σ PAID-аллокации`. Отрицательные корректировки уменьшают ACCRUED/AVAILABLE и могут давать удержание из следующей выплаты.
- Остаток до возврата: `Remaining = principal − Σ(начисления фазы RETURN, net of reversals)`; «выплачено» отражается отдельно (`PaidOut`).
- Прогноз (отдельно от факта, помечается «оценка»): `Forecast_t+k = средняя Base за последние m закрытых периодов × sharePct`; не показывается при m < минимума истории.

## 4. Пример (иллюстрация)
principal 1 000 000; sharePct 10 %; BONUS: 5 % на 12 месяцев.
- Месяц 1: Base 300 000 → Accr 30 000; Remaining 970 000.
- Месяц 33 (условно): Remaining 12 000, Base 300 000. Для закрытия возврата нужна база 12 000 / 10 % = 120 000 → начисление RETURN 12 000. Оставшаяся база 300 000 − 120 000 = 180 000 идёт по ставке BONUS: 180 000 × 5 % = 9 000. Итого за месяц 21 000 (метод деления — решение владельца и договора).
- Возврат клиенту 100 000 из месяца 5 → отрицательное начисление −10 000 (RETURN), Remaining +10 000.

## 5. Проверка совокупных обязательств
`Obligation_i = (principal_i − PaidBack_i) + ожидаемые BONUS до конца срока (по прогнозу, помечено) `. Сводка компании: `Σ Obligation_i`, `Σ ближайшие выплаты (30/60/90 дней)`, доля базы, уходящая инвесторам: `Σ sharePct_i` (по пересекающимся scope).
Правила утверждения договора (блокирующие, значения порогов задаёт владелец):
1. `Σ sharePct` по пересекающимся scope ≤ порог (например, не 100 %, а с запасом).
2. `Σ ближайшие выплаты ≤ ожидаемая полученная выручка × коэффициент`.
3. Сумма capTotal по всем договорам не превышает лимит компании.
Предупреждения на экране «Обязательства»: превышение порога, сжатие запаса, просрочка выплат.

## 6. Модель БД
```
flex_investors        (id, name, contact, status, createdAt)                         -- PII минимально
flex_investor_users   (id, investorId FK, username UNIQUE, passwordHash, totpSecret, isActive)
flex_inv_contracts    (id, investorId FK, currentVersionId FK, status CHECK in
                       ('DRAFT','APPROVED','ACTIVE','COMPLETED','SUSPENDED','TERMINATED'),
                       approvedBy, approvedAt)
flex_inv_contract_versions (id, contractId FK, version int, terms jsonb, principal numeric, currency,
                       sharePct int, bonusPct int, bonusUntil date, capTotal numeric, effectiveFrom, createdBy,
                       UNIQUE(contractId, version))       -- неизменяемая; смена условий = новая версия, прошлое не пересчитывается
flex_inv_period_close (id, periodStart, periodEnd, status CHECK in ('OPEN','CLOSED'), closedBy, baseSnapshot jsonb)
flex_inv_accruals     (id, contractId FK, periodId FK, allocationId FK NULL, phase CHECK in ('RETURN','BONUS'),
                       base numeric, rateBps int, amount numeric, status CHECK in ('ACCRUED','AVAILABLE','PAID','REVERSED'),
                       reversalOf NULL, createdAt, UNIQUE(contractId, allocationId, phase))
flex_inv_payouts      (id, investorId, contractId, amount, method, paidAt, evidence, status, createdBy, approvedBy,
                       idemKey UNIQUE)
flex_inv_payout_lines (payoutId FK, accrualId FK, amount, PRIMARY KEY(payoutId, accrualId))
flex_inv_adjustments  (id, contractId, accrualId NULL, amount, reason, createdBy, approvedBy)
flex_inv_documents    (id, investorId, contractId, kind CHECK in ('CONTRACT','STATEMENT','PAYOUT_ACT','ADJUSTMENT'),
                       storageRef, sha256, createdAt)       -- файлы вне БД, контрольная сумма
flex_inv_notifications(id, investorId, kind, refId, channel, status, UNIQUE(kind, refId, channel))
flex_inv_public_stats (VIEW)    -- агрегаты без propertyId, с порогом малых групп
```
Ограничения: CHECK `amount ≠ 0` для начислений; сумма `payout_lines` по начислению ≤ его суммы; триггеры «только вставка» для accruals(кроме статуса по правилам)/payouts/adjustments/documents/period_close после CLOSED; `closed` период нельзя править — только корректировкой в открытом.
Журнал: все действия — в `flex_change_log` (actorKind INVESTOR | PLATFORM | SYSTEM).

## 7. Процесс начисления (идемпотентное задание)
1. Закрыть период (`CLOSED`) после сверки платежей биллинга. 2. Снять `baseSnapshot`. 3. Для каждого `ACTIVE` договора посчитать начисления по §3 в одной транзакции; повтор — no-op. 4. Перевод `ACCRUED → AVAILABLE` по расписанию. 5. Выплата: `Idempotency-Key`, блокировка строк, проверка `Available`, двойное подтверждение, акт-документ, уведомление. 6. При возврате платежа отеля — сторно в открытом периоде.

## 8. Разделение с агентскими комиссиями
Разные таблицы, роли и API; общий только источник — подтверждённые аллокации (`flex_payment_allocations`) **как вход**, без записи в чужой регистр. Вариант «комиссия агента вычитается из базы инвестора» включается флагом договора (`deductions.agentCommissions`) — по умолчанию выключен. Тест: изменение комиссионных правил не меняет начисления инвестору, если флаг выключен.

## 9. Решения владельца
1. Что входит в базу (налоги, комиссии агентов, возвраты, какие модули). 2. Фаза возврата считается по начислению или по фактической выплате. 3. Метод деления на границе фаз. 4. Режим BONUS: ставка и срок. 5. График выплат и `minPayout`. 6. Пороги обязательств и потолки. 7. Что показывать инвестору (`statsScope`). 8. Валюта договоров. 9. Роль INVESTOR_MANAGER и лимиты выплат. 10. **Юрист: правовая форма договоров, налоги, возможное регулирование, хранение документов, раскрытие данных.**

## 10. Тестовые сценарии расчётов
1. Эталонная таблица: 24 месяца базы → суммы начислений совпадают с ручным расчётом.
2. Граница RETURN/BONUS: деление базы точное, сумма начислений не превышает ожидаемой.
3. Возврат платежа после выплаты → отрицательное начисление, удержание из следующей выплаты, `Remaining` корректен.
4. Повторный запуск начисления / повторный вебхук биллинга → без дублей (`UNIQUE`).
5. Смена условий договора → новая версия, прошлые начисления не меняются.
6. `capTotal` достигнут → начисления останавливаются.
7. Неподтверждённый платёж/неоплаченный счёт не попадает в базу.
8. Несколько инвесторов с пересекающимся scope → проверка §5 блокирует утверждение при превышении.
9. Выплата > Available → отказ; параллельные выплаты → одна проходит.
10. Сверка: `Σ PaidOut + Σ Available + Σ ACCRUED(не доступно) = Σ начислений − Σ сторно`.
11. Часовой пояс и границы периода (последний день месяца 23:59).
12. Агентские комиссии не влияют на инвестора при выключенном флаге.

## 11. Существующая реализация / нужно / зависимости
Есть: журнал, шаблоны изоляции. Нет: всех компонентов инвестора. Зависит от: биллинга и аллокаций FLEX 2.0 (P1), RLS/тенант (P0), платформенного контура. Порядок: после стабильного биллинга (P2); до этого — только договоры и ручной учёт вне платформы.

## 12. Приёмка
Все тесты §10 и тесты 1–12 из `FLEX_INVESTOR_PORTAL.md`; сверка по формуле §10.10 равна нулю; инвестор не получает данных вне своего договора; три денежных контура не пересекаются.
