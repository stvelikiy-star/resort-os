# MARINA SMART FLEX — ограниченная управленческая QA-приёмка без платежей

**Дата:** 2026-11-23. **Статус:** NO-GO до всех нижеописанных доказательств.
Это отдельный релиз MARINA FLEX; не выпуск гостиничного MARINA SMART PMS.

## Scope первого допуска

Входит: SUPER_ADMIN, коммерческий реестр гостиниц, регистрация PENDING,
подтверждение привязки доверенной PMS подписью на синтетических данных,
полный коммерческий каталог, неизменяемые версии цен, конфигурационные
предложения DRAFT/OFF, HOTEL_OWNER read-only, личные QA отчёты SALES_AGENT
и INVESTOR, RU/KG/EN, Dark/Light/mobile, ручной аудит.

Не входит: платежи любого вида, наличные, кассовые операции, выставление
настоящих счетов, подтверждения получения денег, банк, QR, возвраты,
выплаты, финансовые проводки и автоматический ENFORCE в работающей PMS.
Эти модули не удалять, но НЕ разворачивать и НЕ использовать.

## Блокирующие gates (проходить последовательно)

| Gate | Проверка и точный результат | Ответственный/доказательство |
|---|---|---|
| 0 | PR #588: точный HEAD SHA, все required GitHub CI PASS; failed/queued/skipped mandatory checks недопустимы | GitHub checks на одном SHA |
| 1 | Чистый PG16: 0001–0011, RLS + writer, негативные cases; восстановление backup в **независимую** PostgreSQL | SQL logs, restore report |
| 2 | Отдельный Vercel FLEX QA и совместимая изолированная Postgres через Vercel-интеграцию; Cloudflare DNS/TLS/Access, закрытые backend origins, секреты вне repo | QA resource inventory + URLs |
| 3 | Отдельный OIDC issuer EdDSA/JWKS, exact iss/aud/redirect, PKCE, MFA, короткоживущие токены, серверные memberships+grants, subject binding | Журнал сценариев ролей |
| 4 | SUPER_ADMIN: только в QA создать гостиницу PENDING; повтор запроса -> тот же ID; изменённый повтор -> 409; поддельный role/MFA -> 403 | Подписанный HTTP E2E |
| 5 | Hotel A/B: запрос владельца A к B -> 403/404 и никаких B данных, включая drafts, invoices; ошибочный PMS signer/replay/expired -> reject | HTTP/SQL traces |
| 6 | Каталог: создать PLANNED; опубликованный список не меняется; будущие цены v1/v2; история неизменяема; предложение DRAFT/OFF не меняет `flex_subscriptions` | PostgreSQL row diff |
| 7 | SALES_AGENT A/B и INVESTOR A/B: два изолированных кабинета, отчёты QA_ONLY; чужие договоры/начисления -> deny; `actual_paid` нельзя выставить из UI | Signed token E2E |
| 8 | Браузер QA: все доступные кнопки, загрузка/отсутствие данных/ошибки/401/403, RU/KG/EN ручная корректура; Desktop+390px+320px, Dark/Light | Видео/скриншоты и чек-лист |
| 9 | Перепроверить `/api/status`: `payments_enabled=false`, `payouts_enabled=false`; запрещённые пути POST отсутствуют; ограничение доступов PMS остается OFF | Security test |
| 10 | Единственный release candidate и один QA endpoint, backup/restore, мониторинг 5xx и доступности, план отката протестирован | Release sign-off |

**НЕ считать** зелёную synthetic CI заменой gates 2–10. Не писать «живые
гостиницы подключены», если не проведён подписанный пилот.

## Конфигурация QA

Обязательные отдельные переменные окружения внутри защищённых сервисов (значения
не включать в документацию, GitHub или клиентский JS):

- `FLEX_DATABASE_URL`: отдельная PostgreSQL с least-privilege ролями.
- `FLEX_ENVIRONMENT=qa` и `FLEX_ENABLE_QA_CATALOG_DRAFTS=true`;
  для регистрации и связи — отдельные QA флаги.
