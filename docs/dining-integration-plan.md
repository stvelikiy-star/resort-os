# Dining integration plan

Working implementation plan for integrating the legacy Three Crowns dining prototype into Resort OS without creating a second source of truth.

## Principles
- PostgreSQL + Resort Core remain the only operational source of truth.
- Legacy Firebase/Firestore patterns are not imported.
- Guest identity is linked by Stay/Reservation, never by room number alone.
- Included meal entitlement is separate from paid restaurant/room-service charges.
- Chef, waiter, manager and guest surfaces share one Dining Core.

## Delivery order
1. Dining entitlement model and migration.
2. Materialization/reconciliation of meal entitlements from active reservations/stays.
3. Chef production summary: portions by meal/date, adults/children, departures and exceptions.
4. Dining floor enhancements: guest/stay binding, waiter assignment, seat lifecycle and move-table workflow.
5. Guest OS cutoff and room-service handoff into kitchen orders and folio charges.
6. Banquet/conference event production hooks.
7. Finance/folio integration.
8. Full regression and E2E verification.
