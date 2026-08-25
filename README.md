# Resort OS — «Три Короны»

Единая гостиничная система для Resort & SPA «Три Короны», Чолпон-Ата, Иссык-Куль.

## Что входит в текущий V1

Канонический контур:

`PUBLIC SITE / PMS / STAFF / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Resort Core является единственным источником гостиничной правды для:
- 84 комнатных позиций и 12 категорий;
- тарифов и детерминированной доступности;
- ReservationRequest и Reservation;
- размещения гостя по комнатам/датам;
- PMS-шахматки и realtime;
- check-in / check-out;
- уборки и ремонта;
- сотрудников/RBAC;
- внутренних менеджерских фактов оплат;
- управленческих отчётов;
- контролируемых API для n8n.

Клиентские каналы V1 оркестрируются через n8n:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- сайт -> Resort Core напрямую.

Задача автоматизации — довести клиента до горячей квалифицированной заявки. Предоплату и условия менеджер определяет и принимает самостоятельно.

NFC-контур сохранён в репозитории как отложенный исторический код, но **не является активной частью V1**.

## Ключевой операционный экран

PMS Chessboard V2 — основной ежедневный экран ресепшена.

Поддерживается серверно-авторитетный workflow:
- перенос будущей брони на другой номер;
- перенос брони на другую дату с сохранением длительности;
- изменение/сокращение/продление дат;
- split stay / последовательные сегменты проживания в разных комнатах;
- переселение уже заселённого гостя без переписывания прожитой истории;
- check-in/check-out;
- карточка гостя, внутренние оплаты, задачи и аудит;
- PostgreSQL-защита от пересекающихся активных блоков номера;
- preview -> explicit confirm -> atomic transaction;
- stale-version и race-conflict rollback.

## Канонические документы

- `knowledge/04_CURRENT_STATE.md` — фактическое состояние реализации.
- `knowledge/07_EXECUTION_PLAN_THREE_CROWNS.md` — активный порядок разработки.
- `knowledge/06_THREE_CROWNS_MASTER_SPEC.md` — спецификация объекта.
- `docs/PMS_CHESSBOARD_MUTATION_CONTRACT.md` — контракт безопасных изменений шахматки.
- `docs/THREE_CROWNS_SOURCE_RECONCILIATION_2026-08-25.md` — сверка исходных данных.
- `automation/n8n/README.md` — граница n8n / Resort Core.

Критическое правило проекта:

`TARGET != CURRENT. IMPLEMENTED != VERIFIED. DEVELOPMENT VERIFIED != PRODUCTION READY.`

## Структура репозитория

- `services/api/` — FastAPI Resort Core.
- `packages/database/prisma/` — каноническая Prisma/PostgreSQL схема.
- `packages/database/sql/` — PostgreSQL-инварианты, которые не выражаются Prisma schema.
- `apps/admin/` — PMS / ресепшен / шахматка / управление.
- `apps/web/` — публичный продающий сайт и booking widget.
- `apps/staff/` — PWA/Mini App для персонала.
- `automation/n8n/` — provider-neutral workflow templates.
- `scripts/` — bootstrap, seed, backup/restore, preflight.
- `data-intake/` — подтверждённые/квалифицированные входные данные отеля.
- `knowledge/` — канонические product/domain/current-state документы.

## Локальный запуск Core

Требования:
- Docker;
- Node.js 22+;
- Python 3.12+.

### 1. PostgreSQL

```bash
docker compose up -d postgres
```

### 2. Environment

```bash
cp .env.example .env
set -a && source .env && set +a
```

### 3. Development schema

Для локальной development-среды:

```bash
cd packages/database
npm install
npx prisma validate
npx prisma db push
cd ../..
```

`prisma db push` не является постоянной production migration strategy. Production требует migration baseline и preflight gate.

### 4. Python + DB constraints + seed

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt
python scripts/apply_core_constraints.py
python scripts/seed_from_intake.py
```

Seed останавливается, если intake больше не сходится ровно в 84 номера / 12 категорий.

### 5. Создать/обновить владельца

Задайте безопасные локальные значения `BOOTSTRAP_OWNER_*` в `.env`, затем:

```bash
python scripts/bootstrap_owner.py
```

### 6. Запустить Resort Core

```bash
python -m uvicorn app.app_entry:app --app-dir services/api --reload --port 8000
```

Основные endpoint'ы:
- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/booking/check-availability`
- `POST /api/v1/booking/requests`
- `GET /api/v1/pms/grid`
- `GET/POST /api/v1/admin/pms/reservations/{id}/schedule...`
- `GET /api/v1/automation/read/hotel-facts`
- `/docs` — OpenAPI UI в development.

## Запуск приложений

В отдельных терминалах:

```bash
cd apps/admin && npm install && npm run dev
```

```bash
cd apps/web && npm install && npm run dev
```

```bash
cd apps/staff && npm install && npm run dev
```

Ожидаемые development ports:
- public site: `3000`;
- PMS/admin: `3001`;
- staff PWA: `3002`;
- Resort Core: `8000`.

## Бронирование и предоплата

Правила V1:
- `ReservationRequest != Reservation`;
- заявка без менеджерского подтверждения не занимает inventory;
- старое правило публичного сайта про «держим неоплаченную бронь 2 дня» не используется;
- Core рассчитывает стоимость проживания;
- менеджер самостоятельно определяет и принимает предоплату;
- Resort OS может зафиксировать фактически принятую менеджером сумму;
- n8n/AI не выбирает сумму/способ предоплаты и не подтверждает бронь самостоятельно;
- создание Reservation + InventoryBlock + manager-recorded Payment происходит контролируемо и атомарно.

## Публичный сайт

`apps/web` — текущий канонический сайт, а не старый V5-макет.

Уже используется:
- реальная availability из Resort Core;
- стоимость на выбранные даты;
- тарифные meal facts;
- 12 категорий;
- отправка реального ReservationRequest;
- mobile booking flow;
- SEO metadata / OpenGraph / JSON-LD / sitemap / robots.

Перед финальным production cutover нужно заменить временные media sources на собственные фотографии «Трёх Корон» и пройти staging acceptance.

## n8n

n8n не пишет PostgreSQL напрямую.

Он использует `X-Resort-Service-Key` и разрешённые Resort Core contracts для:
- hotel facts;
- availability/pricing;
- create/read ReservationRequest;
- request/reservation status;
- structured staff intake where applicable.

Запрещено для n8n/AI:
- создавать гарантированную бронь напрямую;
- подтверждать деньги;
- check-in/check-out;
- refund;
- прямой SQL;
- выдумывать availability/price/policy.

## Production gates

До production:
- migration baseline;
- backup -> clean restore verification;
- production preflight;
- secure secrets/cookies;
- current-main build/E2E evidence;
- staging acceptance;
- monitoring;
- rollback rehearsal;
- только затем DNS/cutover.

Никаких необратимых production DB/DNS действий без отдельного owner gate.

## Development rule

`KNOWLEDGE -> CURRENT STATE -> GAP -> PRIORITY -> IMPLEMENT -> TEST -> EVIDENCE -> VERIFIED / NOT VERIFIED -> CURRENT STATE UPDATE`
