# THREE CROWNS — SOURCE RECONCILIATION

Date: 2026-08-25
Status: EVIDENCE ANALYSIS
Purpose: reconcile owner-provided 2026 materials, room-grid screenshots, official 3korony.com data and public third-party sources without converting uncertain information into facts.

## 1. Source priority

1. Owner/project-provided 2026 source material.
2. Official 3korony.com current pages / official PDF.
3. Current major listing / booking platforms for cross-check.
4. Tour-operator copies for corroboration only.
5. Guest reviews as operational signals only, never as canonical rules.

## 2. Confirmed property scale

Official website states:
- 84 rooms;
- 220 guest places;
- own beach;
- 150 m pier;
- open pool 15 x 8 m;
- three hotel buildings on the site plan;
- restaurant, summer restaurant/bar, self-service summer kitchen, store/order desk, laundry, SPA/massage, medical point, billiards and other facilities.

The supplied room-grid screenshots reconcile to exactly 84 sellable room positions when the category structure is reconstructed.

## 3. Reconstructed room inventory

Category | Count | Evidence status
---|---:|---
Одноместный, цоколь | 1 | direct screenshot
Двухместный стандарт, цоколь | 10 | direct screenshot
Одноместный, улучшенный | 2 | category inferred for 501/502 from spreadsheet row sequence + exact 84-room total; CONFIRM
Двухместный стандарт в коттеджном доме | 15 | direct screenshot
Двухместный улучшенный | 14 | direct screenshot
Полулюкс без балкона | 2 | direct screenshot
Люкс двухместный | 12 | direct screenshot
Люкс трехместный | 10 | direct screenshot
Двухкомнатный стандарт | 4 | direct screenshot
Двухкомнатный полулюкс | 4 | direct screenshot
Апартаменты | 4 | direct screenshot
Квартиры / апартаменты с кухней | 6 | direct screenshot + official alias reconciliation
TOTAL | 84 | reconciles with official website

The exact room-level import is stored in `data-intake/rooms.csv`.

### Critical room-data caveats

- Exact mapping of ordinary numbered rooms to the official `Первый / Второй / Третий корпус` is not established.
- Exact floor mapping must not be inferred from the first digit of a room number.
- 501/502 are labelled with text including `прачка мансарда`; their category assignment to `Одноместный улучшенный` is a high-confidence reconstruction, not direct category text from the provided crop.
- Bed abbreviations are preserved from the operational spreadsheet; their decoding key must be confirmed before converting to structured bed objects.
- Room 421 is explicitly marked `sea view` in the supplied spreadsheet.

## 4. 2026 pricing reconciliation

The photographed 2026 price list and official 3korony.com / `prices_ru.pdf` agree on the core summer tariff grid.

Periods:
- 1 Jun - 6 Jul;
- 7 Jul - 25 Aug;
- 26 Aug - 15 Sep;
- official site additionally publishes 16 Sep - 31 May.

Current room rate range:
- summer minimum: 3000 KGS;
- summer peak maximum: 15500 KGS.

Summer prices are stated on breakfast basis. Official source states 16 Sep - 31 May is without breakfast.

The complete normalized tariff matrix is stored in `data-intake/rates.csv`.

### Pricing caveat

Official sources display `0 KGS` for basement single/double categories during 16 Sep - 31 May. This MUST NOT be interpreted as a free room. The sale/closure rule for those categories requires owner confirmation.

## 5. Additional guest / food tariffs

Direct 2026 material:

Adult:
- extra guest: 1500 KGS/day;
- breakfast: 500 KGS;
- lunch: 750 KGS;
- dinner: 650 KGS;
- 3 meals/day: 1900 KGS.

Child:
- extra guest: 850 KGS/day;
- breakfast: 400 KGS;
- lunch: 550 KGS;
- dinner: 450 KGS;
- 3 meals/day: 1400 KGS.

Direct sheet wording says extra child charge from age 4 and adult tariff from age 13. Exact under-4 rule still needs explicit confirmation.

## 6. Reservation rule reconciliation

Official website says:
- room is considered booked when the guest has confirmation from a hotel manager;
- guaranteed booking requires prepayment for the first night/day;
- without prepayment the preliminary booking is removed after 2 days.

This supports a two-stage reservation model:

`REQUEST -> MANAGER APPROVED / AWAITING PREPAYMENT -> GUARANTEED`

### Critical conflict

Earlier project concept: `30% prepayment`.

Current official hotel information: `first night prepayment`.

