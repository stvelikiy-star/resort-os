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
| 2 | Отдельный FLEX QA project и DB: НЕ использовать существующую PMS/чужую DB; TLS, закрытые backend origins, журналы, непубличный Postgres, секреты вне repo | QA resource inventory |
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

## Открытые внешние блокеры

На 2026-11-23 отдельная облачная FLEX QA не создана.
Railway ответил: «Your trial has expired. Please select a plan to continue
using Railway». В доступном Supabase нет проекта FLEX, отдельного Vercel
проекта FLEX также не обнаружено. Платные ресурсы без согласованного тарифа
не создаются.

**Следующая фактическая работа:** добиться зелёного CI PostgreSQL на PR #588;
после этого подготовить независимую QA-площадку с известной стоимостью.
