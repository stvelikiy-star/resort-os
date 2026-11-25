# MARINA SMART FLEX — Neon QA и Vercel: фактическая проверка, 2026-11-23

**Статус:** отдельная управленческая QA. Только MARINA SMART FLEX.
**Релиз:** NO-GO до OIDC/MFA, HTTP E2E, Cloudflare R2 и ручной приёмки.
Не относится к MARINA SMART PMS, ее действующим гостиницам и `main`.
Наличные, касса, онлайн-оплата, QR, возвраты, начисления с подтверждением банка
и выплаты не выполняются, права на них серверному пользователю не предоставлены.

## 1. Фактические ресурсы

- Neon Free: `marina-smart-flex-qa`, project `frosty-art-51219188`,
  PostgreSQL 16.16, `aws-eu-central-1`, база `flex_qa`.
- Постоянная ветка: `br-spring-rice-bak1xu5l` (default, `qa`).
- Отдельная закрытая SQL-схема: `flex_private`, 36 прикладных таблиц
  и отдельная таблица `flex_schema_migrations` (всего 37).
  RLS включена на всех 37; 26 имеют FORCE RLS.
  Прямых PUBLIC TABLE grants нет.
- Никаких реальных гостиниц, пользователей, подписок или подтверждённых
  платежей в постоянной базе: всё по 0 на момент проверки.
- GitHub источник зафиксирован: `61e697fafc098aeee08d045791b5b5a1a6d88856`.
  11 записей в `flex_private.flex_schema_migrations` с оригинальными Git
  blob SHA и состоянием; SQL `0001–0008,0010–0011` = APPLIED (10).
  `0009` = `SKIPPED_PAYMENT_FREEZE`: тестовый симулятор не установлен,
  таблица `flex_qa_settlement_evidence` отсутствует.
  Остальные схемы содержат неактивные будущие финансовые структуры,
  но без подтверждений платежей и без API для денег.

## 2. Воспроизводимость, изоляция и восстановление

- Временная ветка `br-wandering-band-bahy77aw`:
  проверена установка полной последовательности 0001–0011. Это **только
  тестовая** ветка, платёжный симулятор не переносить в постоянную QA.
- Временная ветка `br-square-sky-baj4hwy7`:
  проверены 0001–0008,0010–0011 БЕЗ 0009. На ней — исключительно
  синтетические Hotel A/B и два агента/два инвестора для теста RLS.
- RLS/least privilege на временной ветке: без выбранного hotel_id = 0;
  Hotel A видит только A, Hotel B только B; агент/инвестор видит только
  собственную личность, другой субъект не виден.
  Это **DB-level** тест, не замена HTTP/JWT/MFA E2E.
- В постоянной QA создан `flex_qa_read_runtime` — LOGIN без
  SUPERUSER/CREATEROLE/BYPASSRLS, отдельная пустая schema `flex_access`;
  только явные memberships в NOLOGIN reader roles с `INHERIT FALSE`.
  Нет прямого SELECT на гостиницах/платежах, INSERT в коммерческие черновики,
  и нет membership в `flex_qa_settlement_writer` либо writer для денег.
- Neon snapshot: `snap-delicate-hall-ba0zyjpg`,
  `flex-qa-schema-no-payments-20261123` создан с постоянной QA.
  Восстановлен **неразрушающе**, новой веткой
  `br-jolly-wave-ba4j30om`; проверены все 11 ledger rows, отсутствие
  платёжного симулятора и данных, низкие привилегии runtime. **PASS**.
  Это восстановление внутри Neon, НЕ внешний R2 backup.

## 3. Vercel

- Консоль: `marina-smart-flex-qa`, project
  `prj_drTTU7Gs92eM4PmCtJpMnwMleF0D`, защищённый Preview
  `https://marina-smart-flex-54teplpkw-ai-prof-kg.vercel.app`.
- Отдельный FastAPI QA: `marina-smart-flex-api-qa`, project
  `prj_Zs7NtVAr5Qu2NSL5dTzMacxLpx0J`, защищённый Preview
  `https://marina-smart-flex-api-ra1zplh5w-ai-prof-kg.vercel.app`.
- Vercel Authentication включена для `all` в обоих отдельных QA проектах.
- Только API Preview содержит `FLEX_DATABASE_URL` типа `sensitive`,
  на роль `flex_qa_read_runtime` в Neon Free, без GitHub/браузерных секретов.
  `FLEX_ENVIRONMENT=qa`, onboarding/catalog writes = false.
- `apps/flex-api-qa/index.py` предоставляет **только GET /health**:
  реальная проверка подключения и ограничений роли, fail-closed на другой
  БД, отсутствии TLS/секрета или опасных DB правах.
  В нём нет пользовательских, гостиничных или платёжных endpoints.
- Сборка Vercel `READY` подтверждена, но авторизованный HTTP-запрос к
  защищённому `/health` пока не подтверждён. READY ≠ подключение PASS.
- Первая сборка каждого нового QA-проекта попала в Vercel `production`
  target только **внутри изолированного защищённого QA проекта**;
  отдельный Preview создан после. MARINA SMART Production не переключалась.

## 4. Открытые обязательные gates

1. GitHub: полный required CI PASS на **последнем** PR HEAD после
   добавления диагностического FastAPI.
2. Доступ к Preview через авторизованный Vercel CLI/client; проверить
   реальный `GET /health` = 200, отсутствие обхода SSO и отказ на POST.
3. Отдельный доверенный OIDC issuer/EdDSA JWKS, PKCE, MFA и живые
   DB memberships. Neon Managed Better Auth имеет EdDSA, но **обязательное
   MFA пока не поддерживается**; не объявлять его настроенным. Не выдавать
   тестовые/временные токены за реальных пользователей.
4. Проверить SUPER_ADMIN, HOTEL_OWNER A/B, SALES_AGENT A/B, INVESTOR A/B
   через подписанный JWT и backend. Контракты/начисления пользователей
   должны проверяться отдельно; DB identity test недостаточен.
5. Отдельный Cloudflare DNS/HTTPS/Access для FLEX без изменения PMS;
   Cloudflare R2 шифрованный off-site бэкап + **независимое** восстановление,
   RPO/RTO и аудит ключей. В текущей сессии Cloudflare API не подключён.
6. Корректура RU/KG/EN, Dark/Light, мобильные 320/390px, полный браузер E2E,
   откат и подтверждение релизного SHA до снятия NO-GO.

## 5. Нельзя делать

- Нельзя запускать `0009` в постоянной QA или подключать QA settlement
  endpoints, банковские webhook, POS, QR, возвраты, кассы и выплаты.
- Нельзя использовать `flex_qa_owner` в Vercel runtime или добавлять
  `BYPASSRLS`/автоматическое наследование reader/writer ролей.
- Нельзя включать доступ к гостиничным MARINA SMART Production данным
  или перепривязывать живой домен PMS.
- Не объединять цепочку Draft PR в `main` до полной приёмки.
