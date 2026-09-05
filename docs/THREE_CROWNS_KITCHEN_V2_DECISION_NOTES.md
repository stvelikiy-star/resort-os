# Three Crowns Kitchen V2 — decision notes

Status: design boundary for the next implementation step; no fabricated business facts.

## What exists now

The current Core can already manage menu items, physical tables, Kitchen orders, dining arrival cards and guest room orders. This is enough for a real operational baseline, but not enough to truthfully claim a scheduled "menu for today" or separate waiter-vs-kitchen permissions.

## Required Kitchen V2 capabilities

### Kitchen display
- new orders first;
- accept -> cooking -> ready;
- room/table/source context;
- elapsed time since order opened;
- notes and quantities in large touch-friendly format;
- audible/visual new-order signal only after product acceptance;
- no hotel-payment mutation.

### Floor / waiter view
- table map/list;
- seats and table state;
- create order for table;
- add items to an open order only after a server-side mutation contract is defined;
- mark table cleaning / available;
- see READY orders for delivery;
- waiter must not edit hotel reservations/payments.

### Menu manager
- create/edit/archive items;
- RU/KG/EN names;
- category;
- server price;
- active / draft / sold-out;
- optional photo after owned media is supplied;
- publication preview for Guest OS.

### "Menu today"
Current `is_active + !is_draft` means "published now", not a date schedule. A true daily menu requires explicit Core fields or a schedule table for service date / meal window / sold-out. Until that schema exists, UI copy must say "available now" rather than invent a date-specific programme.

### Roles
Current role `DINING_STAFF` can safely power both Kitchen and floor interfaces. Splitting into `KITCHEN_STAFF` and `WAITER` changes the canonical StaffRole enum, auth policy, seed/test accounts and migration contract. Do this only as one reviewed schema/security change, not as a frontend-only label.

## Guest commerce boundary
Guest OS may show only published menu items and may create a Kitchen order. It may also create hotel service requests. It must not:
- expose draft/sold-out items;
- set authoritative prices client-side;
- post Hotel Payment automatically;
- guarantee an external partner service;
- treat an AI answer as commercial confirmation.

## Marketing layer
Offers should ultimately become owner-configurable records with:
- localized title/hook;
- target surface and priority;
- start/end window;
- enabled flag;
- action type (hotel request / internal catalogue / configured external link);
- impression/click/request analytics;
- no hidden profiling or automatic outbound action.

The first branch uses only existing verified hotel-service codes and an optional configured KÖL URL. This is intentionally a safe V1 before a dedicated offers schema is introduced.
