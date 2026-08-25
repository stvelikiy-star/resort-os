# THREE CROWNS — RESERVATION RULES INPUT

Updated: 2026-08-25
Status: EVIDENCE-BACKED INTAKE / NOT YET FULLY OWNER-CONFIRMED

Этот файл содержит только правила, для которых найдено evidence. Неизвестное остаётся `UNKNOWN`.

Source priority used for this update:

1. owner-provided / project-provided 2026 materials;
2. official `3korony.com` and official 2026 PDF;
3. multiple current booking/listing sources for cross-check;
4. third-party reviews only as operational signals, never as business-rule authority.

---

## 1. Human Confirmation

Кто имеет право окончательно подтвердить бронь:

`MANAGER / RESERVATION ADMINISTRATOR` — official website states that a room is considered booked when the guest has booking confirmation from the hotel manager.

Что обязательно проверяет сотрудник перед подтверждением:

`UNKNOWN` — exact checklist not published.

Evidence-backed lifecycle interpretation for design:

`RESERVATION REQUEST -> AVAILABILITY / PRICE CHECK -> MANAGER APPROVAL -> AWAITING PREPAYMENT -> GUARANTEED RESERVATION`

The distinction between manager-confirmed but non-guaranteed and guaranteed reservation should be preserved in the data model.

---

## 2. Deposit / Prepayment

Требуется ли предоплата:

`YES` for guaranteed booking.

Размер:

`FIRST NIGHT / FIRST DAY OF STAY` according to the current official website.

Срок оплаты:

Official wording: if prepayment is absent, preliminary booking is removed after `2 days`.

Exact timestamp from which the 2-day period starts:

`CONFIRM` — likely preliminary booking creation/manager approval, but not explicitly defined.

Что происходит, если срок истёк:

`PRELIMINARY BOOKING IS REMOVED` according to the official website.

### CRITICAL CONFLICT

Earlier project concept used `30% prepayment`.

Current official business information states `prepayment for the first night`.

For implementation, **30% MUST NOT be hard-coded** until the owner explicitly changes the current hotel rule.

---

## 3. Cancellation

Правило отмены:

`UNKNOWN`

Возврат предоплаты:

`UNKNOWN`

---

## 4. No-show

Как обрабатывается незаезд:

`UNKNOWN`

---

## 5. Check-in / Check-out

Check-in: `14:00` — supported by earlier project rule and multiple current booking sources.

Check-out: `12:00` — supported by earlier project rule and multiple current booking sources.

Conflict: Google Hotels currently displays `11:00` checkout, while Skyscanner / Alean / Putevka and project baseline show `12:00`.

Implementation status: `USE 14:00 / 12:00 AS PROVISIONAL HOTEL RULE; OWNER CONFIRM BEFORE GO-LIVE`.

Early check-in:

`UNKNOWN / BY REQUEST` appears on third-party sources, but exact charging rule is not established.

Late check-out:

`UNKNOWN / BY REQUEST` appears on third-party sources, but exact charging rule is not established.

---

## 6. Children / Extra Guests

Owner-provided 2026 price sheet states:

- extra guest above declared room places — adult: `1500 KGS / day`;
- extra guest above declared room places — child: `850 KGS / day`;
- charge wording: child from `4 years`, adult from `13 years` according to tariffs;
- additional linen/service is included in that extra-person tariff.

Therefore the working age interpretation is:

- child tariff: age `4-12`;
- adult tariff: age `13+`.

Status: `HIGH-CONFIDENCE FROM DIRECT 2026 MATERIAL, BUT CONFIRM EXACT AGE BOUNDARY / UNDER-4 RULE`.

A third-party source uses a different child age wording (`до 11 лет`), so the direct 2026 price sheet must take priority until owner clarification.

---

## 7. Meals

Room-price meal inclusion:

- `1 Jun - 15 Sep`: breakfast included;
- `16 Sep - 31 May`: official website/PDF states prices are without breakfast.

Additional meal tariffs from 2026 materials:

Adult:
- breakfast: `500 KGS`;
- lunch: `750 KGS`;
- dinner: `650 KGS`;
- 3 meals/day: `1900 KGS`.

Child:
- breakfast: `400 KGS`;
- lunch: `550 KGS`;
- dinner: `450 KGS`;
- 3 meals/day: `1400 KGS`.

Exact dining entitlement/check-in mechanism:

`UNKNOWN`.

---

## 8. Payment Methods

Owner-provided 2026 price sheet states hotel accepts:

- Visa;
- MasterCard;
- QR payment;
- cash;
- bank transfer.

Official website also mentions an older `Elsom` wallet flow.

Current implementation rule:

`USE OWNER-PROVIDED 2026 PAYMENT LIST AS PRIMARY BUSINESS INPUT; ELSOM STATUS = CONFIRM / POSSIBLY STALE WEBSITE CONTENT`.

Exact acquiring providers / QR provider / bank requisites / fiscal flow:

`UNKNOWN`.

---

## 9. Booking Sources

Observed public contact/booking surfaces:

- official website booking/request form;
- reservation phone;
- WhatsApp;
- Telegram;
- third-party hotel/travel listings including Booking, Yandex Travel, Google Hotels and tour operators.

Important current observation:

Booking.com listing exists, but a recent crawl states the property cannot currently be booked there.

Which channels are actually managed as active sales sources today:

`OWNER / OPERATIONS CONFIRM`.

Instagram account / exact active handle:

`NOT ESTABLISHED FROM AVAILABLE EVIDENCE`.

---

## 10. Discounts / Manual Price Changes

Official website states discounts may be provided:

- to travel agencies depending on number of rooms and duration, with prepayment;
- to collective / group / corporate arrivals depending on room quantity and stay duration.

Exact percentage / approval authority / minimum volume:

`UNKNOWN`.

Can manager manually change price:

`UNKNOWN`.

Required audit reason for manual discount:

`TO BE REQUIRED BY SYSTEM DESIGN, BUT BUSINESS AUTHORITY STILL NEEDS CONFIRMATION`.

---

## 11. Room Assignment

Бронируется конкретный номер или только категория до заселения:

`UNKNOWN`.

The current spreadsheet evidence operates at specific-room level, but this does not prove the booking policy.

Можно ли менять номер после подтверждения:

`UNKNOWN`.

---

## 12. Overbooking

Допускается ли overbooking:

`UNKNOWN`.

Default safety rule remains:

`DO NOT ALLOW OVERBOOKING unless explicitly approved by the owner`.

---

## 13. Immediate Owner Confirmations Still Required

Only the following reservation questions remain critical before production booking logic:

1. Is the guaranteed-booking prepayment definitely **first night**, replacing the old 30% concept?
2. Is check-out definitely **12:00**?
3. Are ages `4-12 child / 13+ adult` correct, and what is the rule for children under 4?
4. Are 2 unpaid days counted from request creation or from manager approval?
5. What are cancellation/refund/no-show rules?
6. Is booking held by category first or by a specific room number?