Production logic must use neither as an unreviewed hard-code. Owner confirmation is required, with the current official rule treated as the stronger evidence until changed.

## 7. Payment method reconciliation

Direct 2026 price sheet:
- Visa;
- MasterCard;
- QR code;
- cash;
- bank transfer.

Official website also mentions Elsom.

Interpretation:
- direct 2026 sheet is the preferred current business input;
- Elsom may be stale website content and must be confirmed before implementation.

## 8. Check-in / check-out conflict

Project baseline and several current booking/tour sources show:
- check-in 14:00;
- check-out 12:00.

Google Hotels currently shows checkout 11:00.

Therefore:
- 14:00 / 12:00 is the stronger working rule;
- owner confirmation is still required before go-live.

## 9. Public channel footprint observed

Confirmed public surfaces:
- 3korony.com;
- official website booking/request form;
- reservation phone;
- WhatsApp;
- Telegram;
- Booking.com listing;
- Yandex Travel;
- Google Hotels;
- 2GIS;
- multiple tour operator / reseller pages.

Current Booking.com crawl states the property cannot currently be booked there, although the listing remains visible.

Exact active Instagram account/handle was not established from available evidence.

### System consequence

The future Communications / Channel Control module should distinguish:
- OWNED CONTACT CHANNEL;
- ACTIVE BOOKING CHANNEL;
- LISTING ONLY;
- RESELLER / TOUR OPERATOR;
- UNKNOWN / NEEDS VERIFICATION.

Do not assume every public listing is an active sales integration.

## 10. Property facilities confirmed from official sources

Official site plan / services confirms at least:
- reception;
- three hotel buildings;
- four conference halls (site text gives capacity range 30-200; another section mentions 40 and 120);
- main restaurant;
- summer restaurant with bar;
- self-service summer kitchen;
- outdoor fresh-water pool;
- decorative water features;
- camping / autocamp units;
- children's playground;
- sports ground;
- gym;
- store / order desk;
- laundry;
- massage / SPA;
- medical point;
- sandy beach;
- 150 m pier with berth and sauna;
- parking;
- billiards among paid leisure services.

Exact current operational status of every listed service is not proven merely by website presence.

## 11. Guest-review operational signals

Historical/current review sources contain recurring signals about:
- housekeeping being requested via reception rather than automatically scheduled;
- delayed housekeeping in some stays;
- delayed maintenance response in some stays;
- beach access / outsider-control complaints despite wristbands;
- dining-hall flow and replenishment issues in some reviews;
- positive feedback about cleanliness, grounds, food and reception responsiveness in other reviews.

These are NOT canonical facts about today's operation.

They are useful product-design signals supporting:
- housekeeping task queue;
- maintenance SLA / escalation;
- guest request tracking;
- beach/access control status;
- dining attendance / entitlement control;
- response-time analytics.

## 12. Audio evidence

Owner/project audio supplied on 2026-08-25 is preserved as a source input in the conversation context.

Its semantic contents have not been entered into canonical facts here because a reliable transcript was not available in the current analysis toolchain. No statement from that audio has been invented or inferred.

## 13. Current verdict

The project now has enough evidence to design the real PMS/booking database around the actual property rather than demo inventory.

What is now sufficiently grounded:
- property scale: 84 rooms / 220 places;
- almost complete room-to-category roster;
- 2026 category rates and seasonal bands;
- base occupancy by category;
- major meal / extra-person tariffs;
- manager confirmation boundary;
- guaranteed-booking prepayment concept;
- major physical/service modules.

What still blocks production booking correctness:
- owner confirmation of prepayment rule versus old 30% concept;
- cancellation/refund/no-show rules;
- exact hold timer start;
- specific-room vs category reservation policy;
- exact building/floor mapping;
- exact 501/502 classification;
- bed-abbreviation dictionary;
- authoritative check-out time;
- active channel ownership and credentials;
- exact dining operation workflow;
- exact access/LED hardware.

## 14. Architecture consequence

Immediate build order should now be:

1. canonical RoomType + Room seed from `rooms.csv`;
2. RatePlan / RatePeriod seed from `rates.csv`;
3. ReservationRequest + Reservation + Hold / Guarantee states;
4. deterministic availability engine;
5. PMS grid backed by real data;
6. public availability request flow;
7. housekeeping + maintenance tasks;
8. unified communications / response control;
9. dining / store / QR / access / billiards / LED modules after their workflows are confirmed.

NFC remains deferred and must not be a dependency of the core hotel system.
