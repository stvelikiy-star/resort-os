# Dining target contract

## Included meals
Included meal rights are represented independently from kitchen orders and financial charges. Each row is scoped to property + stay + service date + meal type and stores adult/child portion counts plus source.

## Paid food
Paid food remains a KitchenOrder and can produce a folio charge only after an explicit charge record is created. Order creation alone is not a Payment.

## Room service
Room-service delivery fee is recorded separately from food subtotal and is configurable in Resort Core.

## Staff responsibilities
- Chef: production quantities, menu availability/stop list and NEW→READY preparation lifecycle.
- Waiter: table/room delivery assignment and READY→SERVED handoff.
- Manager: configuration, exception overrides, table map/zones and audit.

## Identity
All guest dining actions link to Stay/Reservation; room code is display context, not identity.
