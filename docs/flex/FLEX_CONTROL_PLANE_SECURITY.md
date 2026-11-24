# MARINA FLEX — isolated platform access: verified preview contract

Дата: 2026-11-22. Статус: **код и CI-прототип, без развертывания**.

## Граница

- Исходная PMS MARINA SMART (main) и гостиничные БД **не изменяются**.
- Стек запускается только как **отдельный** `uvicorn app.flex_control_plane:app` из каталога `services/api`, с `FLEX_DATABASE_URL`, который отличается от `DATABASE_URL`.
- Модуль **не импортируется** в `app.main`. Нет endpoint создания, оплаты, блокировки или перевода средств.
- SQL `docs/flex/sql/0001_*.sql` + `0002_*.sql` — **предварительные схемы исключительно для одноразовой QA PostgreSQL**. Не миграции текущей Prisma/PMS.

## Кто определяет доступ

1. Доверенный внешний issuer выпускает короткоживущий **EdDSA** JWT с обязательными `sub`, `iss`, `aud`, `iat`, `nbf`, `exp`, `jti`; максимум 900 секунд.
2. Сервис проверяет подпись **публичным ключом** из `FLEX_AUTH_PUBLIC_KEYS_JSON` по allowlisted `kid`, issuer и audience из отдельных env.
3. Заявленные в токене `role`, `hotel_ids`, `agent_id`, `investor_id` **не используются**. Из проверенного JWT берётся только `sub` и признак `amr=mfa`. Доверенные роли и закреплённые гостиницы считываются из `flex_platform_memberships`, `flex_platform_hotel_grants`, `flex_agents`, `flex_investors` в отдельной БД.
4. Сначала выполняется scoped SELECT под `flex_identity_reader`; только после проверки роли и принадлежности к гостинице выполняется scoped SELECT под `flex_hotel_reader` (для SUPER_ADMIN при MFA — под `flex_platform_admin_reader`).
5. В PostgreSQL читательские роли — **NOLOGIN**. Отдельный runtime-login должен иметь право SET ROLE и **не должен** быть owner/superuser/BYPASSRLS; в startup есть проверка rolsuper/rolbypassrls.
6. Все запросы только параметризованные. SET LOCAL role выполняется из allowlist, SELECT выполняется внутри read-only транзакции, `set_config` получает значения из проверенных серверных scope.
7. `RLS` на `flex_hotels`, `flex_subscriptions`, `flex_subscription_items`, `flex_invoices`, `flex_invoice_lines` и каталог. Остальные финансовые таблицы не выдаются владельцу гостиницы; у них default-deny для клиентской роли.

**Особенность PostgreSQL GUC:** `flex.authorized_hotel_id` можно поменять в SQL-сеансе, поэтому _ни один конечный пользователь не получает DB-логин_; контекст устанавливает только API после JWT + сверки membership. Для защиты от SQL-инъекций — подготовленные запросы и отдельные DB-роли. Перед Production обязателен аудит SQL-инъекций, runtime-grants и сетевой политики доступа к DB.

## Реализованные preview endpoints

| Endpoint | Доступ | Эффект |
| --- | --- | --- |
| GET /health | Общий минимальный ответ | Без доступа к БД и данным |
| GET /v1/me | Любой проверенный активный платформенный участник | Своя роль и scope |
| GET /v1/hotels | SUPER_ADMIN с MFA | Общий реестр без гостей |
| GET /v1/hotels/{id}/subscription | OWNER закреплённого отеля либо SUPER_ADMIN с MFA | Только статус подписки |
| GET /v1/hotels/{id}/invoices | OWNER закреплённого отеля либо SUPER_ADMIN с MFA | Только счета данного отеля, суммы как строки |

Не реализованы: вход/регистрация пользователей, выдача JWT, привязка гостиницы к исходному PMS, изменение прав, управление подписками, полное администрирование, агентские и инвесторские финансовые страницы, выплаты, QR-платежи и аналитические API.

## CI

1. `python scripts/marina_flex_control_plane_auth_test.py`: настоящие EdDSA JWT, отрицательные подписи/алгоритмы/issuer/audience/TTL, отдельный DSN.
2. `scripts/marina_flex_rls_isolation_contract.sql`: две гостиницы, scopes и DEFAULT DENY RLS.
3. `python scripts/marina_flex_control_plane_http_test.py`: HTTP через TestClient с ограниченным DB runtime, owner A/B изолированы, SUPER_ADMIN требует MFA, POST запрещён.

## Запреты до включения

- Существующие гостиницы НЕ переводятся на новые коммерческие условия.
- Нельзя объявлять пилот или Production готовым без работающего внешнего issuer, резервной копии, ротации подписных ключей, восстановления, публичного HTTPS, контроля RLS и полного JWT/E2E.
- Выдача токенов в клиентском приложении из приватного ключа запрещена; только доверенный issuer.
- Реальные платёжные счета/QR, commission payout и investor payout отсутствуют и не должны имитироваться в Production.
- При достижении готовности сервиса сначала проверяются сценарии восстановления, а затем регистрация гостиниц; UI контролирует Claude Code отдельно.

## Следующая техническая работа

1. Отдельная production-ready инфраструктура платформенной авторизации, issuer и MFA (с ревизией ролей).
2. Защищённая операция регистрации и подтверждения привязки HOTEL ⇄ PMS instance с независимой attestation.
3. Версионированный каталог SKU, снимки цен и проверенные обновления signed entitlement.
4. Миграции коммерческой БД с reversibility, backup/restore и проверками.
5. Идемпотентный биллинг и QR-провайдер; только затем ENFORCE.