- `FLEX_CATALOG_ADMIN_API_ORIGIN`, `FLEX_ONBOARDING_API_ORIGIN`,
  `FLEX_API_ORIGIN`, `FLEX_PARTNER_API_ORIGIN`: закрытые HTTPS origins.
- `FLEX_OIDC_ISSUER`, `FLEX_OIDC_CLIENT_ID`, `FLEX_API_AUDIENCE`;
  EdDSA JWT/JWKS и серверный MFA, без user-editable role claims.
- `FLEX_SESSION_KEY`: случайный 32-byte key, только на сервере.

Активные MARINA SMART гостиницы, их миграции, API, RBAC и бэкапы
не являются частью этого QA. Не переиспользовать реальных пользователей/пароли.

## Безопасный откат

1. При провале gate **прекратить допуск** и сохранить audit/CI логи.
2. Отозвать только QA-клиент и QA-сессии FLEX, закрыть ingress;
   выключить `FLEX_ENABLE_QA_* ` на FLEX Console/Backend.
3. **НЕ** удалять и не трогать PMS, текущие гостиницы или другие проекты.
4. Вернуть изолированную FLEX QA PostgreSQL из проверенной QA-копии, а не
   переписывать историю подписок или применять downgrade к PMS.
5. Новый исправленный SHA получает повторную полную приёмку.
6. Не объединять цепочку Draft PR в `main` до отдельного утверждения.

## Утверждённый стек: GitHub → Vercel → Cloudflare (решение владельца 2026-11-23)

**GitHub:** исходный код MARINA SMART FLEX, отдельные Draft PR,
автоматизированные проверки, история решений. `main` и PMS Production
не меняются до приёмки.

**Vercel:** выделенный проект MARINA FLEX QA для веб-консоли и совместимых
серверных функций. Существующую MARINA SMART и её проекты не использовать
как тестовую площадку FLEX. Текущие Node HTTP server и Python FastAPI
**не считать автоматически совместимыми** с Vercel Functions:
нужно подготовить deployment adapter/entrypoint и проверить serverless
лимиты, соединения, cookie/OIDC и окружение на Preview.

**Cloudflare:** DNS, HTTPS/TLS, защищённый доступ к QA (Access/WAF по
потребности) и изолированный off-site backup в R2 после подтверждения
реального восстановления. Не менять существующие доменные маршруты PMS.
Домен/поддомен FLEX QA ещё не выбран и не подключён.

**PostgreSQL 16:** текущий контракт 0001–0011 использует Postgres роли,
триггеры и RLS. Подключать только **отдельную Postgres-совместимую БД**
через Vercel Marketplace storage integration после проверки версии,
ролевых прав, сетевой защиты, сроков жизни соединений и стоимости.
Сам Vercel не заменяет PostgreSQL; Cloudflare D1 использует SQLite и
не является совместимой заменой текущей схемы. Никакие чужие БД не
переиспользовать. Для любой интеграции миграции следует проверить в
изолированной `private` схеме и без открытого Data API.

**Railway исключён полностью.** Не предлагать его как резервный
хостинг и не создавать там ресурсы.

## Открытые блокеры

- Пока нет выделенного проекта Vercel FLEX QA и проверенного Preview URL.
- Не выбрана отдельная Postgres-интеграция через Vercel и не утверждена
  её стоимость (возможно $0, но не предполагать).
- Не настроены Cloudflare DNS/Access/R2 для FLEX QA.
- Не выпущены отдельные OIDC/MFA credentials и DB runtime роли.
- Нет подтверждённого внешнего зашифрованного backup и restore постоянной FLEX базы.
- Платежи, касса, наличные, payout и связанные API остаются замороженными.

**Следующее действие:** получить полный PASS CI на едином SHA PR #588;
затем спроектировать и проверить Vercel Preview + Cloudflare QA
маршрутизацию, отдельную Postgres интеграцию и восстановление, не
меняя MARINA SMART Production.
