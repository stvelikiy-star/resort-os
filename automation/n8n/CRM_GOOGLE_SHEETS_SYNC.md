# Three Crowns — Resort Core → Google Sheets CRM Sync

Status: implementation contract for n8n wiring
Date: 2026-08-26

## Purpose

Keep the operational Google Sheets CRM as a convenient manager-facing mirror of Resort Core sales truth without creating a second booking database.

Canonical direction:

`Website / ManyChat / API Green -> Resort Core -> n8n -> Google Sheets CRM`

The Google Sheet is **not** allowed to create, confirm or mutate Reservation, Payment, InventoryBlock or stay lifecycle truth.

## Target spreadsheet

Google Spreadsheet ID:

`1Xqh696QZaNf25pYUA9TLnVEMWl4IZMMyMsZ16OhH_0A`

Title:

`CRM — Три Короны — Продажи и бронирования`

Primary tabs:

- `Лиды`
- `Бронирования`
- `Платежи`

Supporting tabs already present:

- `Гости`
- `Задачи`
- `Справочники`
- `Дашборд`
- `README`

## Authoritative API

Protected endpoint:

`GET /api/v1/automation/read/crm-feed`

Required header:

`X-Resort-Service-Key: <AUTOMATION_SERVICE_KEY>`

Query parameters:

- `updated_after` — optional timezone-aware ISO-8601 timestamp;
- `limit` — 1..1000, default 500.

The endpoint returns three independent collections:

- `requests.items`
- `reservations.items`
- `payments.items`

Each collection also returns `truncated`.

## Sync algorithm

Recommended polling interval for launch: every 5 minutes.

1. Read `last_successful_sync` from n8n workflow static data or a dedicated control record.
2. Request `crm-feed` using an overlap window of at least 5 minutes before the stored timestamp.
3. Upsert every returned row by stable ID.
4. Only advance the stored high-water mark to the response `generated_at` when all three `truncated` flags are `false`.
5. If any collection is truncated, rerun with the same `updated_after` and a higher limit or narrower window; do not advance the high-water mark.
6. Retries are safe because Google Sheet writes must use stable-ID upserts rather than blind append.

The overlap window is deliberate. It protects against scheduler delays and same-timestamp updates; duplicate rows are prevented by ID-based upsert.

## `Лиды` mapping

Primary key: `Lead ID` = `requests.items[].lead_id`

| Google Sheet column | Core field |
| --- | --- |
| Lead ID | `lead_id` |
| Дата/время | `created_at` |
| Канал | `channel` |
| Имя | `guest_name` |
| Телефон | `phone` |
| Контакт/ник | `email` when present; messenger handle may be added later |
| Заезд | `check_in` |
| Выезд | `check_out` |
| Ночей | `nights` |
| Гостей | `adults + children` |
| Дети | `children` |
| Тип номера | `room_type_name` or `room_type_code` |
| Бюджет KGS | `quoted_total_kgs` |
| Статус | `status` |
| Источник/кампания | `channel` until richer attribution is implemented |
| Комментарий | `notes` |
| Booking ID | `booking_id` |

Columns such as owner, next contact and chat URL remain CRM-only manager fields until a canonical Core model is approved. The sync must not erase non-Core manager columns.

## `Бронирования` mapping

Primary key: `Booking ID` = `reservations.items[].booking_id`

Recommended mapping:

| Google Sheet column | Core field |
| --- | --- |
| Booking ID | `booking_id` |
| Lead ID | `lead_id` |
| Дата создания | `created_at` |
| Гость | `guest_name` |
| Телефон | `phone` |
| Заезд | `check_in` |
| Выезд | `check_out` |
| Ночей | `nights` |
| Гостей | `adults + children` |
| Сумма | `total_kgs` |
| Оплачено KGS | `received_kgs` |
| Остаток KGS | `outstanding_kgs` |
| Статус брони | `status` |

Room assignment is intentionally not flattened into this feed yet because PMS supports split stays / relocations. A future CRM room-route projection must be schedule-aware rather than copying only the first room.

## `Платежи` mapping

Primary key: `Payment ID` = `payments.items[].payment_id`

| Google Sheet column | Core field |
| --- | --- |
| Payment ID | `payment_id` |
| Booking ID | `booking_id` |
| Дата | `paid_at` or `created_at` |
| Гость | `guest_name` |
| Сумма KGS | `amount_kgs` |
| Валюта | fixed `KGS` for current Three Crowns property truth |
| Метод | `method` |
| Статус | `status` |
| Референс/транзакция | `external_ref` |

The sheet must never be treated as evidence that money was received. Only Resort Core `Payment` facts are authoritative.

## n8n credentials

Keep secrets only in n8n credentials/environment management:

- `RESORT_CORE_URL`
- `AUTOMATION_SERVICE_KEY`
- Google OAuth2 credential with access to the target spreadsheet

Do not store service keys or OAuth tokens inside workflow JSON, Google Drive documents or repository files.

## Failure behavior

- Core unavailable: stop the sync; do not invent rows.
- Google Sheets unavailable: keep the previous high-water mark and retry later.
- Duplicate Google row: repair by primary key before continuing.
- Missing/unknown Core field: leave the mirror cell blank; do not infer business truth.
- Any attempt to use the sheet to confirm payment/reservation: reject the design; use controlled PMS/Core actions instead.

## Launch acceptance

Before enabling the workflow continuously:

1. create a test ReservationRequest through the normal website/n8n boundary;
2. confirm it appears exactly once in `Лиды`;
3. quote it in PMS and confirm the same row updates rather than appends;
4. record a manager-confirmed payment and convert it to Reservation;
5. verify `Лиды`, `Бронирования`, `Платежи` reflect the same stable IDs and amounts;
6. verify editing a CRM cell cannot mutate Core booking/payment truth;
7. verify retry after a simulated Google error does not duplicate rows.
