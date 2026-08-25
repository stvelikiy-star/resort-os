# THREE CROWNS — RESERVATION RULES INPUT

Updated: 2026-08-25
Status: OWNER-CORRECTED EVIDENCE INTAKE / NOT YET COMPLETE

Этот файл содержит только правила, для которых найдено evidence или получено прямое подтверждение владельца/проекта. Неизвестное остаётся `UNKNOWN`.

Source priority:

1. direct owner / project confirmation;
2. owner-provided / project-provided 2026 materials;
3. official `3korony.com` and official 2026 PDF, unless explicitly identified as stale;
4. current booking/listing sources for cross-check only;
5. third-party reviews only as operational signals, never as business-rule authority.

---

## 1. Reservation validity / Human Confirmation

Canonical product rule:

`RESERVATION REQUEST != CONFIRMED RESERVATION`.

Final reservation requires Human Confirmation.

Direct owner/project correction on 2026-08-25:

`WITHOUT PREPAYMENT THE BOOKING IS NOT VALID.`

Therefore an unpaid request / intent MUST NOT be represented to the guest or staff as a valid confirmed booking.

Working lifecycle for design:

`RESERVATION REQUEST -> AVAILABILITY / PRICE CHECK -> MANAGER APPROVAL -> PAYMENT REQUIRED -> PREPAYMENT CONFIRMED -> VALID / GUARANTEED RESERVATION`

Exact ordering details may be refined after all owner answers are received, but the invariant is already confirmed:

`NO PREPAYMENT -> NO VALID BOOKING`.

Whether an unpaid request temporarily blocks inventory before payment:

`UNKNOWN / OWNER ANSWER REQUIRED`.

---

## 2. Deposit / Prepayment

Требуется ли предоплата:

`YES` — OWNER/PROJECT CONFIRMED 2026-08-25.

Critical rule:

`WITHOUT PREPAYMENT THE BOOKING IS NOT VALID.`

Размер / формула предоплаты:

`UNKNOWN / OWNER ANSWER REQUIRED`.

Do NOT currently hard-code:

- `30%` from an earlier project concept;
- `first night` from stale official website text.

The current official website contains outdated reservation information and MUST NOT be used as authority for the unpaid-booking timer or prepayment formula until revalidated.

Срок оплаты:

`UNKNOWN / OWNER ANSWER REQUIRED`.

Что происходит до оплаты:

The request may exist as a lead / reservation request, but it is NOT a valid confirmed booking.

Whether inventory is held during that period:

`UNKNOWN / OWNER ANSWER REQUIRED`.

---

## 3. STALE WEBSITE RULE — REJECTED FOR IMPLEMENTATION

Old website wording:

- preliminary booking is removed after 2 days without prepayment;
- guaranteed booking requires prepayment for the first night.

Owner/project correction on 2026-08-25:

`THE WEBSITE INFORMATION IS OLD.`

Implementation status:

- `2 unpaid days` rule: **DO NOT IMPLEMENT**;
- timer start question: **REMOVED FROM ACTIVE REQUIREMENTS**;
- `first night` prepayment formula: **DO NOT IMPLEMENT UNTIL OWNER CONFIRMS CURRENT FORMULA**.

Historical website wording may be retained only as stale-source evidence, not as a business rule.

---

## 4. Cancellation

Правило отмены:

`UNKNOWN`

Возврат предоплаты:

`UNKNOWN`

---

## 5. No-show

Как обрабатывается незаезд:

`UNKNOWN`

---

## 6. Check-in / Check-out

Check-in: `14:00` — supported by earlier project rule and multiple current booking sources.

Check-out: `12:00` — supported by earlier project rule and multiple current booking sources.

Conflict: Google Hotels currently displays `11:00` checkout, while other project/current sources show `12:00`.

Implementation status: `USE 14:00 / 12:00 AS PROVISIONAL HOTEL RULE; OWNER CONFIRM BEFORE GO-LIVE`.

Early check-in:

`UNKNOWN`.

Late check-out:

`UNKNOWN`.

---

## 7. Children / Extra Guests

Owner-provided 2026 price sheet states:

- extra guest above declared room places — adult: `1500 KGS / day`;
- extra guest above declared room places — child: `850 KGS / day`;
- charge wording: child from `4 years`, adult from `13 years` according to tariffs;
- additional linen/service is included in that extra-person tariff.

Working age interpretation:

- child tariff: age `4-12`;
- adult tariff: age `13+`.

Status: `HIGH-CONFIDENCE FROM DIRECT 2026 MATERIAL, BUT CONFIRM UNDER-4 RULE`.

---

## 8. Meals

Room-price meal inclusion:

- `1 Jun - 15 Sep`: breakfast included according to 2026 price materials;
- off-season meal inclusion requires final owner confirmation before production if website information is stale.

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

## 9. Payment Methods

Owner-provided 2026 price sheet states hotel accepts:

- Visa;
- MasterCard;
- QR payment;
- cash;
- bank transfer.

Older website payment information must be treated as potentially stale until revalidated.

Exact acquiring providers / QR provider / bank requisites / fiscal flow:

`UNKNOWN`.

---

## 10. Booking Sources

Observed public contact/booking surfaces:

- official website booking/request form;
- reservation phone;
- WhatsApp;
- Telegram;
- third-party hotel/travel listings and tour operators.

Which channels are actually managed as active sales sources today:

`OWNER / OPERATIONS CONFIRM`.

Instagram account / exact active handle:

`NOT ESTABLISHED FROM AVAILABLE EVIDENCE`.

---

## 11. Discounts / Manual Price Changes

Exact percentage / approval authority / minimum volume:

`UNKNOWN`.

Can manager manually change price:

`UNKNOWN`.

Required audit reason for manual discount:

`TO BE REQUIRED BY SYSTEM DESIGN, BUT BUSINESS AUTHORITY STILL NEEDS CONFIRMATION`.

---

## 12. Room Assignment

Бронируется конкретный номер или только категория до заселения:

`UNKNOWN`.

The current spreadsheet evidence operates at specific-room level, but this does not prove the booking policy.

Можно ли менять номер после подтверждения:

`UNKNOWN`.

---

## 13. Overbooking

Допускается ли overbooking:

`UNKNOWN`.

Default safety rule:

`DO NOT ALLOW OVERBOOKING unless explicitly approved by the owner`.

---

## 14. Immediate Owner Answers Still Needed

The former question about `2 unpaid days` is CLOSED and removed because the website rule is stale.

Remaining booking facts to resolve from the owner's answers include:

1. Current prepayment amount / formula.
2. Whether an unpaid request blocks inventory at all, and if yes, for how long / under whose action.
3. Final check-out time.
4. Cancellation / refund / no-show rules.
5. Category-first vs specific-room booking policy.
6. Children under 4 rule.

Do not reintroduce the stale 2-day timer unless the owner explicitly establishes a new current rule.
